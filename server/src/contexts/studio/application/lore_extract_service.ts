import type {
  TextGenerationExecutionOptions,
  TextGenerationProvider,
  TextGenerationProviderFactory,
  TextGenerationTask,
  TextProviderName,
} from "../../../contexts/ai/application/ports/text_generation.js";
import type { Principal } from "../../../shared/application/ports/auth.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import { resolvedTokenUsage, rowTokenSource, unreportedAttemptUsage } from "./attempt_usage.js";
import { failedJobInput } from "./failed_job_input.js";
import {
  assertLoreExtractSegmentCapacity,
  buildLoreExtractTask,
  type LoreExtractCandidate,
  validatedLoreCandidates,
} from "./lore_extract_task.js";
import { dumpJson, jobPayload, safeLoadJson } from "./payloads.js";
import type { StudioJobLedgerStore } from "./ports/job_ledger_store.js";
import type { AttemptUsageInput, JobRecord } from "./ports/job_records.js";
import type { ProjectScope } from "./ports/studio_store.js";
import { scopeForPrincipal } from "./ports/studio_store.js";
import { admitTextProvider } from "./proposal_admission.js";
import { disposeProvider, type ProviderCleanupFailureReporter } from "./provider_disposal.js";
import { firstRunFailureDisposition } from "./studio_failure_classification.js";

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
  readonly execution?: TextGenerationExecutionOptions | undefined;
  readonly scope: ProjectScope;
  readonly retry: JobRecord;
  readonly reportCleanupFailure: ProviderCleanupFailureReporter;
  readonly now: () => Date;
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

/**
 * The labelled usage row of one completed extraction (DR-028): reported counts
 * are written as `provider`, an absent report falls back to the shared word
 * count and is written as `estimated` — never as an unlabelled number.
 */
function completedExtractionUsage(
  outcome: ExtractionOutcome,
  evidence: {
    readonly provider: string;
    readonly promptText: string;
    readonly completionText: string;
    readonly requestEvidenceJson: string;
  },
): AttemptUsageInput {
  const prompt = resolvedTokenUsage(outcome.promptTokens, evidence.promptText);
  const completion = resolvedTokenUsage(outcome.completionTokens, evidence.completionText);
  return {
    provider: evidence.provider,
    model: outcome.model,
    promptTokens: prompt.tokens,
    completionTokens: completion.tokens,
    outcome: "completed",
    tokenSource: rowTokenSource(prompt.source, completion.source),
    requestEvidenceJson: evidence.requestEvidenceJson,
  };
}

/** Run one admitted segment through the provider; the caller owns the landing. */
async function generateLoreCandidates(
  providerFactory: TextGenerationProviderFactory,
  providerName: TextProviderName,
  task: TextGenerationTask,
  reportCleanupFailure: ProviderCleanupFailureReporter,
  execution?: TextGenerationExecutionOptions,
): Promise<ExtractionOutcome> {
  let provider: TextGenerationProvider | undefined;
  try {
    provider = providerFactory(providerName);
    const result = await provider.generateStructured(task, execution);
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
   * job row or provider exists; a provider failure lands one failed job plus
   * its zero-token `unreported` usage row; a completed provider request lands
   * one completed job plus one labelled usage row, atomically.
   */
  async extractSegment(
    principal: Principal,
    projectId: string,
    input: LoreExtractSegmentInput,
    reportCleanupFailure: ProviderCleanupFailureReporter,
    execution?: TextGenerationExecutionOptions,
  ): Promise<Record<string, unknown>> {
    const scope = scopeForPrincipal(principal);
    const providerName = admitTextProvider(input.provider);
    const codePoints = assertLoreExtractSegmentCapacity(input.segment);
    const task = buildLoreExtractTask(input.segment);
    const requestJson = dumpJson({ segment: input.segment });
    const requestEvidenceJson = dumpJson({ operation: "extract", segment_code_points: codePoints });
    try {
      const outcome = await generateLoreCandidates(
        this.providerFactory,
        providerName,
        task,
        reportCleanupFailure,
        execution,
      );
      const resultJson = dumpJson({
        candidates: outcome.candidates,
        ...(providerName === "acp" && execution?.agentExecution !== undefined
          ? { agent_execution: execution.agentExecution }
          : {}),
      });
      return jobPayload(
        this.jobs.recordJobWithUsage(scope, {
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
          usage: completedExtractionUsage(outcome, {
            provider: providerName,
            promptText: input.segment,
            completionText: resultJson,
            requestEvidenceJson,
          }),
        }),
      );
    } catch (error) {
      const disposition = firstRunFailureDisposition(error, "lore-extract");
      if (disposition.kind === "propagate") {
        throw error;
      }
      return jobPayload(
        this.jobs.recordJobWithUsage(scope, {
          job: failedJobInput({
            projectId,
            documentId: null,
            kind: "lore-extract",
            operation: "extract",
            provider: providerName,
            model: "",
            requestJson,
            resultJson: dumpJson({
              candidates: [],
              ...(providerName === "acp" && execution?.agentExecution !== undefined
                ? { agent_execution: execution.agentExecution }
                : {}),
            }),
            error: disposition.failure.message,
            now: this.now(),
          }),
          usage: unreportedAttemptUsage({ provider: providerName, requestEvidenceJson }),
        }),
      );
    }
  }

  /**
   * Retry of a claimed lore-extract job: the stored segment is recovered and
   * re-admitted (segment cap, assembled prompt bytes) before the provider
   * runs, and the landing transitions the reserved retry row plus exactly
   * one labelled usage row, atomically. A lost stored request context refuses
   * the retry; provider failures propagate to the retry executor's failed-job
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
      request.execution,
    );
    const resultJson = dumpJson({
      candidates: outcome.candidates,
      ...(providerName === "acp" && request.execution?.agentExecution !== undefined
        ? { agent_execution: request.execution.agentExecution }
        : {}),
    });
    return this.jobs.markJobOutcomeWithUsage(request.scope, retry.projectId, retry.id, {
      outcome: {
        status: "completed",
        model: outcome.model,
        resultJson,
        error: null,
        eventDetailsJson: dumpJson({ candidates_count: outcome.candidates.length }),
        now: request.now(),
      },
      usage: completedExtractionUsage(outcome, {
        provider: providerName,
        promptText: segment,
        completionText: resultJson,
        requestEvidenceJson: dumpJson({
          operation: "extract",
          segment_code_points: codePoints,
        }),
      }),
    });
  }
}
