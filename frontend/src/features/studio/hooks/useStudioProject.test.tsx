import { act } from "react";
import { MemoryRouter, useLocation, useNavigationType } from "react-router-dom";
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

type HookResult = ReturnType<typeof useStudioProject>;

interface ProjectFixture {
  readonly project: Project;
}

interface HarnessSnapshot {
  readonly hook: HookResult;
  readonly pathname: string;
  readonly navigationType: ReturnType<typeof useNavigationType>;
}

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

function makeProject(projectId: string, label: string): ProjectFixture {
  return {
    project: project({
      id: projectId,
      title: `Project ${label}`,
      description: `Description ${label}`,
      settings: { provider: "mock" },
    }),
  };
}

function renderStudioProjectHook(
  initialProjectId: string,
  initialPath = `/projects/${initialProjectId}/manuscript`,
): {
  readonly result: () => HarnessSnapshot;
  readonly rerender: (projectId: string) => void;
} {
  let projectId = initialProjectId;
  let current: HarnessSnapshot | undefined;

  function Harness(): null {
    const hook = useStudioProject(projectId);
    const location = useLocation();
    const navigationType = useNavigationType();
    current = { hook, pathname: location.pathname, navigationType };
    return null;
  }

  const { root } = harness.mount(
    <MemoryRouter initialEntries={[initialPath]}>
      <Harness />
    </MemoryRouter>,
  );

  const render = () => {
    root.render(
      <MemoryRouter initialEntries={[initialPath]}>
        <Harness />
      </MemoryRouter>,
    );
  };

  return {
    result: () => {
      if (current === undefined) {
        throw new Error("Expected hook result after render.");
      }
      return current;
    },
    rerender: (nextProjectId: string) => {
      projectId = nextProjectId;
      act(render);
    },
  };
}

