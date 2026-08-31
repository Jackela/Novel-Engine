import type { Dispatch, FormEvent, SetStateAction } from "react";

import type {
  ExportFormat,
  LoreStatus,
  ProviderInfo,
  Review,
  Revision,
  StudioExport,
  StudioJob,
} from "@/app/types/studio";

export interface SettingsFormState {
  title: string;
  description: string;
  provider: string;
}

export interface InspectorPendingState {
  proposal: {
    running: boolean;
    accepting: boolean;
  };
  review: boolean;
  jobs: {
    loading: boolean;
    retrying: boolean;
    retryingJobId?: string | null;
  };
  settings: boolean;
  /** #444: lore lifecycle-status save pending. */
  loreStatus?: boolean;
  history?: {
    restoringRevisionId: string | null;
  };
}

/** #412: per-tab data/action groups, assembled once at the Inspector boundary. */
export interface InspectorCopilotModel {
  instruction: string;
  proposal: StudioJob | null;
  /** #308: markdown received so far while the proposal stream is running. */
  streamingText: string | null;
  onRunProposal: (operation: "continue" | "rewrite") => void;
  onAcceptProposal: () => void;
  /** #308: aborts the running proposal stream. */
  onStopProposal?: () => void;
  setInstruction: Dispatch<SetStateAction<string>>;
  setProposal: Dispatch<SetStateAction<StudioJob | null>>;
}

export interface InspectorExportModel {
  exports: StudioExport[];
  exportingFormat: ExportFormat | null;
  failedFormat: ExportFormat | null;
  errorForExport: string | null;
  onExport?: (format: ExportFormat) => void;
  onRetryExport?: (format: ExportFormat) => void;
}

export interface InspectorReviewModel {
  latestReview: Review | null;
  onRunReview: () => void;
}

export interface InspectorHistoryModel {
  revisions: Revision[];
  loadedRevisionId: string | null;
  onRestoreRevision: (revisionId: string) => void;
}

export interface InspectorJobsModel {
  jobs: StudioJob[];
  onLoadJobs: () => void;
  onRetryJob: (jobId: string) => void;
}

export interface InspectorUsageModel {
  /** #377: project scope for the lazily loaded usage panel. */
  projectId: string;
}

export interface InspectorSettingsModel {
  settingsForm: SettingsFormState;
  providers: ProviderInfo[];
  onUpdateSettings: (event: FormEvent) => void;
  setSettingsForm: Dispatch<SetStateAction<SettingsFormState>>;
}

/** #444: document-scoped lifecycle gate for the active lore entry. */
export interface InspectorLoreStatusModel {
  /** React identity for the active Lore entry. */
  readonly documentId: string;
  /** Server-observed baseline; the form owns only the unsaved selection. */
  readonly savedStatus: LoreStatus;
  /** Settles after the mutation owner has cleared its pending state. */
  readonly submit: (status: LoreStatus) => Promise<void>;
}

export interface StudioInspectorModel {
  copilot: InspectorCopilotModel;
  export: InspectorExportModel;
  review: InspectorReviewModel;
  history: InspectorHistoryModel;
  jobs: InspectorJobsModel;
  usage: InspectorUsageModel;
  settings: InspectorSettingsModel;
  loreStatus: InspectorLoreStatusModel | null;
}
