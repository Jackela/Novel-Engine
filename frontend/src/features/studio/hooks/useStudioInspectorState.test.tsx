import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { project } from "@/test/factories";
import { createMountHarness } from "@/test/harness";

import { useStudioInspectorState } from "./useStudioInspectorState";

type HookArgs = Parameters<typeof useStudioInspectorState>[0];
type HookResult = ReturnType<typeof useStudioInspectorState>;

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
});

function renderInspectorHook(initialArgs: HookArgs): {
  readonly result: () => HookResult;
  readonly rerender: (nextArgs: HookArgs) => void;
} {
  let hookArgs = initialArgs;
  let current: HookResult | undefined;

  function Wrapper(): null {
    current = useStudioInspectorState(hookArgs);
    return null;
  }

  const mounted = harness.mount(<Wrapper />);
  const root = mounted.root;

  return {
    result: () => {
      if (current === undefined) {
        throw new Error("Expected hook result after render.");
      }
      return current;
    },
    rerender: (nextArgs: HookArgs) => {
      hookArgs = nextArgs;
      act(() => {
        root.render(<Wrapper />);
      });
    },
  };
}

const baseProject = project({
  description: "A harbor of brass clocks.",
  settings: { provider: "dashscope" },
});

describe("useStudioInspectorState", () => {
  it("reflects the controlled route Inspector when navigation changes", () => {
    const loadJobs = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
    const onSelectInspector = vi.fn();
    const hook = renderInspectorHook({
      inspector: "copilot",
      project: baseProject,
      loadJobs,
      onSelectInspector,
    });

    expect(hook.result().inspector).toBe("copilot");

    hook.rerender({ inspector: "review", project: baseProject, loadJobs, onSelectInspector });
    expect(hook.result().inspector).toBe("review");

    hook.rerender({ inspector: "history", project: baseProject, loadJobs, onSelectInspector });
    expect(hook.result().inspector).toBe("history");

    hook.rerender({ inspector: "export", project: baseProject, loadJobs, onSelectInspector });
    expect(hook.result().inspector).toBe("export");

    hook.rerender({ inspector: "settings", project: baseProject, loadJobs, onSelectInspector });
    expect(hook.result().inspector).toBe("settings");
    expect(loadJobs).not.toHaveBeenCalled();
  });

  it("requests navigation first and loads jobs when the controlled route selects Jobs", () => {
    const loadJobs = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
    const onSelectInspector = vi.fn();
    const hook = renderInspectorHook({
      inspector: "copilot",
      project: baseProject,
      loadJobs,
      onSelectInspector,
    });

    expect(loadJobs).not.toHaveBeenCalled();

    act(() => {
      hook.result().setInspector("jobs");
    });

    expect(onSelectInspector).toHaveBeenCalledWith("jobs");
    expect(hook.result().inspector).toBe("copilot");
    expect(loadJobs).not.toHaveBeenCalled();

    hook.rerender({ inspector: "jobs", project: baseProject, loadJobs, onSelectInspector });
    expect(hook.result().inspector).toBe("jobs");
    expect(loadJobs).toHaveBeenCalledTimes(1);
  });

  it("reloads a visible Jobs inspector once when project ownership changes", () => {
    const firstLoad = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
    const secondLoad = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
    const onSelectInspector = vi.fn();
    const hook = renderInspectorHook({
      inspector: "jobs",
      project: baseProject,
      loadJobs: firstLoad,
      onSelectInspector,
    });
    expect(firstLoad).toHaveBeenCalledTimes(1);

    hook.rerender({
      inspector: "jobs",
      project: project({ id: "project-2" }),
      loadJobs: secondLoad,
      onSelectInspector,
    });

    expect(secondLoad).toHaveBeenCalledTimes(1);
  });

  it("keeps Jobs lazy when project ownership changes behind another inspector", () => {
    const firstLoad = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
    const secondLoad = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
    const onSelectInspector = vi.fn();
    const hook = renderInspectorHook({
      inspector: "review",
      project: baseProject,
      loadJobs: firstLoad,
      onSelectInspector,
    });

    hook.rerender({
      inspector: "review",
      project: project({ id: "project-2" }),
      loadJobs: secondLoad,
      onSelectInspector,
    });
    expect(firstLoad).not.toHaveBeenCalled();
    expect(secondLoad).not.toHaveBeenCalled();

    hook.rerender({
      inspector: "jobs",
      project: project({ id: "project-2" }),
      loadJobs: secondLoad,
      onSelectInspector,
    });
    expect(secondLoad).toHaveBeenCalledTimes(1);
  });

  it("copies the selected project into settings form state", () => {
    const loadJobs = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
    const onSelectInspector = vi.fn();
    const hook = renderInspectorHook({
      inspector: "settings",
      project: baseProject,
      loadJobs,
      onSelectInspector,
    });

    expect(hook.result().settingsForm).toEqual({
      title: "Clockwork Harbor",
      description: "A harbor of brass clocks.",
      provider: "dashscope",
    });

    hook.rerender({
      inspector: "settings",
      project: {
        ...baseProject,
        title: "Mock Harbor",
        description: "",
        settings: {},
      },
      loadJobs,
      onSelectInspector,
    });

    expect(hook.result().settingsForm).toEqual({
      title: "Mock Harbor",
      description: "",
      provider: "mock",
    });
  });
});
