import { act } from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api, HttpError } from "@/app/api";
import type { Project } from "@/app/types/studio";
import { project } from "@/test/factories";
import { createMountHarness, flushEffects } from "@/test/harness";

import { useStudioProject } from "./useStudioProject";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      project: vi.fn<typeof actual.api.project>(),
      reviews: vi.fn<typeof actual.api.reviews>(),
      exports: vi.fn<typeof actual.api.exports>(),
    },
  };
});

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

function renderProject(projectValue: Project) {
  let current: ReturnType<typeof useStudioProject> | undefined;
  vi.mocked(api.project).mockResolvedValue(projectValue);
  vi.mocked(api.reviews).mockResolvedValue({ reviews: [] });
  vi.mocked(api.exports).mockResolvedValue({ exports: [] });

  function Probe(): null {
    current = useStudioProject(projectValue.id);
    return null;
  }
  harness.mount(
    <MemoryRouter>
      <Probe />
    </MemoryRouter>,
  );
  return () => current;
}

describe("useStudioProject shell authority", () => {
  it("rejects a shell read captured before a local shell mutation", async () => {
    const initial = project({ id: "project-1", title: "Initial title" });
    const result = renderProject(initial);
    await flushEffects();
    const capture = result()?.captureProjectShellRead();
    expect(capture).toBeDefined();

    act(() =>
      result()?.setProject((current) =>
        current ? { ...current, title: "Locally committed title" } : current,
      ),
    );
    let published = true;
    act(() => {
      if (capture)
        published =
          result()?.publishProjectShellRead(capture, {
            ...initial,
            title: "Stale read title",
          }) ?? true;
    });

    expect(published).toBe(false);
    expect(result()?.project?.title).toBe("Locally committed title");
  });

  it("lets Document convergence publish when a later Inspector recheck fails", async () => {
    const initial = project({ id: "project-1", title: "Initial title" });
    const converged = project({ id: "project-1", title: "Converged document shell" });
    let rejectInspectorRecheck!: (reason: unknown) => void;
    const inspectorRecheck = new Promise<Project>((_resolve, reject) => {
      rejectInspectorRecheck = reject;
    });
    const result = renderProject(initial);
    await flushEffects();
    const documentCapture = result()?.captureProjectShellRead();
    expect(documentCapture).toBeDefined();
    vi.mocked(api.project).mockReturnValueOnce(inspectorRecheck);

    let recheckPromise: Promise<boolean> | undefined;
    act(() => {
      recheckPromise = result()?.recheckProject(new AbortController().signal);
    });

    let published = false;
    act(() => {
      if (documentCapture) {
        published = result()?.publishProjectShellRead(documentCapture, converged) ?? false;
      }
    });
    expect(published).toBe(true);
    expect(result()?.project?.title).toBe("Converged document shell");

    await act(async () => {
      rejectInspectorRecheck(new HttpError("Inspector recheck unavailable.", 503));
      await expect(recheckPromise).rejects.toThrow("Inspector recheck unavailable.");
    });
    expect(result()?.project?.title).toBe("Converged document shell");
  });
});
