import { describe, expect, it } from "vitest";
import { TextGenerationProviderError } from "../../src/contexts/ai/application/ports/text_generation.js";
import { DeterministicStoryProvider } from "../../src/contexts/ai/infrastructure/providers/deterministic_story_provider.js";
import { INVALID_LORE_CANDIDATES } from "../../src/contexts/studio/application/lore_extract_task.js";
import { revisionWordCount } from "../../src/contexts/studio/domain/revision_word_count.js";
import {
  candidateResult,
  openLorebookInitHarness,
  resultCandidates,
  scriptedFactory,
  usageRequests,
} from "./lorebook_init_harness.js";

/**
 * Fresh-extraction coverage of the lorebook initialization wizard (#614):
 * the trial-provider placeholder set, the provider-failure boundary, and
 * usage singularity across independent segments. Capacity refusals live in
 * `lorebook_init_capacity.test.ts`; the retry chain in
 * `lorebook_init_retry.test.ts`.
 */
describe("lorebook wizard extraction pipeline", () => {
  it("returns the fixed placeholder candidate set on the trial provider", async () => {
    const { cleanup, jobs, principal, projectId, scope, service } = await openLorebookInitHarness(
      () => new DeterministicStoryProvider("mock"),
    );
    try {
      const segment = "Mira met Tomas at the flood market.";
      const payload = await service.extractSegment(
        principal,
        projectId,
        { provider: "mock", segment },
        () => undefined,
      );

      expect(payload).toMatchObject({
        kind: "lore-extract",
        operation: "extract",
        status: "completed",
        provider: "mock",
        document_id: null,
      });
      const candidates = resultCandidates(payload) as Array<{
        kind: string;
        title: string;
        summary: string;
      }>;
      expect(candidates.map((candidate) => candidate.kind)).toEqual(["character", "world"]);
      expect(candidates.map((candidate) => candidate.title)).toEqual([
        "Placeholder Character",
        "Placeholder World",
      ]);
      for (const candidate of candidates) {
        expect(candidate.summary).toContain("trial provider");
      }
      // Exactly one usage event per completed provider request; absent
      // provider tokens fall back to the exact word count.
      const usage = jobs.aggregateProjectUsage(scope, projectId, new Date());
      expect(usage.requestCount).toBe(1);
      expect(usage.perModel[0]?.promptTokens).toBe(revisionWordCount(segment));
    } finally {
      await cleanup();
    }
  });

  it("lands one failed job without usage when the provider fails", async () => {
    const failure = new TextGenerationProviderError(
      "DashScope generation failed for step 'lore_extract'",
    );
    const { factory } = scriptedFactory(async () => {
      throw failure;
    });
    const { cleanup, jobs, principal, projectId, scope, service } =
      await openLorebookInitHarness(factory);
    try {
      const payload = await service.extractSegment(
        principal,
        projectId,
        { provider: "mock", segment: "a quiet rumour at the archive stair" },
        () => undefined,
      );

      expect(payload).toMatchObject({
        kind: "lore-extract",
        operation: "extract",
        status: "failed",
        model: "",
      });
      expect(payload.error).toBe(failure.message);
      expect(resultCandidates(payload)).toEqual([]);
      expect(usageRequests(jobs, scope, projectId)).toBe(0);
    } finally {
      await cleanup();
    }
  });

  it("fails a schema-violating candidate response with the fixed message", async () => {
    const { factory } = scriptedFactory(async () => candidateResult(42));
    const { cleanup, principal, projectId, service } = await openLorebookInitHarness(factory);
    try {
      const payload = await service.extractSegment(
        principal,
        projectId,
        { provider: "mock", segment: "the ledger page names its collector" },
        () => undefined,
      );

      expect(payload).toMatchObject({ status: "failed", error: INVALID_LORE_CANDIDATES });
    } finally {
      await cleanup();
    }
  });

  it("records one usage event per completed segment and keeps segments independent", async () => {
    const { calls, factory } = scriptedFactory(async (task) =>
      candidateResult([
        {
          kind: "character",
          title: task.userPrompt.includes("alpha") ? "Alpha Lead" : "Beta Lead",
          aliases: ["Lead"],
          summary: "Extracted from its own segment.",
        },
      ]),
    );
    const { cleanup, jobs, principal, projectId, scope, service } =
      await openLorebookInitHarness(factory);
    try {
      const first = await service.extractSegment(
        principal,
        projectId,
        { provider: "mock", segment: "alpha walks into the observatory" },
        () => undefined,
      );
      const second = await service.extractSegment(
        principal,
        projectId,
        { provider: "mock", segment: "beta keeps the blackout map" },
        () => undefined,
      );

      expect(first.id).not.toBe(second.id);
      expect(resultCandidates(first)).toEqual([
        {
          kind: "character",
          title: "Alpha Lead",
          aliases: ["Lead"],
          summary: "Extracted from its own segment.",
        },
      ]);
      expect(resultCandidates(second)).toEqual([
        {
          kind: "character",
          title: "Beta Lead",
          aliases: ["Lead"],
          summary: "Extracted from its own segment.",
        },
      ]);
      expect(calls).toHaveLength(2);
      expect(usageRequests(jobs, scope, projectId)).toBe(2);
    } finally {
      await cleanup();
    }
  });
});
