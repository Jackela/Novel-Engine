import { describe, expect, it } from "vitest";
import {
  buildLoreExtractTask,
  MAX_LORE_EXTRACT_SEGMENT_CODE_POINTS,
} from "../../src/contexts/studio/application/lore_extract_task.js";
import { jobPageLimit } from "../../src/contexts/studio/application/ports/job_records.js";
import { GenerationCapacityExceededError } from "../../src/contexts/studio/domain/exceptions.js";
import { GENERATION_PROMPT_BYTE_LIMIT } from "../../src/contexts/studio/domain/generation_capacity_policy.js";
import {
  candidateResult,
  openLorebookInitHarness,
  scriptedFactory,
  usageRequests,
} from "./lorebook_init_harness.js";

/**
 * Capacity coverage of the lorebook initialization wizard (#614): the fixed
 * per-segment code-point cap and the shared assembled-prompt byte authority
 * both fail closed with the stable generation-capacity envelope, bounded to
 * the limit plus one, before any provider construction, job evidence, or
 * usage — never through silent truncation.
 */
describe("lorebook wizard extraction capacity", () => {
  it("admits segments at the 99,999 and 100,000 code-point boundaries", async () => {
    const { calls, factory } = scriptedFactory(async () => candidateResult([]));
    const { cleanup, principal, projectId, service } = await openLorebookInitHarness(factory);
    try {
      for (const length of [99_999, MAX_LORE_EXTRACT_SEGMENT_CODE_POINTS]) {
        const payload = await service.extractSegment(
          principal,
          projectId,
          { provider: "mock", segment: "a".repeat(length) },
          () => undefined,
        );
        expect(payload).toMatchObject({ kind: "lore-extract", status: "completed" });
      }
      expect(calls).toHaveLength(2);
    } finally {
      await cleanup();
    }
  });

  it("refuses a 100,001-code-point segment with the bounded capacity envelope", async () => {
    const { calls, factory } = scriptedFactory(async () => candidateResult([]));
    const { cleanup, jobs, principal, projectId, scope, service } =
      await openLorebookInitHarness(factory);
    try {
      const refusal = await service
        .extractSegment(
          principal,
          projectId,
          { provider: "mock", segment: "a".repeat(MAX_LORE_EXTRACT_SEGMENT_CODE_POINTS + 1) },
          () => undefined,
        )
        .catch((error: unknown) => error);

      expect(refusal).toBeInstanceOf(GenerationCapacityExceededError);
      expect(refusal).toMatchObject({
        resource: "lore_extract_segment",
        limit: MAX_LORE_EXTRACT_SEGMENT_CODE_POINTS,
        observed: MAX_LORE_EXTRACT_SEGMENT_CODE_POINTS + 1,
      });
      // The refusal precedes provider construction, job evidence, and usage.
      expect(calls).toHaveLength(0);
      const page = jobs.collectProjectJobSummaries(scope, projectId, { limit: jobPageLimit(50) });
      expect(page.jobs).toHaveLength(0);
      expect(usageRequests(jobs, scope, projectId)).toBe(0);
    } finally {
      await cleanup();
    }
  });

  it("bounds an oversized segment's observed value at the limit plus one", async () => {
    const { factory } = scriptedFactory(async () => candidateResult([]));
    const { cleanup, principal, projectId, service } = await openLorebookInitHarness(factory);
    try {
      const refusal = await service
        .extractSegment(
          principal,
          projectId,
          { provider: "mock", segment: "a".repeat(MAX_LORE_EXTRACT_SEGMENT_CODE_POINTS * 2) },
          () => undefined,
        )
        .catch((error: unknown) => error);

      expect(refusal).toMatchObject({
        resource: "lore_extract_segment",
        limit: MAX_LORE_EXTRACT_SEGMENT_CODE_POINTS,
        observed: MAX_LORE_EXTRACT_SEGMENT_CODE_POINTS + 1,
      });
    } finally {
      await cleanup();
    }
  });

  it("refuses an assembled extraction prompt over the shared byte authority", () => {
    const refusal = (() => {
      try {
        return buildLoreExtractTask("y".repeat(GENERATION_PROMPT_BYTE_LIMIT + 1));
      } catch (error) {
        return error;
      }
    })();

    expect(refusal).toBeInstanceOf(GenerationCapacityExceededError);
    expect(refusal).toMatchObject({
      resource: "prompt_bytes",
      limit: GENERATION_PROMPT_BYTE_LIMIT,
      observed: GENERATION_PROMPT_BYTE_LIMIT + 1,
    });
  });
});
