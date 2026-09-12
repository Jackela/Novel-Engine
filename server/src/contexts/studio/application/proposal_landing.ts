import {
  isSafeUsageToken,
  type ProviderStep,
  TextGenerationProviderError,
  type TextGenerationTask,
  type TextProviderName,
} from "../../../contexts/ai/application/ports/text_generation.js";
import { revisionWordCount } from "../domain/revision_word_count.js";
import { BoundedPromptWriter } from "./generation_capacity.js";
import { loreEntriesFromDocuments } from "./lorebook.js";
import { dumpJson } from "./payloads.js";
import type { StudioJobLedgerStore } from "./ports/job_ledger_store.js";
import type { CompletedProposalUsageInput, JobRecord } from "./ports/job_records.js";
import type { ProposalContextSource } from "./ports/proposal_context_store.js";
import type { ProjectScope } from "./ports/studio_store.js";
import { assertProposalCodePointLimit, proposalCodePointCount } from "./proposal_code_points.js";
import { INVALID_PROPOSAL_PROSE, SYSTEM_PROMPT } from "./proposal_prompts.js";
import {
  buildProposalUserPrompt,
  residentContextSourceFromProposalContext,
} from "./resident_context.js";
import { isProposalMarkdownProse, sanitizeProposalMarkdown } from "./sanitization.js";

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
  SYSTEM_PROMPT,
} from "./proposal_prompts.js";
export {
  disposeProvider,
  type ProviderCleanupFailureReporter,
} from "./provider_disposal.js";

/**
 * The job/usage landing shared by every proposal pipeline (synchronous
 * draft, #308 streaming, retry): completed proposals persist one completed
 * job plus exactly one usage event, failures persist one failed job — the
 * manuscript itself is never touched here.
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
  return {
    step,
    systemPrompt: SYSTEM_PROMPT,
    userPrompt: buildProposalUserPrompt(
      {
        operation,
        instruction,
        source: residentContextSourceFromProposalContext(context),
        manuscriptMarkdown: revision.contentMarkdown,
        loreEntries: loreEntriesFromDocuments(context.documents),
        loreBudgetCharacters,
      },
      new BoundedPromptWriter(SYSTEM_PROMPT),
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

/** Invalid or absent provider usage falls back to the shared exact word count. */
export function resolvedTokenCount(reported: number | null, text: string): number {
  return isSafeUsageToken(reported) ? reported : revisionWordCount(text);
}

/** Fields every proposal job row shares before its terminal status is known. */
export interface ProposalJobSeed {
  readonly projectId: string;
  readonly documentId: string;
  readonly operation: string;
  readonly provider: TextProviderName;
  readonly requestJson: string;
  readonly now: Date;
}

/** The terminal payload shape of a completed proposal job. */
export interface ProposalLanding {
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
  return jobs.recordCompletedProposalJob(scope, {
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
export interface CompletedProposalLanding {
  readonly outcome: {
    readonly status: "completed";
    readonly model: string;
    readonly resultJson: string;
    readonly error: null;
    readonly eventDetailsJson: string;
    readonly now: Date;
  };
  readonly usage: CompletedProposalUsageInput;
}

export function completedProposalLanding(
  landing: ProposalLanding,
  evidence: { readonly operation: string; readonly revisionId: string; readonly now: Date },
): CompletedProposalLanding {
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
      promptTokens: resolvedTokenCount(landing.promptTokens, landing.instruction),
      completionTokens: resolvedTokenCount(landing.completionTokens, landing.proposal),
      requestEvidenceJson: dumpJson({
        operation: evidence.operation,
        base_revision_id: evidence.revisionId,
      }),
    },
  };
}

export function failedProposalJob(
  jobs: StudioJobLedgerStore,
  scope: ProjectScope,
  seed: ProposalJobSeed,
  revisionId: string,
  message: string,
): JobRecord {
  return jobs.addJob(scope, {
    projectId: seed.projectId,
    documentId: seed.documentId,
    kind: "proposal",
    operation: seed.operation,
    provider: seed.provider,
    status: "failed",
    model: "",
    requestJson: seed.requestJson,
    resultJson: dumpJson({
      proposal_markdown: "",
      base_revision_id: revisionId,
      accepted_revision_id: null,
    }),
    error: message,
    eventDetailsJson: dumpJson({ error: message }),
    now: seed.now,
  });
}
