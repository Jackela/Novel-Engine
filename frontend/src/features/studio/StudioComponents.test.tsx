import { act, type ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { chapter, projectWith } from "@/test/factories";
import { createMountHarness } from "@/test/harness";

import { StudioInspector } from "./StudioInspector";
import { StudioStatusbar } from "./StudioStatusbar";
import { StudioTopbar } from "./StudioTopbar";
import type { StudioInspectorModel } from "./studioInspectorTypes";

/** #412: grouped per-tab model matching the new Inspector boundary. */
function buildInspectorModel(): StudioInspectorModel {
  return {
    copilot: {
      instruction: "",
      proposal: null,
      streamingText: null,
      onRunProposal: vi.fn(),
      onAcceptProposal: vi.fn(),
      setInstruction: vi.fn(),
      setProposal: vi.fn(),
    },
    export: {
      exports: [],
      exportingFormat: null,
      failedFormat: null,
      errorForExport: null,
    },
    review: { latestReview: null, onRunReview: vi.fn() },
    history: {
      revisions: [],
      loadedRevisionId: null,
      historyInitialized: true,
      hasOlderRevisions: false,
      isLoadingOlder: false,
      onLoadOlderRevisions: vi.fn(),
      onRestoreRevision: vi.fn(),
    },
    jobs: {
      jobs: [],
      hasOlderJobs: false,
      onLoadJobs: vi.fn(),
      onLoadOlderJobs: vi.fn(),
      onRetryJob: vi.fn(),
    },
    usage: { projectId: "project-1" },
    settings: {
      settingsForm: { title: "", description: "", provider: "" },
      providers: [],
      onUpdateSettings: vi.fn(),
      setSettingsForm: vi.fn(),
    },
    // #444: no active Lore document in this fixture, so no panel renders.
    loreStatus: null,
  };
}

const harness = createMountHarness();

function render(element: ReactElement): HTMLDivElement {
  return harness.mount(element).container;
}

function click(element: Element | null): void {
  if (!(element instanceof HTMLElement)) {
    throw new Error("Expected a clickable element.");
  }
  act(() => {
    element.click();
  });
}

afterEach(() => {
  harness.cleanup();
});

const baseDocument = chapter("doc-1", {
  title: "Opening",
  position: 1,
  current_revision_id: "revision-abcdefghi",
  content_markdown: "# Opening",
  revision_source: "author",
  word_count: 42,
});

const secondDocument = {
  ...baseDocument,
  id: "doc-2",
  title: "Second",
  position: 2,
  current_revision_id: "revision-second",
  word_count: 12,
};

const baseProject = projectWith([baseDocument, secondDocument]);

describe("Studio split components", () => {
  it("exposes the inspector tabs and active panel as an associated ARIA tab set", () => {
    const setInspector = vi.fn();
    const container = render(
      <StudioInspector
        error={null}
        inspector="copilot"
        setInspector={setInspector}
        model={buildInspectorModel()}
      />,
    );

    const tablist = container.querySelector('[role="tablist"]');
    const disclosure = container.querySelector("details.studio-inspector__disclosure");
    const tabs = Array.from(container.querySelectorAll('[role="tab"]'));
    const activeTab = tabs.find((tab) => tab.getAttribute("aria-selected") === "true");
    const panels = Array.from(container.querySelectorAll('[role="tabpanel"]'));
    const activePanel = panels.find((panel) => !panel.hasAttribute("hidden"));

    expect(tablist).not.toBeNull();
    expect(disclosure).not.toBeNull();
    expect(disclosure?.querySelector("summary")?.textContent).toContain("Inspector");
    expect(disclosure?.hasAttribute("open")).toBe(true);
    expect(tabs).toHaveLength(6);
    expect(panels).toHaveLength(6);
    expect(activeTab?.textContent).toContain("Copilot");
    expect(tabs.filter((tab) => tab.getAttribute("aria-selected") === "false")).toHaveLength(5);
    expect(activeTab?.getAttribute("aria-controls")).toBe(activePanel?.id);
    expect(activePanel?.getAttribute("aria-labelledby")).toBe(activeTab?.id);
    expect(
      tabs.every((tab) => panels.some((panel) => panel.id === tab.getAttribute("aria-controls"))),
    ).toBe(true);
    expect(panels.filter((panel) => panel.hasAttribute("hidden"))).toHaveLength(5);
    expect(container.querySelector('form[aria-label="Lore status"]')).toBeNull();

    click(tabs.find((tab) => tab.textContent?.includes("Review")) ?? null);
    expect(setInspector).toHaveBeenCalledWith("review");
  });

  it("supports APG tablist keyboard navigation and keeps one tab in the tab sequence", () => {
    const setInspector = vi.fn();
    const container = render(
      <StudioInspector
        error={null}
        inspector="copilot"
        setInspector={setInspector}
        model={buildInspectorModel()}
      />,
    );

    const tabs = Array.from(container.querySelectorAll<HTMLButtonElement>('[role="tab"]'));
    expect(tabs.filter((tab) => tab.tabIndex === 0)).toHaveLength(1);

    act(() => {
      tabs[0].dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
    });
    expect(setInspector).toHaveBeenCalledWith("review");
    // #411: focus moves through the tab ref array, not DOM queries.
    expect(document.activeElement).toBe(tabs[1]);

    act(() => {
      tabs[0].dispatchEvent(new KeyboardEvent("keydown", { key: "End", bubbles: true }));
    });
    expect(setInspector).toHaveBeenCalledWith("usage");
    expect(document.activeElement).toBe(tabs[5]);

    act(() => {
      tabs[2].dispatchEvent(new KeyboardEvent("keydown", { key: "Home", bubbles: true }));
    });
    expect(setInspector).toHaveBeenCalledWith("copilot");
    expect(document.activeElement).toBe(tabs[0]);
  });

  it("does not expose an unselected tablist while the settings route is active", () => {
    const container = render(
      <StudioInspector
        error={null}
        inspector="settings"
        setInspector={vi.fn()}
        model={buildInspectorModel()}
      />,
    );

    const tabs = Array.from(container.querySelectorAll('[role="tab"]'));

    expect(container.querySelector('[role="tablist"]')).toBeNull();
    expect(tabs).toHaveLength(0);
    // #411: no orphan tabpanels without a tablist in the settings state.
    expect(container.querySelectorAll('[role="tabpanel"]')).toHaveLength(0);
    expect(container.querySelector("form.studio-inspector__panel")).not.toBeNull();
  });

  it("renders the contextual Lore editor only inside Copilot", () => {
    const model = buildInspectorModel();
    model.loreStatus = {
      documentId: "character-1",
      savedStatus: "draft",
      isSaving: false,
      error: null,
      attemptedStatus: null,
      submit: vi.fn().mockResolvedValue(undefined),
    };

    const copilot = render(
      <StudioInspector error={null} inspector="copilot" setInspector={vi.fn()} model={model} />,
    );
    const history = render(
      <StudioInspector error={null} inspector="history" setInspector={vi.fn()} model={model} />,
    );
    const settings = render(
      <StudioInspector error={null} inspector="settings" setInspector={vi.fn()} model={model} />,
    );

    expect(copilot.querySelector('form[aria-label="Lore status"]')).not.toBeNull();
    expect(history.querySelector('form[aria-label="Lore status"]')).toBeNull();
    expect(settings.querySelector('form[aria-label="Lore status"]')).toBeNull();
  });

  it("keeps a Lore save failure visible while the contextual Export tab is active", () => {
    const model = buildInspectorModel();
    model.loreStatus = {
      documentId: "character-1",
      savedStatus: "draft",
      isSaving: false,
      error: "Unable to update the lore status.",
      attemptedStatus: "stable",
      submit: vi.fn().mockResolvedValue(undefined),
    };
    const container = render(
      <StudioInspector error={null} inspector="export" setInspector={vi.fn()} model={model} />,
    );

    const alerts = Array.from(container.querySelectorAll('[role="alert"]'));
    expect(alerts).toHaveLength(1);
    expect(alerts[0]?.textContent).toContain("Unable to update the lore status.");
  });

  it("keeps distinct Lore and workflow failures readable at the same time", () => {
    const model = buildInspectorModel();
    model.loreStatus = {
      documentId: "character-1",
      savedStatus: "draft",
      isSaving: false,
      error: "Unable to update the lore status.",
      attemptedStatus: "stable",
      submit: vi.fn().mockResolvedValue(undefined),
    };
    const container = render(
      <StudioInspector
        error="Unable to create a proposal."
        inspector="copilot"
        setInspector={vi.fn()}
        model={model}
      />,
    );

    const alertText = Array.from(container.querySelectorAll('[role="alert"]')).map(
      (alert) => alert.textContent,
    );
    expect(alertText).toEqual([
      "Unable to update the lore status.",
      "Unable to create a proposal.",
    ]);
  });

  it("does not duplicate an Export failure already rendered by the Export workflow", () => {
    const model = buildInspectorModel();
    model.export.errorForExport = "Unable to export the project.";
    const container = render(
      <StudioInspector
        error="Unable to export the project."
        inspector="export"
        setInspector={vi.fn()}
        model={model}
      />,
    );

    expect(container.querySelectorAll('[role="alert"]')).toHaveLength(1);
  });

  it("keeps topbar navigation focused on returning to the project library", () => {
    const back = vi.fn();

    const container = render(<StudioTopbar project={baseProject} onBack={back} />);

    expect(container.querySelector(".ui-brand")?.textContent).toContain("Test Engine");
    expect(container.textContent).toContain("Clockwork Harbor");
    click(container.querySelector('button[aria-label="Back to projects"]'));
    expect(back).toHaveBeenCalledTimes(1);
    expect(container.querySelector(".editor-export-menu")).toBeNull();
  });

  it("renders the build identity in the Studio status bar", () => {
    const container = render(
      <StudioStatusbar
        activeDocument={baseDocument}
        loadedRevisionId={baseDocument.current_revision_id}
        saveState="saved"
      />,
    );

    expect(container.textContent).toContain("Test Engine test");
  });
});
