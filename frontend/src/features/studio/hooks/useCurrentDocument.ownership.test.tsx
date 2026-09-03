import type { SetStateAction } from "react";
import { act, useCallback, useRef, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { DocumentSummary, ProjectShell, StudioDocument } from "@/app/types/studio";
import { createMountHarness, deferred, flushEffects } from "@/test/harness";

import type { ProjectShellReadCapture } from "./projectShellReadAuthority";
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

function renderOwnedDocument(initialSummary: DocumentSummary | null = summary) {
  const lifecycle = Symbol("studio lifecycle");
  let inputSummary = initialSummary;
  let current: ReturnType<typeof useCurrentDocument> | undefined;
  let visibleShell: ProjectShell | null = shell;
  let mutateShell: (action: SetStateAction<ProjectShell | null>) => void = () => undefined;
  const onSessionLoss = vi.fn();
  const onProjectMissing = vi.fn();

  function Probe(): null {
    const [project, setProject] = useState<ProjectShell | null>(visibleShell);
    const mutationEpoch = useRef(0);
    const readEpoch = useRef(0);
    const captureProjectShellRead = useCallback(
      (): ProjectShellReadCapture => ({
        projectId: "project-1",
        readEpoch: ++readEpoch.current,
        mutationEpoch: mutationEpoch.current,
      }),
      [],
    );
    const publishProjectShellRead = useCallback(
      (capture: ProjectShellReadCapture, nextProject: ProjectShell) => {
        if (
          capture.readEpoch !== readEpoch.current ||
          capture.mutationEpoch !== mutationEpoch.current
        )
          return false;
        setProject(nextProject);
        return true;
      },
      [],
    );
    visibleShell = project;
    mutateShell = (action) => {
      mutationEpoch.current += 1;
      setProject(action);
    };
    current = useCurrentDocument("project-1", {
      summary: inputSummary,
      lifecycle,
      captureProjectShellRead,
      publishProjectShellRead,
      onSessionLoss,
      onProjectMissing,
    });
    return null;
  }

  const mounted = harness.mount(<Probe />);
  return {
    result: () => current,
    shell: () => visibleShell,
    mutateSummary: (nextSummary: DocumentSummary) => {
      act(() => {
        inputSummary = nextSummary;
        mutateShell((project) => project);
        mounted.root.render(<Probe />);
      });
    },
    setShell: (action: SetStateAction<ProjectShell | null>) => act(() => mutateShell(action)),
  };
}

describe("useCurrentDocument ownership", () => {
  it("keeps one lease when summary-only fields change under the same causal tuple", async () => {
    const pending = deferred<StudioDocument>();
    let signal: AbortSignal | undefined;
    vi.mocked(api.document).mockImplementation((_projectId, _documentId, init) => {
      signal = init?.signal ?? undefined;
      return pending.promise;
    });
    const view = renderOwnedDocument();
    await flushEffects();

    view.mutateSummary({ ...summary, position: 7, lore_status: "stable" });
    await flushEffects();

    expect(api.document).toHaveBeenCalledTimes(1);
    expect(signal?.aborted).toBe(false);
    await act(async () => pending.resolve(document));
    expect(view.result()?.document).toEqual(document);
  });

  it("does not request a child summary owned by another project", async () => {
    const view = renderOwnedDocument({ ...summary, project_id: "project-2" });
    await flushEffects();

    expect(api.document).not.toHaveBeenCalled();
    expect(view.result()).toMatchObject({ document: null, isLoading: false });
  });

  it.each([{ project_id: "project-2" }, { id: "document-2" }])(
    "rejects a response outside the summary tuple: %o",
    async (identity) => {
      vi.mocked(api.document).mockResolvedValue({ ...document, ...identity });
      const view = renderOwnedDocument();
      await flushEffects();

      expect(view.result()?.document).toBeNull();
      expect(view.result()?.error).toContain("listed but could not be loaded");
    },
  );

  it("does not roll a concurrent shell mutation back when convergence finishes late", async () => {
    const refresh = deferred<ProjectShell>();
    vi.mocked(api.document).mockResolvedValue({ ...document, current_revision_id: "revision-2" });
    vi.mocked(api.project).mockReturnValue(refresh.promise);
    const view = renderOwnedDocument();
    await flushEffects();
    await vi.waitFor(() => expect(api.project).toHaveBeenCalledTimes(1));

    view.setShell((current) =>
      current
        ? {
            ...current,
            documents: [{ ...summary, lore_status: "stable" }],
          }
        : current,
    );
    await act(async () =>
      refresh.resolve({
        ...shell,
        documents: [{ ...summary, current_revision_id: "revision-2" }],
      }),
    );
    await flushEffects();

    expect(view.shell()?.documents[0]?.lore_status).toBe("stable");
    expect(api.document).toHaveBeenCalledTimes(1);
    expect(view.result()?.document).toBeNull();
    expect(view.result()?.error).toContain("project changed while loading");
  });
});
