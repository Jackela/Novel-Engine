import { act, type ReactElement, type Ref, useRef } from "react";
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { project } from "@/test/factories";
import { createMountHarness, deferred, flushEffects } from "@/test/harness";

import { useStudioPageModel } from "./hooks/useStudioPageModel";
import { StudioPage } from "./StudioPage";

vi.mock("./hooks/useStudioPageModel", () => ({
  useStudioPageModel: vi.fn(),
}));

vi.mock("./StudioPageView", () => ({
  StudioPageView: ({ headingRef }: { headingRef?: Ref<HTMLHeadingElement> }) => (
    <main aria-labelledby="ready-project-title" data-studio-ready>
      <h1 id="ready-project-title" ref={headingRef} tabIndex={-1}>
        Studio ready
      </h1>
    </main>
  ),
}));

const harness = createMountHarness();
let currentPath = "";
const lifecycleTokens = new Map<string, symbol>();
const readyProject = project({ id: "project-1", title: "Harbor" });
const readyViewProps = {} as NonNullable<ReturnType<typeof useStudioPageModel>["viewProps"]>;

function LocationProbe(): null {
  const location = useLocation();
  currentPath = `${location.pathname}${location.search}`;
  return null;
}

function ProjectSwitch(): ReactElement {
  const navigate = useNavigate();
  return (
    <button onClick={() => navigate("/projects/project-2/manuscript")} type="button">
      Switch project
    </button>
  );
}

function useLifecycleProbe(projectId: string): ReturnType<typeof useStudioPageModel> {
  const token = useRef(Symbol(projectId));
  lifecycleTokens.set(projectId, token.current);
  return {
    project: null,
    viewProps: null,
    loadError: null,
    isLoading: true,
    retryLoad: vi.fn().mockResolvedValue(undefined),
  };
}

function studioTree(path: string, includeSwitch = false): ReactElement {
  return (
    <MemoryRouter initialEntries={[path]}>
      <LocationProbe />
      {includeSwitch ? <ProjectSwitch /> : null}
      <Routes>
        <Route path="/projects" element={<p>Project library</p>} />
        <Route path="/projects/:projectId/:section?" element={<StudioPage />} />
      </Routes>
    </MemoryRouter>
  );
}

function mountStudio(path: string, includeSwitch = false) {
  return harness.mount(studioTree(path, includeSwitch));
}

function renderStudio(path: string, includeSwitch = false): HTMLDivElement {
  return mountStudio(path, includeSwitch).container;
}

beforeEach(() => {
  currentPath = "";
  lifecycleTokens.clear();
  vi.mocked(useStudioPageModel).mockReturnValue({
    project: null,
    viewProps: null,
    loadError: null,
    isLoading: true,
    retryLoad: vi.fn().mockResolvedValue(undefined),
  });
});

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

