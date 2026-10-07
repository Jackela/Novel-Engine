import {
  ProviderNotConfiguredError,
  TextGenerationCancelledError,
  TextGenerationProviderError,
} from "../../../contexts/ai/application/ports/text_generation.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import {
  ExportArtifactWriteError,
  ExportCapacityExceededError,
  ExportSourceInvalidatedError,
  GenerationCapacityExceededError,
  NotFoundError,
  ReviewSourceInvalidatedError,
} from "../domain/exceptions.js";

/**
 * The studio job chains' single "domain failure → disposition" registry.
 * Every chain that must decide between landing a failed job, retaining a
 * structured capacity outcome, and letting an error escape asks this module
 * instead of re-listing `instanceof` whitelists, so one table states each
 * known failure class's disposition for every chain: the first-run entry
 * points (proposal draft, review bridge, export bridge, lore-extract
 * wizard), the streaming twin, and the retry executor. Unknown failures —
 * programming errors included — match no rule and propagate untouched, so
 * they keep reaching the opaque 500 handler instead of minting phantom job
 * rows; the HTTP envelope mapping in the interface layer is a separate
 * concern and does not consume this registry.
 */

/** Every first-run entry point whose work can fail into a fresh failed-job row. */
export type StudioFirstRunChain = "proposal" | "review" | "export" | "lore-extract";

/** One first-run chain's verdict: land the failure as a failed job, or let it escape. */
export type StudioFirstRunDisposition =
  | { readonly kind: "land"; readonly failure: Error }
  | { readonly kind: "propagate" };

/**
 * The streaming twin's verdict: `abort` is the client-cancellation signal
 * (the stream ends with no row and no error frame), `land` carries the
 * provider failure whose failed job and `PROVIDER_FAILED` frame the twin
 * records, `propagate` rethrows untouched.
 */
export type StudioStreamingDisposition =
  | { readonly kind: "abort" }
  | { readonly kind: "land"; readonly failure: Error }
  | { readonly kind: "propagate" };

/**
 * The retry chain's verdict for one failed kind execution. The capacity
 * kinds carry the typed failure their structured outcome builder requires;
 * a `land` carries whether the failed attempt was provider-attributable,
 * because only kinds that record provider usage keep the zero-token
 * `unreported` usage row (DR-028) — other kinds land the plain failed
 * transition. `propagate` rethrows untouched.
 */
export type StudioRetryFailureDisposition =
  | { readonly kind: "capacity-export"; readonly failure: ExportCapacityExceededError }
  | { readonly kind: "capacity-generation"; readonly failure: GenerationCapacityExceededError }
  | { readonly kind: "land"; readonly failure: Error; readonly providerAttributable: boolean }
  | { readonly kind: "propagate" };

/** The retry chain's row-level verdict vocabulary, stored on each rule. */
type StudioRetryRule = "land" | "propagate";

/**
 * One classification row: a known failure class paired with its disposition
 * per chain. `matches` doubles as the narrowing proof — a matched failure is
 * an Error — so the landing exits read `failure.message` without casts; the
 * HTTP status of any such failure stays a pure interface concern.
 */
interface StudioFailureRule {
  readonly matches: (error: unknown) => error is Error;
  /** The first-run chains that land this failure as a fresh failed-job row. */
  readonly firstRun: readonly StudioFirstRunChain[];
  /** The streaming twin's verdict for this failure. */
  readonly stream: StudioStreamingDisposition["kind"];
  /** The retry chain's verdict for this failure (fixed; no kind dependence). */
  readonly retry: StudioRetryRule;
  /** Provider-attributable failures keep a retry usage row on usage-recording kinds (DR-028). */
  readonly providerAttributable: boolean;
}

/** Pair a failure constructor with its classification; `matches` narrows to Error. */
function failureRule(
  failureConstructor: abstract new (...args: never[]) => Error,
  classification: Omit<StudioFailureRule, "matches">,
): StudioFailureRule {
  return {
    ...classification,
    matches: (error): error is Error => error instanceof failureConstructor,
  };
}

/** The first-run chains a provider-attributable failure lands in, shared by both provider rows. */
const PROVIDER_LANDING_CHAINS: readonly StudioFirstRunChain[] = [
  "proposal",
  "review",
  "lore-extract",
];

/**
 * The classification table, ordered subclass-first: the first matching row
 * wins, so `ProviderNotConfiguredError` is classified before its
 * `TextGenerationProviderError` parent. The two capacity failures are stated
 * by `retryFailureDisposition` itself — their only chain is the retry chain,
 * which recognizes them by constructor because their dispositions carry the
 * typed failure the capacity outcome builders require.
 */
