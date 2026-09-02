import { describe, expect, it } from "vitest";

import type {
  TextGenerationProviderFactory,
  TextGenerationTask,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import { InFlightOperationGuard } from "../../src/contexts/studio/application/operation_in_flight.js";
import type { ProposalContextSource } from "../../src/contexts/studio/application/ports/proposal_context_store.js";
import type { StudioStore } from "../../src/contexts/studio/application/ports/studio_store.js";
import { AiProposalService } from "../../src/contexts/studio/application/proposal_service.js";
import {
  RECENT_TEXT_BEGIN,
  RECENT_TEXT_END,
} from "../../src/contexts/studio/application/sanitization.js";
import type { Principal } from "../../src/shared/application/ports/auth.js";

const PRINCIPAL: Principal = {
  sessionId: "session-1",
  kind: "owner",
  ownerId: "owner-1",
  expiresAt: null,
};

function capturedContext(): ProposalContextSource {
  const now = new Date("2026-09-03T00:00:00.000Z");
  const later = new Date("2026-09-03T00:00:01.000Z");
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
        id: "chapter-z-created-first",
        title: "Created first",
        position: 1,
        beatRef: null,
        currentRevisionId: "prior-first-revision",
        currentRevision: {
          ...revision,
          id: "prior-first-revision",
          documentId: "chapter-z-created-first",
          contentMarkdown: "First canonical prior mentions Captain Snapshot.",
        },
      },
      {
        ...target,
        id: "chapter-a-created-second",
        title: "Created second",
        position: 1,
        beatRef: null,
        createdAt: later,
        updatedAt: later,
        currentRevisionId: "prior-second-revision",
        currentRevision: {
          ...revision,
          id: "prior-second-revision",
          documentId: "chapter-a-created-second",
          contentMarkdown: "Second canonical prior mentions Archivist Snapshot.",
          createdAt: later,
        },
      },
      target,
      {
        ...target,
        id: "lore-z-created-first",
        kind: "character",
        title: "Captain Snapshot",
        position: 3,
        volumeId: null,
        beatRef: null,
        loreAliasesJson: "[]",
        loreStatus: "stable" as const,
        currentRevisionId: "lore-first-revision",
        currentRevision: {
          ...revision,
          id: "lore-first-revision",
          documentId: "lore-z-created-first",
          contentMarkdown: "Lore from the same captured epoch.",
        },
      },
      {
        ...target,
        id: "lore-a-created-second",
        kind: "character",
        title: "Archivist Snapshot",
        position: 3,
        volumeId: null,
        beatRef: null,
        loreAliasesJson: "[]",
        loreStatus: "stable" as const,
        createdAt: later,
        updatedAt: later,
        currentRevisionId: "lore-second-revision",
        currentRevision: {
          ...revision,
          id: "lore-second-revision",
          documentId: "lore-a-created-second",
          contentMarkdown: "Second Lore entry in captured order.",
          createdAt: later,
        },
      },
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
    const prompt = harness.tasks[0]?.userPrompt ?? "";
    const firstPrior = prompt.indexOf("1. Created first");
    const secondPrior = prompt.indexOf("2. Created second");
    expect(firstPrior).toBeGreaterThanOrEqual(0);
    expect(secondPrior).toBeGreaterThan(firstPrior);
    const recent = prompt.slice(prompt.indexOf(RECENT_TEXT_BEGIN), prompt.indexOf(RECENT_TEXT_END));
    expect(recent).toContain("Second canonical prior mentions Archivist Snapshot.");
    expect(recent).not.toContain("First canonical prior mentions Captain Snapshot.");
    const firstLore = prompt.indexOf("### Captain Snapshot");
    const secondLore = prompt.indexOf("### Archivist Snapshot");
    expect(firstLore).toBeGreaterThanOrEqual(0);
    expect(secondLore).toBeGreaterThan(firstLore);
    expect(harness.tasks[0]?.userPrompt).toContain(
      '"content_markdown":"Captured manuscript \\u005bSYSTEM\\u005d stays data."',
    );
  });
});