describe("useStudioProject", () => {
  it("publishes only the bounded project shell during bootstrap", async () => {
    // Given
    const fixture = makeProject("project-1", "one");
    vi.mocked(api.project).mockResolvedValue(fixture.project);

    // When
    const harness = renderStudioProjectHook("project-1");
    await flushEffects();

    // Then
    expect(harness.result().hook.project).toEqual(fixture.project);
    expect(api.reviews).not.toHaveBeenCalled();
    expect(api.exports).not.toHaveBeenCalled();
  });

  it("replaces to the project library with no partial aggregate when the project is missing", async () => {
    // Given
    vi.mocked(api.project).mockRejectedValue(new HttpError("Project not found.", 404));

    // When
    const harness = renderStudioProjectHook("project-1");
    await flushEffects();

    // Then
    expect(harness.result().pathname).toBe("/projects");
    expect(harness.result().navigationType).toBe("REPLACE");
    expect(harness.result().hook.project).toBeNull();
    expect(api.reviews).not.toHaveBeenCalled();
    expect(api.exports).not.toHaveBeenCalled();
  });

  it("publishes the new shell when the project id changes", async () => {
    // Given
    const first = makeProject("project-1", "one");
    const second = makeProject("project-2", "two");
    vi.mocked(api.project)
      .mockResolvedValueOnce(first.project)
      .mockResolvedValueOnce(second.project);

    // When
    const harness = renderStudioProjectHook("project-1");
    await flushEffects();
    const firstPublished = harness.result().hook;
    harness.rerender("project-2");
    await flushEffects();

    // Then
    expect(firstPublished.project).toEqual(first.project);
    expect(harness.result().hook.project).toEqual(second.project);
    expect(api.project).toHaveBeenNthCalledWith(1, "project-1", {
      signal: expect.any(AbortSignal),
    });
    expect(api.project).toHaveBeenNthCalledWith(2, "project-2", {
      signal: expect.any(AbortSignal),
    });
  });

  it("hides the previous project aggregate and errors as soon as the route identity changes", async () => {
    // Given
    const first = makeProject("project-1", "one");
    const secondProject = deferred<Project>();
    vi.mocked(api.project)
      .mockResolvedValueOnce(first.project)
      .mockReturnValueOnce(secondProject.promise);
    const hook = renderStudioProjectHook("project-1");
    await flushEffects();
    act(() => {
      hook.result().hook.setError("Project one action failed.");
    });

    // When: project two has not loaded yet.
    hook.rerender("project-2");

    // Then: no project-one state remains interactive for even one render.
    expect(hook.result().hook.project).toBeNull();
    expect(hook.result().hook.error).toBeNull();
    expect(hook.result().hook.loadError).toBeNull();
  });

  it("discards reverse-order shell completion from the previous project", async () => {
    // Given
    const first = makeProject("project-1", "one");
    const second = makeProject("project-2", "two");
    const firstProject = deferred<Project>();
    vi.mocked(api.project)
      .mockReturnValueOnce(firstProject.promise)
      .mockResolvedValueOnce(second.project);
    const hook = renderStudioProjectHook("project-1");
    await flushEffects();

    // When: project two wins, then the transport-ignoring project-one mocks finish late.
    hook.rerender("project-2");
    await flushEffects();
    await act(async () => {
      firstProject.resolve(first.project);
      await firstProject.promise;
      await Promise.resolve();
    });

    // Then
    expect(hook.result().hook.project).toEqual(second.project);
  });

  it("retries an operational failure and clears the stale load error on shell success", async () => {
    // Given
    const fixture = makeProject("project-1", "one");
    vi.mocked(api.project)
      .mockRejectedValueOnce(new HttpError("Upstream failure.", 503))
      .mockResolvedValueOnce(fixture.project);
    const hook = renderStudioProjectHook("project-1");
    await flushEffects();
    expect(hook.result().hook.loadError).toBe("Upstream failure.");

    // When
    await act(async () => {
      await hook.result().hook.retryLoad();
    });

    // Then
    expect(hook.result().hook.loadError).toBeNull();
    expect(hook.result().hook.project).toEqual(fixture.project);
  });

  it("replaces to the entry route when authentication is required", async () => {
    // Given
    vi.mocked(api.project).mockRejectedValue(new HttpError("Authentication required.", 401));
    vi.mocked(api.reviews).mockResolvedValue({ reviews: [] });
    vi.mocked(api.exports).mockResolvedValue({ exports: [] });

    // When
    const hook = renderStudioProjectHook("project-1");
    await flushEffects();

    // Then
    expect(hook.result().pathname).toBe("/");
    expect(hook.result().navigationType).toBe("REPLACE");
    expect(hook.result().hook.loadError).toBeNull();
  });

  it("renders a readable error state and keeps the route when the failure is not a 404", async () => {
    // Given
    vi.mocked(api.project).mockRejectedValue(new HttpError("Upstream failure.", 503));
    vi.mocked(api.reviews).mockResolvedValue({ reviews: [] });
    vi.mocked(api.exports).mockResolvedValue({ exports: [] });

    // When
    const harness = renderStudioProjectHook("project-1");
    await flushEffects();

    // Then: no silent redirect, the error is published for the page to render.
    expect(harness.result().pathname).toBe("/projects/project-1/manuscript");
    expect(harness.result().hook.loadError).toBe("Upstream failure.");
    expect(harness.result().hook.project).toBeNull();
  });

  it("refreshes shell authority for an Inspector 404 without clearing the loaded project", async () => {
    const first = makeProject("project-1", "one");
    const refreshed = makeProject("project-1", "refreshed");
    vi.mocked(api.project)
      .mockResolvedValueOnce(first.project)
      .mockResolvedValueOnce(refreshed.project);
    const mounted = renderStudioProjectHook("project-1");
    await flushEffects();

    await act(async () => {
      await mounted.result().hook.recheckProject(new AbortController().signal);
    });

    expect(mounted.result().hook.project).toEqual(refreshed.project);
    expect(mounted.result().pathname).toBe("/projects/project-1/manuscript");
  });

  it("replaces to the library when an Inspector recheck proves the project is missing", async () => {
    const first = makeProject("project-1", "one");
    vi.mocked(api.project)
      .mockResolvedValueOnce(first.project)
      .mockRejectedValueOnce(new HttpError("Project not found.", 404));
    const mounted = renderStudioProjectHook("project-1");
    await flushEffects();

    await act(async () => {
      await mounted.result().hook.recheckProject(new AbortController().signal);
    });

    expect(mounted.result().pathname).toBe("/projects");
    expect(mounted.result().navigationType).toBe("REPLACE");
  });

  it("aborts the in-flight requests of the previous project when the id changes", async () => {
    // Given
    const second = makeProject("project-2", "two");
    vi.mocked(api.reviews).mockResolvedValue({ reviews: [] });
    vi.mocked(api.exports).mockResolvedValue({ exports: [] });
    // The stale project request only settles when its signal is aborted.
    vi.mocked(api.project)
      .mockImplementationOnce((_projectId: string, init?: RequestInit) => {
        return new Promise((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => reject(new Error("Request cancelled.")));
        });
      })
      .mockResolvedValueOnce(second.project);

    // When
    const harness = renderStudioProjectHook("project-1");
    await flushEffects();
    harness.rerender("project-2");
    await flushEffects();

    // Then: the stale call's signal was aborted, the fresh one was not, and
    // the stale response never published project-1 over project-2.
    const [firstProjectCall, secondProjectCall] = vi.mocked(api.project).mock.calls;
    const firstSignal = firstProjectCall?.[1]?.signal ?? null;
    const secondSignal = secondProjectCall?.[1]?.signal ?? null;
    expect(firstSignal?.aborted).toBe(true);
    expect(secondSignal?.aborted).toBe(false);
    expect(harness.result().hook.project).toEqual(second.project);
  });
});
