import {
  isSafeUsageToken,
  type TextGenerationProvider,
  TextGenerationProviderError,
  type TextGenerationProviderFactory,
  type TextGenerationTask,
  type TextProviderName,
} from "../../../contexts/ai/application/ports/text_generation.js";
import type { Principal } from "../../../shared/application/ports/auth.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import { revisionWordCount } from "../domain/revision_word_count.js";
import { failedJobInput } from "./failed_job_input.js";
import {
  assertLoreExtractSegmentCapacity,
  buildLoreExtractTask,
  type LoreExtractCandidate,
  validatedLoreCandidates,
} from "./lore_extract_task.js";
import { dumpJson, jobPayload, safeLoadJson } from "./payloads.js";
import type { StudioJobLedgerStore } from "./ports/job_ledger_store.js";
import type { JobRecord } from "./ports/job_records.js";
import type { ProjectScope } from "./ports/studio_store.js";
import { scopeForPrincipal } from "./ports/studio_store.js";
import { admitTextProvider } from "./proposal_admission.js";
import { disposeProvider, type ProviderCleanupFailureReporter } from "./provider_disposal.js";

/**
 * The lorebook initialization wizard's extraction service (#614): one input
 * segment per call, extracted through the configured provider's structured
 * generation as its own synchronous `lore-extract` Job. A completed provider
 * request lands one completed job plus exactly one usage event in a single
 * transaction; a provider failure lands one failed job with no usage event.
 * Candidates are suggestions only — they ride the job payload and are never
 * persisted as documents, revisions, or Lore lifecycle state. The request
 * shapes and capacity refusals live in `lore_extract_task.ts`.
 */

/** Transport-decoded wizard request: one segment and the named provider. */
export interface LoreExtractSegmentInput {
  readonly provider: string;
  readonly segment: string;
}

/** A claimed lore-extract retry row plus the scope and clock executing it. */
export interface LoreExtractRetryRequest {
  readonly scope: ProjectScope;
  readonly retry: JobRecord;
  readonly reportCleanupFailure: ProviderCleanupFailureReporter;
  readonly now: () => Date;
}

/** Invalid or absent provider usage falls back to the shared exact word count. */
function resolvedTokenCount(reported: number | null, text: string): number {
  return isSafeUsageToken(reported) ? reported : revisionWordCount(text);
}

/** Recover the stored segment of a claimed retry; a lost context refuses the retry. */
export function recoverLoreExtractSegment(requestJson: string): string {
  const stored = safeLoadJson(requestJson);
  if (typeof stored.segment !== "string") {
    throw new InvalidOperationError("Original lore extraction job is missing its request context.");
  }
  return stored.segment;
}

/** The job/usage evidence of one completed provider request. */
interface ExtractionOutcome {
  readonly candidates: readonly LoreExtractCandidate[];
  readonly model: string;
  readonly promptTokens: number | null;
  readonly completionTokens: number | null;
}

/** Run one admitted segment through the provider; the caller owns the landing. */
async function generateLoreCandidates(
  providerFactory: TextGenerationProviderFactory,
  providerName: TextProviderName,
  task: TextGenerationTask,
  reportCleanupFailure: ProviderCleanupFailureReporter,
): Promise<ExtractionOutcome> {
  let provider: TextGenerationProvider | undefined;
  try {
    provider = providerFactory(providerName);
    const result = await provider.generateStructured(task);
    return {
      candidates: validatedLoreCandidates(result.content),
      model: result.model,
      promptTokens: result.promptTokens,
      completionTokens: result.completionTokens,
    };
  } finally {
    if (provider !== undefined) {
      await disposeProvider(provider, reportCleanupFailure);
    }
  }
}

export class LoreExtractService {
  constructor(
    private readonly jobs: StudioJobLedgerStore,
    private readonly providerFactory: TextGenerationProviderFactory,
    private readonly now: () => Date = () => new Date(),
  ) {}