describe("StudioPage route lifecycle", () => {
  it("replaces invalid path and Inspector state with the canonical URL", async () => {
    renderStudio("/projects/project-1/not-a-section?inspector=jobs");

    await flushEffects();

    expect(currentPath).toBe("/projects/project-1/manuscript");
    expect(useStudioPageModel).toHaveBeenCalledWith(
      "project-1",
      {
        section: "manuscript",
        inspector: "copilot",
        canonicalPath: "/projects/project-1/manuscript",
      },
      expect.any(Function),
    );
  });

  it("offers working retry and project-library recovery for operational failures", async () => {
    const retryLoad = vi.fn().mockResolvedValue(undefined);
    vi.mocked(useStudioPageModel).mockReturnValue({
      project: null,
      viewProps: null,
      loadError: "Service unavailable.",
      isLoading: false,
      retryLoad,
    });
    const container = renderStudio("/projects/project-1/manuscript");

    const retry = Array.from(container.querySelectorAll("button")).find(
      (button) => button.textContent === "Try again",
    );
    const back = Array.from(container.querySelectorAll("button")).find(
      (button) => button.textContent === "Back to projects",
    );
    expect(container.querySelector('[role="alert"]')?.textContent).toContain(
      "Service unavailable.",
    );

    act(() => retry?.click());
    expect(retryLoad).toHaveBeenCalledTimes(1);

    act(() => back?.click());
    await flushEffects();
    expect(currentPath).toBe("/projects");
  });

  it("keeps the recovery surface and user-moved focus during a failed retry", async () => {
    const retryCommand = deferred<void>();
    const retryLoad = vi.fn(() => retryCommand.promise);
    const failedModel = {
      project: null,
      viewProps: null,
      loadError: "Service unavailable.",
      isLoading: false,
      retryLoad,
    };
    vi.mocked(useStudioPageModel).mockReturnValue(failedModel);
    const mounted = mountStudio("/projects/project-1/manuscript");
    const retry = mounted.container.querySelector<HTMLButtonElement>(".ui-command--primary");
    if (retry === null) throw new Error("Expected the retry command.");

    retry.focus();
    act(() => retry.click());
    vi.mocked(useStudioPageModel).mockReturnValue({ ...failedModel, isLoading: true });
    act(() => mounted.root.render(studioTree("/projects/project-1/manuscript")));

    const pendingRetry = mounted.container.querySelector<HTMLButtonElement>(".ui-command--primary");
    const back = Array.from(mounted.container.querySelectorAll<HTMLButtonElement>("button")).find(
      (button) => button.textContent === "Back to projects",
    );
    expect(mounted.container.querySelector('[role="alert"]')?.textContent).toContain(
      "Service unavailable.",
    );
    expect(pendingRetry).toBeDisabled();
    expect(pendingRetry).toHaveAttribute("aria-busy", "true");
    expect(back).toBeEnabled();
    back?.focus();

    await act(async () => {
      retryCommand.resolve(undefined);
      await retryCommand.promise;
      vi.mocked(useStudioPageModel).mockReturnValue(failedModel);
      mounted.root.render(studioTree("/projects/project-1/manuscript"));
    });

    expect(document.activeElement).toBe(back);
  });

  it("returns focus to Try again when a failed retry leaves focus behind", async () => {
    const retryCommand = deferred<void>();
    const retryLoad = vi.fn(() => retryCommand.promise);
    const failedModel = {
      project: null,
      viewProps: null,
      loadError: "Still unavailable.",
      isLoading: false,
      retryLoad,
    };
    vi.mocked(useStudioPageModel).mockReturnValue(failedModel);
    const mounted = mountStudio("/projects/project-1/manuscript");
    const retry = mounted.container.querySelector<HTMLButtonElement>(".ui-command--primary");
    if (retry === null) throw new Error("Expected the retry command.");

    retry.focus();
    act(() => retry.click());
    vi.mocked(useStudioPageModel).mockReturnValue({ ...failedModel, isLoading: true });
    act(() => mounted.root.render(studioTree("/projects/project-1/manuscript")));

    await act(async () => {
      retryCommand.resolve(undefined);
      await retryCommand.promise;
      vi.mocked(useStudioPageModel).mockReturnValue(failedModel);
      mounted.root.render(studioTree("/projects/project-1/manuscript"));
    });

    expect(document.activeElement).toBe(
      mounted.container.querySelector<HTMLButtonElement>(".ui-command--primary"),
    );
  });

  it("moves retry focus to the stable Studio heading after recovery succeeds", async () => {
    const retryCommand = deferred<void>();
    const retryLoad = vi.fn(() => retryCommand.promise);
    const failedModel = {
      project: null,
      viewProps: null,
      loadError: "Service unavailable.",
      isLoading: false,
      retryLoad,
    };
    vi.mocked(useStudioPageModel).mockReturnValue(failedModel);
    const mounted = mountStudio("/projects/project-1/manuscript");
    const retry = mounted.container.querySelector<HTMLButtonElement>(".ui-command--primary");
    if (retry === null) throw new Error("Expected the retry command.");

    retry.focus();
    act(() => retry.click());
    vi.mocked(useStudioPageModel).mockReturnValue({ ...failedModel, isLoading: true });
    act(() => mounted.root.render(studioTree("/projects/project-1/manuscript")));

    await act(async () => {
      retryCommand.resolve(undefined);
      await retryCommand.promise;
      vi.mocked(useStudioPageModel).mockReturnValue({
        project: readyProject,
        viewProps: readyViewProps,
        loadError: null,
        isLoading: false,
        retryLoad,
      });
      mounted.root.render(studioTree("/projects/project-1/manuscript"));
    });

    const readyHeading =
      mounted.container.querySelector<HTMLHeadingElement>("#ready-project-title");
    expect(document.activeElement).toBe(readyHeading);
    expect(document.activeElement).not.toBe(document.body);
  });

  it("remounts the complete workbench when the route project identity changes", async () => {
    vi.mocked(useStudioPageModel).mockImplementation(useLifecycleProbe);
    const container = renderStudio("/projects/project-1/manuscript", true);
    const firstToken = lifecycleTokens.get("project-1");

    act(() => {
      Array.from(container.querySelectorAll("button"))
        .find((button) => button.textContent === "Switch project")
        ?.click();
    });
    await flushEffects();

    expect(currentPath).toBe("/projects/project-2/manuscript");
    expect(firstToken).toBeDefined();
    expect(lifecycleTokens.get("project-2")).toBeDefined();
    expect(lifecycleTokens.get("project-2")).not.toBe(firstToken);
  });
});
