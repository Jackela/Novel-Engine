import { afterEach, describe, expect, it, vi } from "vitest";

import { createMountHarness } from "@/test/harness";

import { StudioInspector } from "./StudioInspector";
import type { StudioInspectorModel } from "./studioInspectorTypes";

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
});

function inspectorModel(
  documents: StudioInspectorModel["lore"]["documents"],
): StudioInspectorModel {
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
    review: { latestReview: null, summaries: [], onRunReview: vi.fn() },
    history: {
      revisions: [],
      loadedRevisionId: null,
      historyInitialized: true,
      hasOlderRevisions: false,
      isLoadingOlder: false,
      isLoadingHistory: false,
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
    stats: { projectId: "project-1" },
    lore: { projectId: "project-1", provider: "mock", documents },
    settings: {
      settingsForm: { title: "Novel", description: "", provider: "mock" },
      error: null,
      providers: [],
      onUpdateSettings: vi.fn(),
      setSettingsForm: vi.fn(),
      diagnostics: { onExport: vi.fn(), isExporting: false, error: null },
    },
    loreStatus: null,
    beat: null,
  };
}

function renderInspector(
  inspector: StudioInspectorModel["lore"],
  selection: "lore" | "stats" = "lore",
): HTMLDivElement {
  return harness.mount(
    <StudioInspector
      error={null}
      inspector={selection}
      setInspector={vi.fn()}
      model={inspectorModel(inspector.documents)}
    />,
  ).container;
}

describe("StudioInspector lore tab (#614)", () => {
  it("activates the lore tab as the wizard host with stats still present", () => {
    const container = renderInspector({ projectId: "project-1", provider: "mock", documents: [] });

    const tabs = Array.from(container.querySelectorAll('[role="tab"]'));
    const activeTab = tabs.find((tab) => tab.getAttribute("aria-selected") === "true");
    expect(activeTab?.textContent).toContain("Lore");
    // Both late additions coexist in one tablist: stats (#653) then lore (#614).
    expect(tabs.at(-2)?.textContent).toContain("Stats");
    expect(tabs.at(-1)?.textContent).toContain("Lore");
    expect(container.textContent).toContain("Lorebook wizard");
  });

  it("keeps the stats panel its own surface when lore is inactive", () => {
    const container = renderInspector(
      { projectId: "project-1", provider: "mock", documents: [] },
      "stats",
    );
    const panels = Array.from(container.querySelectorAll('[role="tabpanel"]'));
    const visible = panels.filter((panel) => !panel.hasAttribute("hidden"));
    expect(visible).toHaveLength(1);
    expect(container.textContent).toContain("Writing stats");
  });
});
