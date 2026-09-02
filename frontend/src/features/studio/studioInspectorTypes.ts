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
import type { JobsLoadInitiator, ProposalAuditStatus } from "./hooks/useStudioJobs";

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
    loadingInitiator?: JobsLoadInitiator | null;
    retrying: boolean;
    retryingJobId?: string | null;
    retryGated?: boolean;
  };
  settings: boolean;
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
  onRunProposal: (operation: "continue" | "rewrite") => void | Promise<void>;
  onAcceptProposal: () => void | Promise<void>;
  /** #308: aborts the running proposal stream. */
  onStopProposal?: () => void;
  proposalOutcomeUnknown?: boolean;
  proposalAuditStatus?: ProposalAuditStatus;
  unknownAttemptOperation?: "continue" | "rewrite";
  onRetryProposalAudit?: () => void | Promise<void>;
  setInstruction: Dispatch<SetStateAction<string>>;
  setProposal: Dispatch<SetStateAction<StudioJob | null>>;
}

export interface InspectorExportModel {
  exports: StudioExport[];
  exportingFormat: ExportFormat | null;
  retryingFormat?: ExportFormat | null;
  failedFormat: ExportFormat | null;
  errorForExport: string | null;
  onExport?: (format: ExportFormat) => void | Promise<void>;
  onRetryExport?: (format: ExportFormat) => void | Promise<void>;
}

export interface InspectorReviewModel {
  latestReview: Review | null;
  onRunReview: () => void | Promise<void>;
}

export interface InspectorHistoryModel {
  revisions: Revision[];
  loadedRevisionId: string | null;
  onRestoreRevision: (revisionId: string) => void | Promise<void>;
}

export interface InspectorJobsModel {
  jobs: StudioJob[];
  hasOlderJobs: boolean;
  onLoadJobs: () => void | Promise<void>;
  onLoadOlderJobs: () => void | Promise<void>;
  onRetryJob: (jobId: string) => void | Promise<void>;
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
  /** Pending belongs to this document, never to whichever entry is active now. */
  readonly isSaving: boolean;
  /** Failed mutation for this document; other documents do not inherit it. */
  readonly error: string | null;
  /** Keeps the failed selection available when the author returns to this entry. */
  readonly attemptedStatus: LoreStatus | null;
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
