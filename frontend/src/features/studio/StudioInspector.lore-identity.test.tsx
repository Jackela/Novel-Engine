import { getByRole } from "@testing-library/dom";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createMountHarness } from "@/test/harness";

import { StudioInspector } from "./StudioInspector";
import type { InspectorLoreStatusModel, StudioInspectorModel } from "./studioInspectorTypes";

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
});

function inspectorModel(loreStatus: InspectorLoreStatusModel): StudioInspectorModel {
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
    settings: {
      settingsForm: { title: "Novel", description: "", provider: "mock" },
      error: null,
      providers: [],
      onUpdateSettings: vi.fn(),
      setSettingsForm: vi.fn(),
    },
    loreStatus,
  };
}

function renderInspector(loreStatus: InspectorLoreStatusModel) {
  return (
    <StudioInspector
      error={null}
      inspector="copilot"
      setInspector={vi.fn()}
      model={inspectorModel(loreStatus)}
    />
  );
}

describe("StudioInspector Lore identity", () => {
  it("shows only the active document's pending, attempted, and failure state", () => {
    const submit = vi.fn().mockResolvedValue(undefined);
    const { container, root } = harness.mount(
      renderInspector({
        documentId: "character-a",
        savedStatus: "draft",
        isSaving: true,
        error: null,
        attemptedStatus: "stable",
        submit,
      }),
    );

    expect(getByRole(container, "form", { name: "Lore status" })).toHaveAttribute(
      "aria-busy",
      "true",
    );

    act(() => {
      root.render(
        renderInspector({
          documentId: "world-b",
          savedStatus: "stable",
          isSaving: false,
          error: null,
          attemptedStatus: null,
          submit,
        }),
      );
    });

    expect(getByRole(container, "form", { name: "Lore status" })).toHaveAttribute(
      "aria-busy",
      "false",
    );
    expect(getByRole(container, "combobox", { name: "Lore status" })).toBeEnabled();
    expect(container.querySelector('[role="alert"]')).toBeNull();

    act(() => {
      root.render(
        renderInspector({
          documentId: "character-a",
          savedStatus: "draft",
          isSaving: false,
          error: "Mara status was rejected.",
          attemptedStatus: "stable",
          submit,
        }),
      );
    });

    expect(getByRole(container, "alert")).toHaveTextContent("Mara status was rejected.");
    expect(getByRole(container, "combobox", { name: "Lore status" })).toHaveValue("stable");
    expect(getByRole(container, "button", { name: "Save status" })).toBeEnabled();
  });
});
