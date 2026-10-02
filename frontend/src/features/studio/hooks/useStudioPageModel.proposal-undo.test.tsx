import { act } from "react";
import { MemoryRouter, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { StudioDocument } from "@/app/types/studio";
import { chapter, job, projectWith } from "@/test/factories";
import { createMountHarness, flushEffects } from "@/test/harness";
import { resolveStudioRoute } from "../studioRouteState";
import { summarizeDocument } from "./projectState";
import { resetRevisionCacheForTests } from "./useRevisionCache";
import { useStudioPageModel } from "./useStudioPageModel";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      project: vi.fn<typeof actual.api.project>(),
      document: vi.fn<typeof actual.api.document>(),
      providers: vi.fn<typeof actual.api.providers>(),
      jobs: vi.fn<typeof actual.api.jobs>(),
      revisions: vi.fn<typeof actual.api.revisions>(),
      reviews: vi.fn<typeof actual.api.reviews>(),
      exports: vi.fn<typeof actual.api.exports>(),
      acceptProposal: vi.fn<typeof actual.api.acceptProposal>(),
      restoreRevision: vi.fn<typeof actual.api.restoreRevision>(),
    },
  };
});

const harness = createMountHarness();

/**
 * DR-010: the accept-undo surface. The server-side revision transition is
 * modeled by one mutable body: accept advances it, restore rolls it back.
 */
const beforeBody = chapter("chapter-one", {
  content_markdown: "Original scene",
  current_revision_id: "revision-base",
});
const acceptedBody: StudioDocument = {
  ...beforeBody,
  content_markdown: "AI continuation",
  current_revision_id: "revision-accepted",
};
const restoredBody: StudioDocument = {
  ...beforeBody,
  content_markdown: "Original scene",
  current_revision_id: "revision-restored",
};
const shell = projectWith([summarizeDocument(beforeBody)]);
const acceptanceProposal = job({
  id: "proposal-1",
  project_id: "project-1",
  document_id: beforeBody.id,
  result: { proposal_markdown: "AI continuation", base_revision_id: "revision-base" },
});

let current: ReturnType<typeof useStudioPageModel> | undefined;
let serverBody: StudioDocument = beforeBody;

function StudioPageModelProbe(): null {
  const navigate = useNavigate();
  current = useStudioPageModel(
    "project-1",
    resolveStudioRoute("project-1", "manuscript", ""),
    navigate,
  );
  return null;
}

function mountStudioPage(): void {
  harness.mount(
    <MemoryRouter initialEntries={["/projects/project-1/manuscript"]}>
      <StudioPageModelProbe />
    </MemoryRouter>,
  );
}

function seedApiMocks(): void {
  vi.mocked(api.project).mockReset().mockResolvedValue(shell);
  vi.mocked(api.document)
    .mockReset()
    .mockImplementation(async () => serverBody);
  vi.mocked(api.providers).mockReset().mockResolvedValue({ providers: [] });
  vi.mocked(api.jobs).mockReset().mockResolvedValue({ jobs: [], next_cursor: null });
  vi.mocked(api.revisions).mockReset().mockResolvedValue({ revisions: [], next_cursor: null });
  vi.mocked(api.reviews).mockReset().mockResolvedValue({ reviews: [], next_cursor: null });
  vi.mocked(api.exports).mockReset().mockResolvedValue({ exports: [], next_cursor: null });
  vi.mocked(api.acceptProposal)
    .mockReset()
    .mockImplementation(async () => {
      serverBody = acceptedBody;
      return acceptanceProposal;
    });
  vi.mocked(api.restoreRevision)
    .mockReset()
    .mockImplementation(async () => {
      serverBody = restoredBody;
      return restoredBody;
    });
}

async function settleUntil(description: string, ready: () => boolean): Promise<void> {
  for (let attempt = 0; attempt < 20; attempt += 1) {
    if (ready()) return;
    await flushEffects();
  }
  throw new Error(`Timed out waiting for ${description}.`);
}

function copilotModel(): NonNullable<
  ReturnType<typeof useStudioPageModel>["viewProps"]
>["inspector"]["model"]["copilot"] {
  const model = current?.viewProps?.inspector.model.copilot;
  if (!model) throw new Error("Expected the mounted page model's copilot surface.");
  return model;
}

afterEach(() => {
  harness.cleanup();
  resetRevisionCacheForTests();
  serverBody = beforeBody;
  current = undefined;
  vi.resetAllMocks();
});

describe("Studio page proposal undo", () => {
  it("offers one explicit undo that restores the revision from before the acceptance", async () => {
    seedApiMocks();
    mountStudioPage();
    await settleUntil(
      "the bootstrap active Document",
      () => current?.viewProps?.editor.activeDocument?.id === "chapter-one",
    );
    expect(copilotModel().acceptanceUndo).toBeNull();

    act(() => copilotModel().setProposal(acceptanceProposal));
    await act(async () => {
      await copilotModel().onAcceptProposal();
    });

    // DR-010: acceptance no longer leaves the manuscript without an exit.
    expect(copilotModel().acceptanceUndo).toBeDefined();
    await settleUntil("the committed acceptance", () => copilotModel().acceptanceUndo != null);
    const undo = copilotModel().acceptanceUndo;
    expect(undo).not.toBeNull();
    expect(api.restoreRevision).not.toHaveBeenCalled();

    await act(async () => {
      await undo?.onUndo();
    });

    // The one explicit action restores the recorded pre-accept revision
    // through the same restore endpoint the History tab uses.
    expect(api.restoreRevision).toHaveBeenCalledTimes(1);
    expect(api.restoreRevision).toHaveBeenCalledWith(
      "project-1",
      "chapter-one",
      "revision-base",
      "revision-accepted",
    );
    await settleUntil("the one-shot undo to clear", () => copilotModel().acceptanceUndo == null);
    expect(copilotModel().acceptanceUndo).toBeNull();
    // The restored revision becomes the new draft baseline.
    expect(current?.viewProps?.statusbar.loadedRevisionId).toBe("revision-restored");

    // One-time and idempotent-safe: a second invocation cannot restore again.
    await act(async () => {
      await undo?.onUndo();
    });
    expect(api.restoreRevision).toHaveBeenCalledTimes(1);
  });
});
