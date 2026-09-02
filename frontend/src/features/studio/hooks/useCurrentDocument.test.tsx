import type { Dispatch, SetStateAction } from "react";
import { act, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api, HttpError } from "@/app/api";
import type { DocumentSummary, ProjectShell, StudioDocument } from "@/app/types/studio";
import { createMountHarness, deferred, flushEffects } from "@/test/harness";

import { useCurrentDocument } from "./useCurrentDocument";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      document: vi.fn<typeof actual.api.document>(),
      project: vi.fn<typeof actual.api.project>(),
    },
  };
});

const timestamp = "2026-09-03T00:00:00Z";
const summary: DocumentSummary = {
  id: "document-1",
  project_id: "project-1",
  kind: "chapter",
  title: "Chapter 1",
  position: 0,
  volume_id: null,
  beat_ref: null,
  lore_status: null,
  current_revision_id: "revision-1",
  revision_source: "author",
  word_count: 2,
  created_at: timestamp,
  updated_at: timestamp,
};
const document: StudioDocument = {
  ...summary,
  content_markdown: "Accepted body",
  metadata: {},
};
const shell: ProjectShell = {
  id: "project-1",
  title: "Harbor",
  description: "",
  settings: {},
  import_hash: null,
  documents: [summary],
  volumes: [],
  created_at: timestamp,
  updated_at: timestamp,
};

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

interface HookOptions {
  summary: DocumentSummary | null;
  lifecycle: symbol;
  setProject: Dispatch<SetStateAction<ProjectShell | null>>;
  onSessionLoss: () => void;
  onProjectMissing: () => void;
}

function renderCurrentDocument(initialSummary: DocumentSummary | null = summary) {
  const lifecycle = Symbol("studio lifecycle");
  let selected = initialSummary;
  let current: ReturnType<typeof useCurrentDocument> | undefined;
  let visibleShell: ProjectShell | null = shell;
  const onSessionLoss = vi.fn();
  const onProjectMissing = vi.fn();

  function Probe(): null {
    const [project, setProject] = useState<ProjectShell | null>(visibleShell);
    visibleShell = project;
    const effectiveSummary =
      selected === null
        ? null
        : (project?.documents.find((candidate) => candidate.id === selected?.id) ?? null);
    const options: HookOptions = {
      summary: effectiveSummary,
      lifecycle,
      setProject,
      onSessionLoss,
      onProjectMissing,
    };
    current = useCurrentDocument("project-1", options);
    return null;
  }

  const mounted = harness.mount(<Probe />);
  return {
    ...mounted,
    lifecycle,
    result: () => {
      if (!current) throw new Error("Expected current-document hook state.");
      return current;
    },
    shell: () => visibleShell,
    onSessionLoss,
    onProjectMissing,
    rerender: (nextSummary: DocumentSummary | null) => {
      selected = nextSummary;
      act(() => mounted.root.render(<Probe />));
    },
  };
}

