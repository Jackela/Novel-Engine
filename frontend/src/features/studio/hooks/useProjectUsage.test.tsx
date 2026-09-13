import { act, StrictMode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { ProjectUsage } from "@/app/types/studio";
import { createMountHarness, deferred, flushEffects } from "@/test/harness";

import { useProjectUsage } from "./useProjectUsage";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      usage: vi.fn<typeof actual.api.usage>(),
    },
  };
});

type HookResult = ReturnType<typeof useProjectUsage>;

const mountHarness = createMountHarness();

afterEach(() => {
  mountHarness.cleanup();
  vi.resetAllMocks();
});

function usage(projectId: string, requestCount: number): ProjectUsage {
  return {
    project_id: projectId,
    request_count: requestCount,
    prompt_tokens: requestCount * 100,
    completion_tokens: requestCount * 25,
    per_model: [],
    daily: [],
  };
}

function renderUsageHook(initialProjectId: string, initialActive: boolean, strict = false) {
  let projectId = initialProjectId;
  let active = initialActive;
  let current: HookResult | undefined;

  function Harness(): null {
    current = useProjectUsage(projectId, active);
    return null;
  }

  const content = () =>
    strict ? (
      <StrictMode>
        <Harness />
      </StrictMode>
    ) : (
      <Harness />
    );
  const { root } = mountHarness.mount(content());
  const render = () => root.render(content());

  return {
    result: () => {
      if (current === undefined) throw new Error("Expected usage hook result after render.");
      return current;
    },
    rerender: (nextProjectId: string, nextActive = active) => {
      projectId = nextProjectId;
      active = nextActive;
      act(render);
    },
  };
}

describe("useProjectUsage", () => {
  it("restarts the current project's first active load after StrictMode cleanup", async () => {
    // Given: the first transport ignores cancellation and would otherwise leave Loading stuck.
    const firstRequest = deferred<ProjectUsage>();
    const completed = usage("project-1", 4);
    vi.mocked(api.usage).mockReturnValueOnce(firstRequest.promise).mockResolvedValueOnce(completed);

    // When
    const hook = renderUsageHook("project-1", true, true);
    await flushEffects();

    // Then: StrictMode aborted the simulated first mount and the real setup loaded again.
    expect(api.usage).toHaveBeenCalledTimes(2);
    expect(vi.mocked(api.usage).mock.calls[0]?.[1]?.signal?.aborted).toBe(true);
    expect(hook.result().usage).toEqual(completed);
    expect(hook.result().isLoading).toBe(false);
    expect(hook.result().error).toBeNull();
  });

  it("loads the directly active project's usage and hides the previous project's totals immediately", async () => {
    // Given
    const first = usage("project-1", 1);
    const secondRequest = deferred<ProjectUsage>();
    vi.mocked(api.usage).mockResolvedValueOnce(first).mockReturnValueOnce(secondRequest.promise);
    const hook = renderUsageHook("project-1", true);
    await flushEffects();
    expect(hook.result().usage).toEqual(first);

    // When: the active Usage panel is routed to project two before its request settles.
    hook.rerender("project-2");

    // Then
    expect(hook.result().usage).toBeNull();
    expect(hook.result().error).toBeNull();
    expect(api.usage).toHaveBeenNthCalledWith(2, "project-2", {
      signal: expect.any(AbortSignal),
    });
  });

  it("aborts and discards a reverse-order completion from the previous project", async () => {
    // Given
    const firstRequest = deferred<ProjectUsage>();
    const second = usage("project-2", 2);
    vi.mocked(api.usage).mockReturnValueOnce(firstRequest.promise).mockResolvedValueOnce(second);
    const hook = renderUsageHook("project-1", true);
    await flushEffects();

    // When
    hook.rerender("project-2");
    await flushEffects();
    const firstSignal = vi.mocked(api.usage).mock.calls[0]?.[1]?.signal;
    await act(async () => {
      firstRequest.resolve(usage("project-1", 99));
      await firstRequest.promise;
      await Promise.resolve();
    });

    // Then
    expect(firstSignal?.aborted).toBe(true);
    expect(hook.result().usage).toEqual(second);
    expect(hook.result().isLoading).toBe(false);
  });

  it("clears a stale usage error after refresh succeeds", async () => {
    // Given
    const recovered = usage("project-1", 3);
    vi.mocked(api.usage)
      .mockRejectedValueOnce(new Error("usage unavailable"))
      .mockResolvedValueOnce(recovered);
    const hook = renderUsageHook("project-1", true);
    await flushEffects();
    expect(hook.result().error).toBe("usage unavailable");

    // When
    await act(async () => {
      await hook.result().reload();
    });

    // Then
    expect(hook.result().usage).toEqual(recovered);
    expect(hook.result().error).toBeNull();
  });
});
