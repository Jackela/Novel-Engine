import { act, StrictMode } from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api, HttpError } from "@/app/api";
import type { Project } from "@/app/types/studio";
import { project } from "@/test/factories";
import { createMountHarness, deferred, flushEffects } from "@/test/harness";

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
const projectFixture = project({ id: "project-1", title: "Harbor" });
const nextProject = project({ id: "project-2", title: "Headland" });

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

function renderProjectHook(strict = false): {
  readonly result: () => ReturnType<typeof useStudioProject>;
  readonly rerender: (projectId: string) => void;
} {
  let projectId = projectFixture.id;
  let current: ReturnType<typeof useStudioProject> | undefined;

  function Probe(): null {
    current = useStudioProject(projectId);
    return null;
  }

  const route = () => (
    <MemoryRouter initialEntries={[`/projects/${projectId}/manuscript`]}>
      <Probe />
    </MemoryRouter>
  );
  const content = () => (strict ? <StrictMode>{route()}</StrictMode> : route());
  const { root } = harness.mount(content());

  return {
    result: () => {
      if (current === undefined) throw new Error("Expected the project hook result.");
      return current;
    },
    rerender: (nextProjectId) => {
      projectId = nextProjectId;
      act(() => root.render(content()));
    },
  };
}

describe("useStudioProject retry lifecycle", () => {
  it("keeps the recovery error visible and coalesces retry calls during the render gap", async () => {
    const retryProject = deferred<Project>();
    vi.mocked(api.project)
      .mockRejectedValueOnce(new HttpError("Service unavailable.", 503))
      .mockReturnValueOnce(retryProject.promise);
    vi.mocked(api.reviews).mockResolvedValue({ reviews: [] });
    vi.mocked(api.exports).mockResolvedValue({ exports: [], next_cursor: null });
    const { result } = renderProjectHook();
    await flushEffects();
    expect(result().loadError).toBe("Service unavailable.");
    expect(result().isLoading).toBe(false);

    let firstRetry!: Promise<void>;
    let duplicateRetry!: Promise<void>;
    act(() => {
      firstRetry = result().retryLoad();
      duplicateRetry = result().retryLoad();
    });

    expect(api.project).toHaveBeenCalledTimes(2);
    expect(api.reviews).not.toHaveBeenCalled();
    expect(api.exports).not.toHaveBeenCalled();
    expect(result().isLoading).toBe(true);
    expect(result().loadError).toBe("Service unavailable.");

    await act(async () => {
      retryProject.resolve(projectFixture);
      await Promise.all([firstRetry, duplicateRetry]);
    });

    expect(result().isLoading).toBe(false);
    expect(result().loadError).toBeNull();
    expect(result().project).toEqual(projectFixture);
    expect(api.reviews).not.toHaveBeenCalled();
    expect(api.exports).not.toHaveBeenCalled();
  });

  it("restarts the current owner load after the StrictMode cleanup boundary", async () => {
    vi.mocked(api.project)
      .mockImplementationOnce(
        (_projectId, init) =>
          new Promise<Project>((_resolve, reject) => {
            init?.signal?.addEventListener("abort", () => reject(new Error("Request cancelled.")));
          }),
      )
      .mockResolvedValueOnce(projectFixture);
    vi.mocked(api.reviews).mockResolvedValue({ reviews: [] });
    vi.mocked(api.exports).mockResolvedValue({ exports: [], next_cursor: null });

    const { result } = renderProjectHook(true);
    await flushEffects();

    expect(api.project).toHaveBeenCalledTimes(2);
    expect(result().project).toEqual(projectFixture);
    expect(result().isLoading).toBe(false);
  });

  it("lets a new project owner load while an old retry settles late", async () => {
    const staleRetry = deferred<Project>();
    vi.mocked(api.project)
      .mockRejectedValueOnce(new HttpError("Project one failed.", 503))
      .mockReturnValueOnce(staleRetry.promise)
      .mockResolvedValueOnce(nextProject);
    vi.mocked(api.reviews).mockResolvedValue({ reviews: [] });
    vi.mocked(api.exports).mockResolvedValue({ exports: [], next_cursor: null });
    const hook = renderProjectHook();
    await flushEffects();
    let stalePromise!: Promise<void>;
    act(() => {
      stalePromise = hook.result().retryLoad();
    });
    expect(hook.result().isLoading).toBe(true);

    hook.rerender(nextProject.id);
    await flushEffects();
    expect(hook.result().project).toEqual(nextProject);
    expect(hook.result().loadError).toBeNull();
    expect(hook.result().isLoading).toBe(false);

    await act(async () => {
      staleRetry.resolve(projectFixture);
      await stalePromise;
    });
    expect(hook.result().project).toEqual(nextProject);
    expect(hook.result().isLoading).toBe(false);
  });
});
