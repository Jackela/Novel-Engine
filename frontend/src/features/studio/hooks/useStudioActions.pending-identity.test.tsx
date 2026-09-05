import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { StudioDocument } from "@/app/types/studio";
import { chapter, projectWith } from "@/test/factories";
import { createMountHarness, deferred } from "@/test/harness";

import { useStudioActions } from "./useStudioActions";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      createDocument: vi.fn<typeof actual.api.createDocument>(),
      reorderDocuments: vi.fn<typeof actual.api.reorderDocuments>(),
    },
  };
});

const opening = chapter("doc-1", { title: "Opening", position: 1 });
const second = chapter("doc-2", { title: "Second", position: 2 });
const project = projectWith([opening, second]);
const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

function renderActions(): () => ReturnType<typeof useStudioActions> {
  let current: ReturnType<typeof useStudioActions> | undefined;

  function Probe(): null {
    current = useStudioActions({
      project,
      projectId: project.id,
      setProject: vi.fn(),
      setReviewPage: vi.fn(),
      setError: vi.fn(),
      setActiveId: vi.fn(),
      settingsForm: { title: project.title, description: project.description, provider: "mock" },
      loadJobs: vi.fn().mockResolvedValue(undefined),
    });
    return null;
  }

  harness.mount(<Probe />);
  return () => {
    if (current === undefined) throw new Error("Expected Studio actions.");
    return current;
  };
}

describe("useStudioActions pending identity", () => {
  it("exposes the exact create kind and preserves it when another kind is blocked", async () => {
    const response = deferred<StudioDocument>();
    vi.mocked(api.createDocument).mockReturnValue(response.promise);
    const result = renderActions();
    let createPromise!: Promise<void>;

    act(() => {
      createPromise = result().createDocument("character");
      void result().createDocument("world");
    });

    expect(api.createDocument).toHaveBeenCalledTimes(1);
    expect(result().creatingDocumentKind).toBe("character");
    expect(result().isCreatingDocument).toBe(true);

    await act(async () => {
      response.resolve({ ...opening, id: "character-1", kind: "character", title: "Characters 1" });
      await createPromise;
    });
    expect(result().creatingDocumentKind).toBeNull();
    expect(result().isCreatingDocument).toBe(false);
  });

  it("exposes the exact move target and direction until that reorder settles", async () => {
    const response = deferred<{ documents: StudioDocument[] }>();
    vi.mocked(api.reorderDocuments).mockReturnValue(response.promise);
    const result = renderActions();
    let movePromise!: Promise<void>;

    act(() => {
      movePromise = result().moveDocument(opening.id, 1);
      void result().moveDocument(second.id, -1);
    });

    expect(api.reorderDocuments).toHaveBeenCalledTimes(1);
    expect(result().movingDocument).toEqual({ documentId: opening.id, direction: 1 });
    expect(result().isMovingDocument).toBe(true);

    await act(async () => {
      response.resolve({
        documents: [
          { ...second, position: 1 },
          { ...opening, position: 2 },
        ],
      });
      await movePromise;
    });
    expect(result().movingDocument).toBeNull();
    expect(result().isMovingDocument).toBe(false);
  });

  it("blocks reorder while a create mutation owns the document aggregate", async () => {
    const response = deferred<StudioDocument>();
    vi.mocked(api.createDocument).mockReturnValue(response.promise);
    const result = renderActions();
    let createPromise!: Promise<void>;

    act(() => {
      createPromise = result().createDocument("chapter");
      void result().moveDocument(opening.id, 1);
    });

    expect(api.createDocument).toHaveBeenCalledTimes(1);
    expect(api.reorderDocuments).not.toHaveBeenCalled();
    await act(async () => {
      response.resolve({ ...opening, id: "doc-3", position: 3 });
      await createPromise;
    });
  });

  it("blocks create while a reorder mutation owns the document aggregate", async () => {
    const response = deferred<{ documents: StudioDocument[] }>();
    vi.mocked(api.reorderDocuments).mockReturnValue(response.promise);
    const result = renderActions();
    let movePromise!: Promise<void>;

    act(() => {
      movePromise = result().moveDocument(opening.id, 1);
      void result().createDocument("chapter");
    });

    expect(api.reorderDocuments).toHaveBeenCalledTimes(1);
    expect(api.createDocument).not.toHaveBeenCalled();
    await act(async () => {
      response.resolve({ documents: [second, opening] });
      await movePromise;
    });
  });
});