  /**
   * Extract one wizard segment as its own synchronous `lore-extract` Job:
   * admission refusals (segment cap, assembled prompt bytes) throw before any
   * job row or provider exists; a provider failure lands one failed job; a
   * completed provider request lands one completed job plus exactly one
   * usage event, atomically.
   */
  async extractSegment(
    principal: Principal,
    projectId: string,
    input: LoreExtractSegmentInput,
    reportCleanupFailure: ProviderCleanupFailureReporter,
  ): Promise<Record<string, unknown>> {
    const scope = scopeForPrincipal(principal);
    const providerName = admitTextProvider(input.provider);
    const codePoints = assertLoreExtractSegmentCapacity(input.segment);
    const task = buildLoreExtractTask(input.segment);
    const requestJson = dumpJson({ segment: input.segment });
    try {
      const outcome = await generateLoreCandidates(
        this.providerFactory,
        providerName,
        task,
        reportCleanupFailure,
      );
      const resultJson = dumpJson({ candidates: outcome.candidates });
      return jobPayload(
        this.jobs.recordCompletedJobWithUsage(scope, {
          job: {
            projectId,
            documentId: null,
            kind: "lore-extract",
            operation: "extract",
            provider: providerName,
            status: "completed",
            model: outcome.model,
            requestJson,
            resultJson,
            error: null,
            eventDetailsJson: dumpJson({ candidates_count: outcome.candidates.length }),
            now: this.now(),
          },
          usage: {
            provider: providerName,
            model: outcome.model,
            promptTokens: resolvedTokenCount(outcome.promptTokens, input.segment),
            completionTokens: resolvedTokenCount(outcome.completionTokens, resultJson),
            requestEvidenceJson: dumpJson({
              operation: "extract",
              segment_code_points: codePoints,
            }),
          },
        }),
      );
    } catch (error) {
      if (!(error instanceof TextGenerationProviderError)) {
        throw error;
      }
      return jobPayload(
        this.jobs.addJob(
          scope,
          failedJobInput({
            projectId,
            documentId: null,
            kind: "lore-extract",
            operation: "extract",
            provider: providerName,
            model: "",
            requestJson,
            resultJson: dumpJson({ candidates: [] }),
            error: error.message,
            now: this.now(),
          }),
        ),
      );
    }
  }

  /**
   * Retry of a claimed lore-extract job: the stored segment is recovered and
   * re-admitted (segment cap, assembled prompt bytes) before the provider
   * runs, and the landing transitions the reserved retry row plus exactly
   * one usage event, atomically. A lost stored request context refuses the
   * retry; provider failures propagate to the retry executor's failed-job
   * landing, exactly like proposal retries.
   */
  async retry(request: LoreExtractRetryRequest): Promise<JobRecord> {
    const retry = request.retry;
    const segment = recoverLoreExtractSegment(retry.requestJson);
    const providerName = admitTextProvider(retry.provider);
    const codePoints = assertLoreExtractSegmentCapacity(segment);
    const task = buildLoreExtractTask(segment);
    const outcome = await generateLoreCandidates(
      this.providerFactory,
      providerName,
      task,
      request.reportCleanupFailure,
    );
    const resultJson = dumpJson({ candidates: outcome.candidates });
    return this.jobs.markJobOutcomeWithUsage(request.scope, retry.projectId, retry.id, {
      outcome: {
        status: "completed",
        model: outcome.model,
        resultJson,
        error: null,
        eventDetailsJson: dumpJson({ candidates_count: outcome.candidates.length }),
        now: request.now(),
      },
      usage: {
        provider: providerName,
        model: outcome.model,
        promptTokens: resolvedTokenCount(outcome.promptTokens, segment),
        completionTokens: resolvedTokenCount(outcome.completionTokens, resultJson),
        requestEvidenceJson: dumpJson({ operation: "extract", segment_code_points: codePoints }),
      },
    });
  }
}
