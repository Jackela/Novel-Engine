import type { Principal } from "../../../shared/application/ports/auth.js";
import type { DiagnosticsHealthProbe } from "./ports/diagnostics_health.js";
import type { StudioJobLedgerStore } from "./ports/job_ledger_store.js";
import { jobPageLimit } from "./ports/job_records.js";
import { scopeForPrincipal } from "./ports/studio_store.js";

/**
 * Human-readable provider labels mirroring the Settings surface's English
 * dictionary values (#606); unknown provider ids fall back to their raw id so
 * providers added later stay readable in support files.
 */
const PROVIDER_LABELS: Readonly<Record<string, string>> = {
  mock: "Mock (trial — no API key)",
  dashscope: "DashScope",
  openai_compatible: "OpenAI-compatible",
};

/** How many persisted failure messages the export carries. */
const RECENT_ERROR_LIMIT = 5;

/**
 * The bounded audit window the failure scan reads: the newest job summaries,
 * newest first. Failures older than this window fall out of the "recent"
 * horizon by design — diagnostics describes the machine's present, not its
 * complete history.
 */
const RECENT_ERROR_WINDOW = jobPageLimit(100);

/**
 * The composition-root-supplied facts of the diagnostics export (#654):
 * identity, runtime, and configuration state as plain values, so the service
 * never reads the filesystem or the process itself.
 */
export interface DiagnosticsFacts {
  readonly product: { readonly name: string; readonly version: string };
  readonly runtime: {
    readonly platform: string;
    readonly architecture: string;
    readonly nodeVersion: string;
  };
  readonly provider: { readonly id: string };
  /**
   * Set/unset booleans only — the structural redaction rule: the summary has
   * no field capable of carrying a secret value, so the session secret and
   * provider API keys are reported as configured state, never as values.
   */
  readonly keys: {
    readonly sessionSecret: boolean;
    readonly dashscopeApiKey: boolean;
    readonly openaiCompatibleApiKey: boolean;
  };
}

/** One persisted failure message of the project's most recent failed Jobs. */
export interface DiagnosticsRecentError {
  readonly message: string;
  readonly occurredAt: string;
}

/** The complete diagnostics summary the export endpoint serializes. */
export interface DiagnosticsSummary {
  readonly generatedAt: string;
  readonly product: DiagnosticsFacts["product"];
  readonly runtime: DiagnosticsFacts["runtime"];
  readonly configuration: {
    readonly provider: {
      readonly id: string;
      readonly label: string;
      readonly configured: boolean;
    };
    readonly keys: {
      readonly sessionSecret: boolean;
      readonly dashscopeApiKey: boolean;
      readonly openaiCompatibleApiKey: boolean;
    };
  };
  readonly database: {
    readonly quickCheck: string;
    readonly journalMode: string;
    readonly foreignKeys: boolean;
    readonly ownerConfigured: boolean;
  };
  /**
   * The current project's most recent failed Jobs' persisted error messages,
   * newest first; empty is an explicit healthy state, not a missing field.
   */
  readonly recentErrors: readonly DiagnosticsRecentError[];
}

interface DiagnosticsServiceOptions {
  readonly now?: (() => Date) | undefined;
}

/**
 * Assembles the opt-in diagnostics export (#654). Everything secret-capable
 * arrives as a boolean and everything book-like is out of scope by
 * construction: the service reads only the facts above, the health probe, and
 * the persisted failure messages of the requesting project's own jobs.
 */
export class DiagnosticsService {
  private readonly jobs: StudioJobLedgerStore;
  private readonly health: DiagnosticsHealthProbe;
  private readonly facts: DiagnosticsFacts;
  private readonly now: () => Date;

  constructor(
    jobs: StudioJobLedgerStore,
    health: DiagnosticsHealthProbe,
    facts: DiagnosticsFacts,
    options: DiagnosticsServiceOptions = {},
  ) {
    this.jobs = jobs;
    this.health = health;
    this.facts = facts;
    this.now = options.now ?? (() => new Date());
  }

  /**
   * Collect the summary for one project. An unknown project identifier fails
   * with the store's NotFoundError (the 404 envelope at the route); failed
   * jobs of other projects are structurally absent because the store query is
   * owner- and project-scoped.
   */
  collectDiagnostics(principal: Principal, projectId: string): DiagnosticsSummary {
    const scope = scopeForPrincipal(principal);
    const window = this.jobs.collectProjectJobSummaries(scope, projectId, {
      limit: RECENT_ERROR_WINDOW,
    });
    const recentErrors = window.jobs
      .flatMap((job) =>
        job.status === "failed" && job.error !== null
          ? [{ message: job.error, occurredAt: job.updatedAt.toISOString() }]
          : [],
      )
      .slice(0, RECENT_ERROR_LIMIT);
    return {
      generatedAt: this.now().toISOString(),
      product: this.facts.product,
      runtime: this.facts.runtime,
      configuration: {
        provider: {
          id: this.facts.provider.id,
          label: PROVIDER_LABELS[this.facts.provider.id] ?? this.facts.provider.id,
          configured: this.providerConfigured(),
        },
        keys: this.facts.keys,
      },
      database: this.health(),
      recentErrors,
    };
  }

  /**
   * The resolved provider's credential state, mirroring the provider catalog:
   * the deterministic mock is always configured; an HTTP provider exactly
   * when its key is set. Computed from the boolean facts — never from a
   * credential value.
   */
  private providerConfigured(): boolean {
    const id = this.facts.provider.id;
    if (id === "mock") return true;
    if (id === "dashscope") return this.facts.keys.dashscopeApiKey;
    if (id === "openai_compatible") return this.facts.keys.openaiCompatibleApiKey;
    return false;
  }
}