const STUDIO_FAILURE_RULES: readonly StudioFailureRule[] = [
  // An application-owned stream cancellation is never a job failure: the
  // streaming twin returns silently, every other chain lets it escape.
  failureRule(TextGenerationCancelledError, {
    firstRun: [],
    stream: "abort",
    retry: "propagate",
    providerAttributable: false,
  }),
  // DR-022: an unconfigured provider never starts work and never lands a
  // failed job on the streaming twin — the dedicated PROVIDER_NOT_CONFIGURED
  // envelope must answer. Everywhere else it is what its parent is: a
  // provider failure that lands like any other.
  failureRule(ProviderNotConfiguredError, {
    firstRun: PROVIDER_LANDING_CHAINS,
    stream: "propagate",
    retry: "land",
    providerAttributable: true,
  }),
  // Every expected provider failure lands: a failed job plus (on
  // usage-recording kinds) its zero-token `unreported` usage row.
  failureRule(TextGenerationProviderError, {
    firstRun: PROVIDER_LANDING_CHAINS,
    stream: "land",
    retry: "land",
    providerAttributable: true,
  }),
  // A captured review source disappeared before its result could land: the
  // review bridge and the retry chain land it; nothing else liaises with it.
  failureRule(ReviewSourceInvalidatedError, {
    firstRun: ["review"],
    stream: "propagate",
    retry: "land",
    providerAttributable: false,
  }),
  // A captured export source disappeared before publication landed.
  failureRule(ExportSourceInvalidatedError, {
    firstRun: ["export"],
    stream: "propagate",
    retry: "land",
    providerAttributable: false,
  }),
  // A known operational filesystem failure prevented artifact publication.
  failureRule(ExportArtifactWriteError, {
    firstRun: ["export"],
    stream: "propagate",
    retry: "land",
    providerAttributable: false,
  }),
  // Request-shape refusals raised before or during a retried sequence: the
  // reserved row records them (they are replayable facts, not crashes); the
  // first-run chains raise them before any landing and let them escape.
  failureRule(InvalidOperationError, {
    firstRun: [],
    stream: "propagate",
    retry: "land",
    providerAttributable: false,
  }),
  // A known miss inside a retried sequence lands the same stable refusal.
  failureRule(NotFoundError, {
    firstRun: [],
    stream: "propagate",
    retry: "land",
    providerAttributable: false,
  }),
];

/**
 * The first row matching `error`, paired with its Error narrowing (the second
 * `matches` call is the proof `failure` relies on); null when nothing matches.
 */
function matchingRule(
  error: unknown,
): { readonly rule: StudioFailureRule; readonly failure: Error } | null {
  const rule = STUDIO_FAILURE_RULES.find((candidate) => candidate.matches(error));
  if (rule === undefined || !rule.matches(error)) {
    return null;
  }
  return { rule, failure: error };
}

/**
 * The first-run verdict for one chain (proposal draft, review bridge, export
 * bridge, lore-extract wizard): `land` carries the narrow-matched failure the
 * chain records as a failed-job row, `propagate` means rethrow untouched.
 */
export function firstRunFailureDisposition(
  error: unknown,
  chain: StudioFirstRunChain,
): StudioFirstRunDisposition {
  const match = matchingRule(error);
  if (match === null || !match.rule.firstRun.includes(chain)) {
    return { kind: "propagate" };
  }
  return { kind: "land", failure: match.failure };
}

/** The streaming twin's verdict; see {@link StudioStreamingDisposition}. */
export function streamingFailureDisposition(error: unknown): StudioStreamingDisposition {
  const match = matchingRule(error);
  if (match === null || match.rule.stream === "propagate") {
    return { kind: "propagate" };
  }
  if (match.rule.stream === "abort") {
    return { kind: "abort" };
  }
  return { kind: "land", failure: match.failure };
}

/**
 * The retry chain's verdict for one failed kind execution. Export capacity
 * refusals land their structured outcome and rethrow (the surface renders the
 * pinned envelope); the prompt-byte capacity protocol belongs to proposal
 * retries only — a lore-extract retry re-admits its stored segment, so its
 * refusal lands through the plain failed outcome, like every other landing
 * failure. Unknown failures propagate untouched.
 */
export function retryFailureDisposition(
  error: unknown,
  retryKind: string,
): StudioRetryFailureDisposition {
  // Capacity refusals have no first-run or streaming role: their single chain
  // is the retry chain, which recognizes them by constructor so the
  // disposition carries the typed failure the outcome builders require.
  if (error instanceof ExportCapacityExceededError) {
    return { kind: "capacity-export", failure: error };
  }
  if (error instanceof GenerationCapacityExceededError) {
    return retryKind === "proposal"
      ? { kind: "capacity-generation", failure: error }
      : { kind: "land", failure: error, providerAttributable: false };
  }
  const match = matchingRule(error);
  if (match === null || match.rule.retry !== "land") {
    return { kind: "propagate" };
  }
  return {
    kind: "land",
    failure: match.failure,
    providerAttributable: match.rule.providerAttributable,
  };
}
