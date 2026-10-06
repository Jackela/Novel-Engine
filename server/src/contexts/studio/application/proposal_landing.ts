import {
  type ProviderStep,
  TextGenerationProviderError,
  type TextGenerationTask,
  type TextProviderName,
} from "../../../contexts/ai/application/ports/text_generation.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import { resolvedTokenUsage, rowTokenSource, unreportedAttemptUsage } from "./attempt_usage.js";
import { failedJobInput } from "./failed_job_input.js";
import { BoundedPromptWriter } from "./generation_capacity.js";
import { loreEntriesFromDocuments } from "./lorebook.js";
import type { ProposalStreamFramePayload } from "./payload_schemas/proposal_frame.js";
import { dumpJson, jobPayload } from "./payloads.js";
import type { StudioJobLedgerStore } from "./ports/job_ledger_store.js";
import type { AttemptUsageInput, JobRecord } from "./ports/job_records.js";
import type { ProposalContextSource } from "./ports/proposal_context_store.js";
import type { ProjectScope } from "./ports/studio_store.js";
import { assertProposalCodePointLimit, proposalCodePointCount } from "./proposal_code_points.js";
import { INVALID_PROPOSAL_PROSE, proposalSystemPrompt } from "./proposal_prompts.js";
import {
  buildProposalUserPrompt,
  residentContextSourceFromProposalContext,
} from "./resident_context.js";
import { isProposalMarkdownProse, sanitizeProposalMarkdown } from "./sanitization.js";
import { projectWritingLanguage } from "./writing_language.js";

export {
  createProposalCodePointCounter,
  includeProposalDelta,
  MAX_PROPOSAL_CODE_POINTS,
  OVERSIZED_PROPOSAL,
  type ProposalCodePointCounter,
  proposalCodePointCount,
} from "./proposal_code_points.js";

// The prompt vocabulary and the code-point counter live in their own modules;
// re-exported here so every pipeline and test keeps one stable import surface.
export {
  INVALID_PROPOSAL_PROSE,
  OPERATION_STEPS,
  proposalSystemPrompt,
  SYSTEM_PROMPT,
  SYSTEM_PROMPT_ZH,
} from "./proposal_prompts.js";
export {
  disposeProvider,
  type ProviderCleanupFailureReporter,
} from "./provider_disposal.js";

/**
 * The job/usage landing shared by every proposal pipeline (synchronous
 * draft, #308 streaming, retry): completed proposals persist one completed
 * job plus exactly one usage row carrying labelled token provenance, failures
 * persist one failed job plus its zero-token `unreported` usage row (DR-028) —
 * the manuscript itself is never touched here.
 */

/** The provider task shared by the synchronous, streaming, and retry pipelines. */
export function buildProposalTask(
  step: ProviderStep,
  operation: string,
  instruction: string,
  context: ProposalContextSource,
  /** Lorebook character budget (#445); undefined keeps the adjudicated default. */
  loreBudgetCharacters?: number | undefined,
): TextGenerationTask {
  const document = context.target;
  const revision = document.currentRevision;
  if (revision === null) {
    throw new Error("Proposal task requires a captured current revision.");
  }
  // DR-023: the project's inferred writing language drives both the provider
  // task and the system prompt; the user-prompt budget keeps sharing the
  // selected system prompt's bytes.
  const language = projectWritingLanguage(context);
  const systemPrompt = proposalSystemPrompt(language);
  return {
    step,
    language,
    systemPrompt,
    userPrompt: buildProposalUserPrompt(
      {
        operation,
        instruction,
        source: residentContextSourceFromProposalContext(context),
        manuscriptMarkdown: revision.contentMarkdown,
        loreEntries: loreEntriesFromDocuments(context.documents),
        loreBudgetCharacters,
      },
      new BoundedPromptWriter(systemPrompt),
    ),
    responseSchema: { chapter_markdown: { type: "string" } },
    metadata: {
      operation,
      document_id: document.id,
      base_revision_id: revision.id,
      chapter_number: document.position,
      title: document.title,
    },
  };
}

/**
 * The completed/failed judgment shared by draft, stream, and retry: the
 * provider response must carry a `chapter_markdown` string that sanitizes
 * into story prose. Anything else raises the provider error that every
 * entry point maps onto its failed-job landing.
 */
export function validatedProposalOrThrow(result: {
  readonly content: { readonly chapter_markdown?: unknown };
}): { proposal: string } {
  const chapterMarkdown = result.content.chapter_markdown;
  if (typeof chapterMarkdown !== "string") {
    throw new TextGenerationProviderError(INVALID_PROPOSAL_PROSE);
  }
  assertProposalCodePointLimit(proposalCodePointCount(chapterMarkdown));
  const proposal = sanitizeProposalMarkdown(chapterMarkdown);
  if (!isProposalMarkdownProse(proposal)) {
    throw new TextGenerationProviderError(INVALID_PROPOSAL_PROSE);
  }
  return { proposal };
}

/** Fields every proposal job row shares before its terminal status is known. */
export interface ProposalJobSeed {
  readonly projectId: string;
  readonly documentId: string;
  readonly operation: string;
  readonly provider: TextProviderName;
  readonly requestJson: string;
  /** The optional client request key claimed by the landed row (DR-027). */
  readonly requestKey?: string | undefined;
  readonly now: Date;
}

