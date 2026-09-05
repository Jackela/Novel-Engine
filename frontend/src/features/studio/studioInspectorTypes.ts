import type { Dispatch, FormEvent, SetStateAction } from "react";

import type {
  ExportFormat,
  LoreStatus,
  ProviderInfo,
  Review,
  RevisionSummary,
  StudioExport,
  StudioJob,
  StudioJobSummary,
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
  historyInitialized?: boolean;
  isLoadingHistory?: boolean;
  historyError?: string | null;
  onRetryHistory?: () => void | Promise<void>;
  exportingFormat: ExportFormat | null;
  retryingFormat?: ExportFormat | null;
  failedFormat: ExportFormat | null;
  errorForExport: string | null;
  onExport?: (format: ExportFormat) => void | Promise<void>;
  onRetryExport?: (format: ExportFormat) => void | Promise<void>;
}

export interface InspectorReviewModel {
  latestReview: Review | null;
  historyInitialized?: boolean;
  isLoadingHistory?: boolean;
  historyError?: string | null;
  actionError?: string | null;
  onRetryHistory?: () => void | Promise<void>;
  onRunReview: () => void | Promise<void>;
}

export interface InspectorHistoryModel {
  revisions: RevisionSummary[];
  loadedRevisionId: string | null;
  historyInitialized: boolean;
  hasOlderRevisions: boolean;
  isLoadingOlder: boolean;
  isLoadingHistory: boolean;
  onLoadOlderRevisions: () => void | Promise<void>;
  onRestoreRevision: (revisionId: string) => void | Promise<void>;
}

export interface InspectorJobsModel {
  jobs: StudioJobSummary[];
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
  error: string | null;
  onUpdateSettings: (event: FormEvent) => Promise<void>;
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

/** #466: chapter-scoped beat association for the active chapter. */
export interface InspectorBeatModel {
  /** React identity for the active chapter. */
  readonly documentId: string;
  /**
   * Stored-reference authority: the successful command's normalized title,
   * or null when unlinked. The independently resolved display is not
   * authority and may differ after an outline rename.
   */
  readonly beatRef: string | null;
  /** Pending belongs to this chapter, never to whichever entry is active now. */
  readonly isSaving: boolean;
  /** Failed mutation for this chapter; other documents do not inherit it. */
  readonly error: string | null;
  /** Keeps the failed title available when the author returns to this chapter. */
  readonly attemptedTitle: string | null;
  /** Links to a beat title, or clears the association with null. */
  readonly link: (beat: string | null) => Promise<void>;
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
  beat: InspectorBeatModel | null;
}
