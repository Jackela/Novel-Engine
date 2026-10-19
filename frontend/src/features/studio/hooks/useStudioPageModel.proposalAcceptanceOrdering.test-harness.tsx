import { getByRole } from "@testing-library/dom";
import { act } from "react";
import { MemoryRouter, useNavigate } from "react-router-dom";
import { afterEach, beforeEach, expect, vi } from "vitest";

import { api, HttpError } from "@/app/api";
import type { StudioDocument } from "@/app/types/studio";
import { chapter, job, projectWith, revision } from "@/test/factories";
import { createMountHarness, flushEffects } from "@/test/harness";
import { StudioHistoryPanel } from "../components/StudioHistoryPanel";
import { resolveStudioRoute } from "../studioRouteState";
import { summarizeDocument } from "./projectState";
import { resetRevisionCacheForTests } from "./useRevisionCache";
import { useStudioPageModel } from "./useStudioPageModel";

const harness = createMountHarness();
export const before = chapter("chapter-one", {
  content_markdown: "Original scene",
  current_revision_id: "revision-base",
});
export const other = chapter("chapter-two", {
  content_markdown: "Other chapter",
  revision_source: "ai-accepted",
});
export const accepted = {
  ...before,
  content_markdown: "AI continuation",
  current_revision_id: "revision-accepted",
};
const restoreTarget = "older-r0";
export const restored = {
  ...before,
  current_revision_id: "revision-restored",
  content_markdown: "Earlier scene from R0",
};
export const proposal = job({
  id: "proposal-one",
  project_id: "project-1",
  document_id: before.id,
  result: {
    proposal_markdown: accepted.content_markdown,
    base_revision_id: before.current_revision_id,
  },
});
let current: ReturnType<typeof useStudioPageModel> | undefined;
let serverBody: StudioDocument;

function Probe() {
  current = useStudioPageModel(
    "project-1",
    resolveStudioRoute("project-1", "manuscript", ""),
    useNavigate(),
  );
  const props = current.viewProps;
  return props ? (
    <StudioHistoryPanel
      {...props.inspector.model.history}
      restoringRevisionId={props.inspector.pending.history?.restoringRevisionId}
    />
  ) : null;
}

export function view() {
  if (!current?.viewProps) throw new Error("Expected mounted Studio");
  return current.viewProps;
}

export function wholeBook() {
  const model = view().navigator.wholeBook;
  if (!model) throw new Error("Expected whole-book controls");
  return model;
}

export async function until(ready: () => boolean): Promise<void> {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    if (ready()) return;
    await flushEffects();
  }
  throw new Error("Expected Studio state to settle");
}

beforeEach(() => {
  vi.useFakeTimers();
  serverBody = before;
  vi.mocked(api.project).mockImplementation(async () =>
    projectWith([summarizeDocument(serverBody), summarizeDocument(other)]),
  );
  vi.mocked(api.document).mockImplementation(async (_project, id) =>
    id === other.id ? other : serverBody,
  );
  vi.mocked(api.providers).mockResolvedValue({ providers: [] });
  vi.mocked(api.jobs).mockResolvedValue({ jobs: [], next_cursor: null });
  vi.mocked(api.revisions).mockImplementation(async () => ({
    revisions: [
      revision(serverBody.current_revision_id, { document_id: before.id }),
      revision(restoreTarget, { document_id: before.id }),
    ],
    next_cursor: null,
  }));
  vi.mocked(api.reviews).mockResolvedValue({ reviews: [], next_cursor: null });
  vi.mocked(api.exports).mockResolvedValue({ exports: [], next_cursor: null });
  vi.mocked(api.acceptProposal).mockImplementation(async () => {
    serverBody = accepted;
    return proposal;
  });
  vi.mocked(api.restoreRevision).mockImplementation(
    async (_project, _document, _revision, base) => {
      if (base !== serverBody.current_revision_id) {
        throw new HttpError("Revision conflict", 409, undefined, "REVISION_CONFLICT");
      }
      serverBody = restored;
      return restored;
    },
  );
  vi.mocked(api.saveDocument).mockImplementation(async (_project, _document, request) => {
    if (request.base_revision_id !== serverBody.current_revision_id) {
      throw new HttpError("Revision conflict", 409, undefined, "REVISION_CONFLICT");
    }
    serverBody = {
      ...serverBody,
      content_markdown: request.content_markdown,
      current_revision_id: "revision-saved",
    };
    return serverBody;
  });
});

afterEach(() => {
  harness.cleanup();
  resetRevisionCacheForTests();
  current = undefined;
  vi.resetAllMocks();
  vi.useRealTimers();
});

export async function mount(): Promise<void> {
  harness.mount(
    <MemoryRouter initialEntries={["/projects/project-1/manuscript"]}>
      <Probe />
    </MemoryRouter>,
  );
  await until(() => current?.viewProps?.editor.activeDocument?.id === before.id);
  act(() => view().inspector.model.copilot.setProposal(proposal));
}

/** Keeps only the acceptance's current-body response pending; all later reads see server authority. */
export async function startPendingAcceptance() {
  let resolve!: (document: StudioDocument) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<StudioDocument>((resolveResponse, rejectResponse) => {
    resolve = resolveResponse;
    reject = rejectResponse;
  });
  const response = { promise, resolve, reject };
  vi.mocked(api.document).mockImplementationOnce(() => response.promise);
  let pending = Promise.resolve();
  act(() => {
    pending = Promise.resolve(view().inspector.model.copilot.onAcceptProposal());
  });
  await until(() => vi.mocked(api.document).mock.calls.length >= 2);
  return { pending, response };
}

async function confirmHistoryRestore(): Promise<void> {
  const button = getByRole(document.body, "button", { name: "Restore revision older-r0" });
  expect(button).not.toBeDisabled();
  act(() => button.click());
  act(() => getByRole(document.body, "button", { name: "Confirm restore" }).click());
  await flushEffects();
}

export async function restoreThroughHistory(): Promise<void> {
  // R0 is older than the displayed R1, so the real History restore control remains available.
  // The first request conflicts because acceptance already committed R2 on the server.
  await confirmHistoryRestore();
  expect(api.restoreRevision).toHaveBeenLastCalledWith(
    "project-1",
    before.id,
    restoreTarget,
    before.current_revision_id,
  );
  await until(() => view().statusbar.loadedRevisionId === accepted.current_revision_id);
  await confirmHistoryRestore();
  expect(api.restoreRevision).toHaveBeenLastCalledWith(
    "project-1",
    before.id,
    restoreTarget,
    accepted.current_revision_id,
  );
  await until(() => view().statusbar.loadedRevisionId === restored.current_revision_id);
  expect(view().project.documents[0]?.current_revision_id).toBe(restored.current_revision_id);
  expect(view().editor.draft).toBe(restored.content_markdown);
}