/** The terminal payload shape of a completed proposal job. */
interface ProposalLanding {
  readonly proposal: string;
  readonly provider: TextProviderName;
  readonly model: string;
  readonly promptTokens: number | null;
  readonly completionTokens: number | null;
  /** The author instruction, used only for absent-token word-count fallback. */
  readonly instruction: string;
}

export function completedProposalJob(
  jobs: StudioJobLedgerStore,
  scope: ProjectScope,
  seed: ProposalJobSeed,
  revisionId: string,
  landing: ProposalLanding,
): JobRecord {
  const { outcome, usage } = completedProposalLanding(landing, {
    operation: seed.operation,
    revisionId,
    now: seed.now,
  });
  // #392: the job row and its usage event commit in one transaction so a
  // failure between the two writes can never strand a completed job.
  return jobs.recordJobWithUsage(scope, {
    job: {
      projectId: seed.projectId,
      documentId: seed.documentId,
      kind: "proposal",
      operation: seed.operation,
      provider: seed.provider,
      status: "completed",
      model: outcome.model,
      requestJson: seed.requestJson,
      resultJson: outcome.resultJson,
      error: null,
      requestIdempotencyKey: seed.requestKey ?? null,
      eventDetailsJson: outcome.eventDetailsJson,
      now: seed.now,
    },
    usage,
  });
}

/**
 * The completed-proposal landing pieces every pipeline shares (#392): the
 * fresh draft inserts a new job row while a retry transitions its reserved
 * row, so both landings carry identical result/usage shapes by construction
 * instead of by duplication. Structurally assignable to
 * `CompleteJobWithUsageInput` for the retry transition.
 */
interface CompletedProposalLanding {
  readonly outcome: {
    readonly status: "completed";
    readonly model: string;
    readonly resultJson: string;
    readonly error: null;
    readonly eventDetailsJson: string;
    readonly now: Date;
  };
  readonly usage: AttemptUsageInput;
}

export function completedProposalLanding(
  landing: ProposalLanding,
  evidence: { readonly operation: string; readonly revisionId: string; readonly now: Date },
): CompletedProposalLanding {
  const prompt = resolvedTokenUsage(landing.promptTokens, landing.instruction);
  const completion = resolvedTokenUsage(landing.completionTokens, landing.proposal);
  return {
    outcome: {
      status: "completed",
      model: landing.model,
      resultJson: dumpJson({
        proposal_markdown: landing.proposal,
        base_revision_id: evidence.revisionId,
        accepted_revision_id: null,
      }),
      error: null,
      eventDetailsJson: dumpJson({ proposal_only: true }),
      now: evidence.now,
    },
    usage: {
      provider: landing.provider,
      model: landing.model,
      promptTokens: prompt.tokens,
      completionTokens: completion.tokens,
      outcome: "completed",
      // DR-028: an estimated side is disclosed on the row itself.
      tokenSource: rowTokenSource(prompt.source, completion.source),
      requestEvidenceJson: dumpJson({
        operation: evidence.operation,
        base_revision_id: evidence.revisionId,
      }),
    },
  };
}

/**
 * The failed-proposal landing (DR-028): the failed job row and its zero-token
 * `unreported` usage row commit in one transaction, so a provider attempt that
 * reached the provider stays visible in the usage ledger even when it failed
 * before any usage was reported.
 */
export function failedProposalJob(
  jobs: StudioJobLedgerStore,
  scope: ProjectScope,
  // The captured landing target: the job seed plus its immutable base revision.
  target: { readonly seed: ProposalJobSeed; readonly revisionId: string },
  message: string,
  // DR-006: raw text accumulated before a mid-stream failure; the persisted
  // `partial_markdown` is its sanitized form, "" when nothing was accumulated.
  partialMarkdown = "",
): JobRecord {
  return jobs.recordJobWithUsage(scope, {
    job: failedJobInput({
      projectId: target.seed.projectId,
      documentId: target.seed.documentId,
      kind: "proposal",
      operation: target.seed.operation,
      provider: target.seed.provider,
      model: "",
      requestJson: target.seed.requestJson,
      resultJson: dumpJson({
        proposal_markdown: "",
        partial_markdown: sanitizeProposalMarkdown(partialMarkdown),
        base_revision_id: target.revisionId,
        accepted_revision_id: null,
      }),
      error: message,
      requestIdempotencyKey: target.seed.requestKey ?? null,
      now: target.seed.now,
    }),
    usage: unreportedAttemptUsage({
      provider: target.seed.provider,
      requestEvidenceJson: dumpJson({
        operation: target.seed.operation,
        base_revision_id: target.revisionId,
      }),
    }),
  });
}

/**
 * DR-027 replay projection: the stored terminal outcome of a request-key
 * generation as the exact stream frame the normal completion path emits — the
 * `done` frame carrying the stored job payload for a completed job, the
 * shared `error` frame for a failed one. A stored job with no terminal
 * outcome is a protocol violation and throws instead of inventing a frame.
 */
export function replayedProposalFrame(job: JobRecord): ProposalStreamFramePayload {
  if (job.status === "completed") return { type: "done", job: jobPayload(job) };
  if (job.status === "failed" && job.error !== null) {
    return { type: "error", error: { code: "PROVIDER_FAILED", message: job.error } };
  }
  throw new InvalidOperationError(`Stored request-key job has no terminal outcome: ${job.id}.`);
}
