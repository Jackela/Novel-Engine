import { vi } from "vitest";

import type { StudioInspectorModel } from "../studioInspectorTypes";

/**
 * The #412 grouped per-tab inspector model every component fixture builds on:
 * empty state, mocked commands, and the DR-043/review additions the boundary
 * now carries.
 */
export function buildInspectorModel(): StudioInspectorModel {
  return {
    copilot: {
      instruction: "",
      proposal: null,
      streamingText: null,
      streamingInterrupted: false,
      streamingStopped: false,
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
    review: {
      selectedReview: null,
      selectedReviewId: null,
      onSelectReview: vi.fn(),
      summaries: [],
      onRunReview: vi.fn(),
    },
    history: {
      revisions: [],
      loadedRevisionId: null,
      historyInitialized: true,
      hasOlderRevisions: false,
      isLoadingOlder: false,
      isLoadingHistory: false,
      onLoadOlderRevisions: vi.fn(),
      onRestoreRevision: vi.fn(),
      preview: null,
    },
    jobs: {
      jobs: [],
      hasOlderJobs: false,
      onLoadJobs: vi.fn(),
      onLoadOlderJobs: vi.fn(),
      onRetryJob: vi.fn(),
      projectId: "project-1",
    },
    usage: { projectId: "project-1" },
    stats: { projectId: "project-1" },
    lore: { projectId: "project-1", provider: "mock", documents: [] },
    settings: {
      settingsForm: { title: "", description: "", provider: "" },
      error: null,
      providers: [],
      onUpdateSettings: vi.fn(),
      setSettingsForm: vi.fn(),
      diagnostics: { onExport: vi.fn(), isExporting: false, error: null },
    },
    // #444: no active Lore document in this fixture, so no panel renders.
    loreStatus: null,
    // #466: no active chapter in this fixture, so no beat panel renders.
    beat: null,
  };
}