describe("useCurrentDocument", () => {
  it("publishes only the exact current Document selected by the shell", async () => {
    vi.mocked(api.document).mockResolvedValue(document);

    const view = renderCurrentDocument();
    expect(view.result().document).toBeNull();
    expect(view.result().isLoading).toBe(true);
    await flushEffects();

    expect(api.document).toHaveBeenCalledWith("project-1", "document-1", {
      signal: expect.any(AbortSignal),
    });
    expect(view.result()).toMatchObject({ document, error: null, isLoading: false });
  });

  it.each([{ project_id: "project-2" }, { id: "document-2" }])(
    "rejects a current Document with the wrong route identity: %o",
    async (identity) => {
      vi.mocked(api.document).mockResolvedValue({ ...document, ...identity });

      const view = renderCurrentDocument();
      await flushEffects();

      expect(view.result().document).toBeNull();
      expect(view.result().error).toContain("listed but could not be loaded");
    },
  );

  it("refreshes the shell once and accepts a raced body only when its pointer matches", async () => {
    const raced = { ...document, current_revision_id: "revision-2" };
    const refreshedSummary = { ...summary, current_revision_id: "revision-2" };
    vi.mocked(api.document).mockResolvedValue(raced);
    vi.mocked(api.project).mockResolvedValue({
      ...shell,
      documents: [refreshedSummary],
    });

    const view = renderCurrentDocument();
    await flushEffects();
    await flushEffects();

    expect(api.project).toHaveBeenCalledTimes(1);
    expect(api.document).toHaveBeenCalledTimes(1);
    expect(view.shell()?.documents[0]?.current_revision_id).toBe("revision-2");
    expect(view.result().document).toEqual(raced);
  });

  it("bounds revision churn to one shell refresh and one replacement body read", async () => {
    const firstRace = { ...document, current_revision_id: "revision-2" };
    const refreshedSummary = { ...summary, current_revision_id: "revision-3" };
    const secondRace = { ...document, current_revision_id: "revision-4" };
    vi.mocked(api.document).mockResolvedValueOnce(firstRace).mockResolvedValueOnce(secondRace);
    vi.mocked(api.project).mockResolvedValue({ ...shell, documents: [refreshedSummary] });

    const view = renderCurrentDocument();
    await flushEffects();
    view.rerender(refreshedSummary);
    await flushEffects();
    await flushEffects();

    expect(api.project).toHaveBeenCalledTimes(1);
    expect(api.document).toHaveBeenCalledTimes(2);
    expect(view.result().document).toBeNull();
    expect(view.result().error).toContain("changed again");
  });

  it("coalesces equal lifecycle reads and aborts only after the last subscriber releases", async () => {
    const pending = deferred<StudioDocument>();
    let requestSignal: AbortSignal | undefined;
    vi.mocked(api.document).mockImplementation((_projectId, _documentId, init) => {
      requestSignal = init?.signal ?? undefined;
      return pending.promise;
    });
    const lifecycle = Symbol("shared lifecycle");
    let first: ReturnType<typeof useCurrentDocument> | undefined;
    let second: ReturnType<typeof useCurrentDocument> | undefined;
    const setProject = vi.fn();
    const options = {
      summary,
      lifecycle,
      setProject,
      onSessionLoss: vi.fn(),
      onProjectMissing: vi.fn(),
    };
    function First(): null {
      first = useCurrentDocument("project-1", options);
      return null;
    }
    function Second(): null {
      second = useCurrentDocument("project-1", options);
      return null;
    }
    const firstRoot = harness.mount(<First />);
    harness.mount(<Second />);
    await flushEffects();
    expect(api.document).toHaveBeenCalledTimes(1);

    harness.unmount(firstRoot.container);
    expect(requestSignal?.aborted).toBe(false);
    await act(async () => pending.resolve(document));

    expect(first?.document).toBeNull();
    expect(second?.document).toEqual(document);
    expect(requestSignal?.aborted).toBe(false);
  });

  it("aborts an unsettled read when its last subscriber releases", async () => {
    let requestSignal: AbortSignal | undefined;
    vi.mocked(api.document).mockImplementation(
      (_projectId, _documentId, init) =>
        new Promise<StudioDocument>((_resolve, reject) => {
          requestSignal = init?.signal ?? undefined;
          requestSignal?.addEventListener("abort", () => reject(new Error("Request cancelled.")));
        }),
    );

    const view = renderCurrentDocument();
    await flushEffects();
    expect(requestSignal?.aborted).toBe(false);

    harness.unmount(view.container);

    expect(requestSignal?.aborted).toBe(true);
  });

  it("suppresses a late body after the active selection changes", async () => {
    const secondSummary = {
      ...summary,
      id: "document-2",
      current_revision_id: "revision-2",
    };
    const secondDocument = {
      ...document,
      ...secondSummary,
      content_markdown: "Second body",
    };
    const firstRead = deferred<StudioDocument>();
    const secondRead = deferred<StudioDocument>();
    const signals: AbortSignal[] = [];
    vi.mocked(api.document).mockImplementation((_projectId, documentId, init) => {
      if (init?.signal) signals.push(init.signal);
      return documentId === summary.id ? firstRead.promise : secondRead.promise;
    });
    const lifecycle = Symbol("selection lifecycle");
    let selected = summary;
    let current: ReturnType<typeof useCurrentDocument> | undefined;
    const options = {
      lifecycle,
      setProject: vi.fn(),
      onSessionLoss: vi.fn(),
      onProjectMissing: vi.fn(),
    };
    function Probe(): null {
      current = useCurrentDocument("project-1", { ...options, summary: selected });
      return null;
    }
    const mounted = harness.mount(<Probe />);
    await flushEffects();

    selected = secondSummary;
    act(() => mounted.root.render(<Probe />));
    await flushEffects();
    expect(signals[0]?.aborted).toBe(true);

    await act(async () => {
      firstRead.resolve(document);
      secondRead.resolve(secondDocument);
      await Promise.all([firstRead.promise, secondRead.promise]);
    });

    expect(current?.document).toEqual(secondDocument);
  });

  it("does not retain a successful body in a global cache", async () => {
    vi.mocked(api.document).mockResolvedValue(document);
    const first = renderCurrentDocument();
    await flushEffects();
    expect(first.result().document).toEqual(document);
    harness.unmount(first.container);

    const second = renderCurrentDocument();
    await flushEffects();

    expect(second.result().document).toEqual(document);
    expect(api.document).toHaveBeenCalledTimes(2);
  });

  it("refreshes structural authority after a scoped 404 without inventing a body", async () => {
    vi.mocked(api.document).mockRejectedValue(new HttpError("Document not found.", 404));
    vi.mocked(api.project).mockResolvedValue({ ...shell, documents: [] });

    const view = renderCurrentDocument();
    await flushEffects();
    await flushEffects();

    expect(api.project).toHaveBeenCalledTimes(1);
    expect(view.shell()?.documents).toEqual([]);
    expect(view.result().document).toBeNull();
    expect(view.result().error).toBeNull();
  });

  it("classifies authentication and project absence globally", async () => {
    vi.mocked(api.document).mockRejectedValueOnce(new HttpError("Authentication required.", 401));
    const unauthorized = renderCurrentDocument();
    await flushEffects();
    expect(unauthorized.onSessionLoss).toHaveBeenCalledTimes(1);

    vi.mocked(api.document).mockRejectedValueOnce(new HttpError("Document not found.", 404));
    vi.mocked(api.project).mockRejectedValueOnce(new HttpError("Project not found.", 404));
    const missing = renderCurrentDocument();
    await flushEffects();
    await flushEffects();
    expect(missing.onProjectMissing).toHaveBeenCalledTimes(1);
  });
});
