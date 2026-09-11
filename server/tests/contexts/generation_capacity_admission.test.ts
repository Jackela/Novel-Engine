import { describe, expect, it } from "vitest";

import type { TextGenerationProviderFactory } from "../../src/contexts/ai/application/ports/text_generation.js";
import { GENERATION_PROMPT_BYTE_LIMIT } from "../../src/contexts/studio/application/generation_capacity.js";
import { InFlightOperationGuard } from "../../src/contexts/studio/application/operation_in_flight.js";
import type { StudioJobLedgerStore } from "../../src/contexts/studio/application/ports/job_ledger_store.js";
import type { ProposalAcceptanceStore } from "../../src/contexts/studio/application/ports/proposal_acceptance_store.js";
import type { ProposalContextStore } from "../../src/contexts/studio/application/ports/proposal_context_store.js";
import type { DocumentWithCurrent } from "../../src/contexts/studio/application/ports/studio_store.js";
import { ProposalGenerationPipeline } from "../../src/contexts/studio/application/proposal_pipeline.js";
import { AiProposalService } from "../../src/contexts/studio/application/proposal_service.js";
import { GenerationCapacityExceededError } from "../../src/contexts/studio/domain/exceptions.js";
import type { Principal } from "../../src/shared/application/ports/auth.js";

const PRINCIPAL: Principal = {
  sessionId: "session-1",
  kind: "owner",
  ownerId: "owner-1",
  expiresAt: null,
};

function oversizedDocument(): DocumentWithCurrent {
  const now = new Date("2026-09-03T00:00:00.000Z");
  const revision = {
    id: "revision-1",
    documentId: "document-1",
    parentRevisionId: null,
    revisionNumber: 1,
    contentMarkdown: "a".repeat(GENERATION_PROMPT_BYTE_LIMIT),
    metadataJson: "{}",
    source: "author",
    wordCount: 0,
    createdAt: now,
  };
  return {
    id: "document-1",
    projectId: "project-1",
    kind: "chapter",
    title: "Chapter 1",
    position: 1,
    volumeId: null,
    beatRef: null,
    loreAliasesJson: "[]",
    loreStatus: "draft",
    currentRevisionId: revision.id,
    createdAt: now,
    updatedAt: now,
    currentRevision: revision,
  };
}

function admissionHarness(): {
  readonly service: AiProposalService;
  readonly factoryCalls: () => number;
  readonly generationCalls: () => number;
} {
  const document = oversizedDocument();
  const proposalContext = {
    readProposalContext: () => ({
      projectId: document.projectId,
      target: document,
      documents: [document],
      volumes: [],
    }),
  } as unknown as ProposalContextStore;
  const unusedJobs = {
    addJob: () => {
      throw new Error("admission refusal must not record jobs");
    },
    recordCompletedProposalJob: () => {
      throw new Error("admission refusal must not record jobs");
    },
  } as unknown as StudioJobLedgerStore;
  const unusedAcceptance = {
    acceptCompletedProposal: () => {
      throw new Error("admission refusal must not accept proposals");
    },
  } as unknown as ProposalAcceptanceStore;
  let factoryCalls = 0;
  let generationCalls = 0;
  const providerFactory: TextGenerationProviderFactory = () => {
    factoryCalls += 1;
    return {
      async generateStructured() {
        generationCalls += 1;
        throw new Error("oversized prompt reached provider generation");
      },
      async *generateStructuredStreaming() {
        generationCalls += 1;
        yield "oversized prompt reached provider streaming";
      },
    };
  };
  return {
    service: new AiProposalService(
      unusedAcceptance,
      new ProposalGenerationPipeline(
        proposalContext,
        unusedJobs,
        providerFactory,
        new InFlightOperationGuard(),
      ),
    ),
    factoryCalls: () => factoryCalls,
    generationCalls: () => generationCalls,
  };
}

const REQUEST = { operation: "continue", instruction: "", provider: "mock" };

describe("fresh proposal prompt admission", () => {
  it("refuses synchronous generation before constructing a Provider", async () => {
    const harness = admissionHarness();

    await expect(
      harness.service.draftProposal(PRINCIPAL, "project-1", "document-1", REQUEST, () => {}),
    ).rejects.toBeInstanceOf(GenerationCapacityExceededError);
    expect(harness.factoryCalls()).toBe(0);
    expect(harness.generationCalls()).toBe(0);
  });

  it("refuses an SSE session before constructing a Provider", async () => {
    const harness = admissionHarness();
    const session = harness.service.draftProposalStream(
      PRINCIPAL,
      "project-1",
      "document-1",
      REQUEST,
      () => {},
    );

    await expect(session.frames.next()).rejects.toBeInstanceOf(GenerationCapacityExceededError);
    session.releaseCapacity();
    expect(harness.factoryCalls()).toBe(0);
    expect(harness.generationCalls()).toBe(0);
  });
});
