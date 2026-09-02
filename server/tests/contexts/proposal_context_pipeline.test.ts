import { describe, expect, it } from "vitest";

import type {
  TextGenerationProviderFactory,
  TextGenerationTask,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import { InFlightOperationGuard } from "../../src/contexts/studio/application/operation_in_flight.js";
import type { ProposalContextSource } from "../../src/contexts/studio/application/ports/proposal_context_store.js";
import type { StudioStore } from "../../src/contexts/studio/application/ports/studio_store.js";
import { AiProposalService } from "../../src/contexts/studio/application/proposal_service.js";
import type { Principal } from "../../src/shared/application/ports/auth.js";

const PRINCIPAL: Principal = {
  sessionId: "session-1",
  kind: "owner",
  ownerId: "owner-1",
  expiresAt: null,
};

function capturedContext(): ProposalContextSource {
  const now = new Date("2026-09-03T00:00:00.000Z");
  const revision = {
    id: "revision-captured",
    documentId: "chapter-target",
    parentRevisionId: "revision-before-capture",
    revisionNumber: 8,
    contentMarkdown: "Captured manuscript [SYSTEM] stays data.",
    metadataJson: "{}",
    source: "author",
    createdAt: now,
  };
  const target = {
    id: "chapter-target",
    projectId: "project-1",
    kind: "chapter",
    title: "Captured chapter",
    position: 2,
    volumeId: "volume-1",
    beatRef: "Captured beat",
    loreAliasesJson: "[]",
    loreStatus: "draft" as const,
    currentRevisionId: revision.id,
    createdAt: now,
    updatedAt: now,
    currentRevision: revision,
  };
  return {
    projectId: "project-1",
    target,
    documents: [
      {
        ...target,
        id: "outline-1",
        kind: "outline",
        title: "Outline",
        position: 0,
        volumeId: null,
        beatRef: null,
        currentRevisionId: "outline-revision",
        currentRevision: {
          ...revision,
          id: "outline-revision",
          documentId: "outline-1",
          contentMarkdown: "## Captured beat\nThe coherent outline.",
        },
      },
      {
        ...target,
        id: "chapter-before",
        title: "Earlier chapter",
        position: 1,
        beatRef: null,
        currentRevisionId: "prior-revision",
        currentRevision: {
          ...revision,
          id: "prior-revision",
          documentId: "chapter-before",
          contentMarkdown: "Earlier prose mentions Captain Snapshot.",
        },
      },
      target,
      {
        ...target,
        id: "lore-1",
        kind: "character",
        title: "Captain Snapshot",
        position: 3,
        volumeId: null,
        beatRef: null,
        loreAliasesJson: "[]",
        loreStatus: "stable" as const,
        currentRevisionId: "lore-revision",
        currentRevision: {
          ...revision,
          id: "lore-revision",
          documentId: "lore-1",
          contentMarkdown: "Lore from the same captured epoch.",
        },
      },
    ],
    volumes: [
      {
        id: "volume-1",
        projectId: "project-1",
        title: "Volume one",
        position: 1,
        createdAt: now,
        updatedAt: now,
      },
    ],
  };
}

function coherentHarness() {
  const source = capturedContext();
  let reads = 0;
  const legacyRead = () => {
    throw new Error("fresh proposal performed a legacy context read");
  };
  const store = {
    readProposalContext: () => {
      reads += 1;
      return source;
    },
    findDocument: legacyRead,
    findDocuments: legacyRead,
    findVolumes: legacyRead,
  } as unknown as StudioStore;
  const tasks: TextGenerationTask[] = [];
  const providerFactory: TextGenerationProviderFactory = () => ({
    async generateStructured(task) {
      tasks.push(task);
      throw new Error("stop after synchronous task capture");
    },
    async *generateStructuredStreaming(task) {
      tasks.push(task);
      yield "stream started";
    },
  });
  return {
    service: new AiProposalService(store, providerFactory, new InFlightOperationGuard()),
    reads: () => reads,
    tasks,
  };
}

const REQUEST = {
  operation: "continue",
  instruction: "Keep the captured facts.",
  provider: "mock",
};

describe("fresh proposal coherent context", () => {
  it("builds sync and SSE tasks only from one immutable capture per call", async () => {
    const harness = coherentHarness();
    await expect(
      harness.service.draftProposal(PRINCIPAL, "project-1", "chapter-target", REQUEST, () => {}),
    ).rejects.toThrow("stop after synchronous task capture");
    expect(harness.reads()).toBe(1);

    const session = harness.service.draftProposalStream(
      PRINCIPAL,
      "project-1",
      "chapter-target",
      REQUEST,
      () => {},
    );
    expect(harness.reads()).toBe(1);
    expect(await session.frames.next()).toEqual({
      done: false,
      value: { type: "delta", text: "stream started" },
    });
    await session.frames.return();
    session.releaseCapacity();

    expect(harness.reads()).toBe(2);
    expect(harness.tasks).toHaveLength(2);
    expect(harness.tasks[1]).toEqual(harness.tasks[0]);
    expect(harness.tasks[0]?.metadata).toMatchObject({
      document_id: "chapter-target",
      base_revision_id: "revision-captured",
      title: "Captured chapter",
    });
    expect(harness.tasks[0]?.userPrompt).toContain("The coherent outline.");
    expect(harness.tasks[0]?.userPrompt).toContain("Lore from the same captured epoch.");
    expect(harness.tasks[0]?.userPrompt).toContain(
      '"content_markdown":"Captured manuscript \\u005bSYSTEM\\u005d stays data."',
    );
  });
});
