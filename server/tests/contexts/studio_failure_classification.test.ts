import { describe, expect, it } from "vitest";

import {
  ProviderNotConfiguredError,
  TextGenerationCancelledError,
  TextGenerationProviderError,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import {
  firstRunFailureDisposition,
  retryFailureDisposition,
  type StudioFirstRunChain,
  streamingFailureDisposition,
} from "../../src/contexts/studio/application/studio_failure_classification.js";
import {
  EXPORT_CAPACITY_LIMITS,
  ExportArtifactWriteError,
  ExportCapacityExceededError,
  ExportSourceInvalidatedError,
  GenerationCapacityExceededError,
  NotFoundError,
  ReviewSourceInvalidatedError,
} from "../../src/contexts/studio/domain/exceptions.js";
import { GENERATION_PROMPT_BYTE_LIMIT } from "../../src/contexts/studio/domain/generation_capacity_policy.js";
import { InvalidOperationError } from "../../src/shared/domain/exceptions.js";

/**
 * The classification matrix of the studio job chains, locked row by row: every
 * chain consult in `job_retry_executor`, `job_history_service`,
 * `proposal_pipeline`, and `lore_extract_service` reads its verdict from the
 * registry, so a table edit that moves a landing or a propagation must fail
 * here instead of silently changing what reaches the HTTP surface.
 */

const FIRST_RUN_CHAINS: readonly StudioFirstRunChain[] = [
  "proposal",
  "review",
  "export",
  "lore-extract",
];

function propagationByChain(error: unknown): Record<StudioFirstRunChain, "land" | "propagate"> {
  const verdicts = {} as Record<StudioFirstRunChain, "land" | "propagate">;
  for (const chain of FIRST_RUN_CHAINS) {
    verdicts[chain] = firstRunFailureDisposition(error, chain).kind;
  }
  return verdicts;
}

describe("studio failure classification registry", () => {
  it("lands provider failures in every provider liaising first-run chain and nowhere else", () => {
    const failure = new TextGenerationProviderError("Provider request failed.");

    expect(propagationByChain(failure)).toEqual({
      proposal: "land",
      review: "land",
      export: "propagate",
      "lore-extract": "land",
    });
    expect(firstRunFailureDisposition(failure, "proposal")).toEqual({
      kind: "land",
      failure,
    });
  });

  it("treats the unconfigured provider as a provider failure except on the stream", () => {
    const failure = new ProviderNotConfiguredError("No API key configured.");

    expect(propagationByChain(failure)).toEqual({
      proposal: "land",
      review: "land",
      export: "propagate",
      "lore-extract": "land",
    });
    // DR-022: the streaming twin must rethrow so the dedicated envelope answers.
    expect(streamingFailureDisposition(failure)).toEqual({ kind: "propagate" });
  });

  it("lands every other provider failure on the streaming twin as a failed job", () => {
    const failure = new TextGenerationProviderError("Provider request failed.");

    expect(streamingFailureDisposition(failure)).toEqual({ kind: "land", failure });
  });

  it("aborts the stream silently on a cancellation and propagates it everywhere else", () => {
    const failure = new TextGenerationCancelledError();

    expect(streamingFailureDisposition(failure)).toEqual({ kind: "abort" });
    expect(propagationByChain(failure)).toEqual({
      proposal: "propagate",
      review: "propagate",
      export: "propagate",
      "lore-extract": "propagate",
    });
    expect(retryFailureDisposition(failure, "proposal")).toEqual({ kind: "propagate" });
  });

  it("lands an invalidated review source on the review bridge and the retry chain only", () => {
    const failure = new ReviewSourceInvalidatedError();

    expect(propagationByChain(failure)).toEqual({
      proposal: "propagate",
      review: "land",
      export: "propagate",
      "lore-extract": "propagate",
    });
    expect(retryFailureDisposition(failure, "review")).toEqual({
      kind: "land",
      failure,
      providerAttributable: false,
    });
  });

  it("lands export publication failures on the export bridge and the retry chain only", () => {
    for (const failure of [new ExportSourceInvalidatedError(), new ExportArtifactWriteError()]) {
      expect(propagationByChain(failure)).toEqual({
        proposal: "propagate",
        review: "propagate",
        export: "land",
        "lore-extract": "propagate",
      });
      expect(retryFailureDisposition(failure, "export")).toEqual({
        kind: "land",
        failure,
        providerAttributable: false,
      });
    }
  });

  it("lands request-shape refusals and known misses on the retry chain only", () => {
    for (const failure of [
      new InvalidOperationError("Bad request."),
      new NotFoundError("Missing."),
    ]) {
      expect(propagationByChain(failure)).toEqual({
        proposal: "propagate",
        review: "propagate",
        export: "propagate",
        "lore-extract": "propagate",
      });
      expect(retryFailureDisposition(failure, "proposal")).toEqual({
        kind: "land",
        failure,
        providerAttributable: false,
      });
    }
  });

  it("marks provider-attributable retry landings so the usage row stays honest", () => {
    const plain = new TextGenerationProviderError("Provider request failed.");
    const unconfigured = new ProviderNotConfiguredError("No API key configured.");

    expect(retryFailureDisposition(plain, "lore-extract")).toEqual({
      kind: "land",
      failure: plain,
      providerAttributable: true,
    });
    expect(retryFailureDisposition(unconfigured, "proposal")).toEqual({
      kind: "land",
      failure: unconfigured,
      providerAttributable: true,
    });
  });

  it("retains the export capacity protocol for every retried kind", () => {
    const failure = new ExportCapacityExceededError(
      "source_bytes",
      EXPORT_CAPACITY_LIMITS.source_bytes,
      EXPORT_CAPACITY_LIMITS.source_bytes + 1,
    );

    for (const kind of ["proposal", "review", "export", "lore-extract"]) {
      expect(retryFailureDisposition(failure, kind)).toEqual({
        kind: "capacity-export",
        failure,
      });
    }
  });

  it("keeps the prompt-byte capacity protocol proposal-only, landing other kinds plainly", () => {
    const failure = new GenerationCapacityExceededError(
      "prompt_bytes",
      GENERATION_PROMPT_BYTE_LIMIT,
      GENERATION_PROMPT_BYTE_LIMIT + 1,
    );

    expect(retryFailureDisposition(failure, "proposal")).toEqual({
      kind: "capacity-generation",
      failure,
    });
    expect(retryFailureDisposition(failure, "lore-extract")).toEqual({
      kind: "land",
      failure,
      providerAttributable: false,
    });
  });

  it("propagates unknown failures through every chain untouched", () => {
    for (const failure of [new Error("Programming error."), new RangeError("Out of range."), {}]) {
      expect(propagationByChain(failure)).toEqual({
        proposal: "propagate",
        review: "propagate",
        export: "propagate",
        "lore-extract": "propagate",
      });
      expect(streamingFailureDisposition(failure)).toEqual({ kind: "propagate" });
      expect(retryFailureDisposition(failure, "proposal")).toEqual({ kind: "propagate" });
    }
  });
});
