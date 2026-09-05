import type { ComponentProps, Dispatch, FormEvent, SetStateAction } from "react";
import type { NavigateFunction } from "react-router-dom";

import type {
  DocumentKind,
  DocumentSummary,
  LoreStatus,
  ProviderInfo,
  RevisionSummary,
  StudioDocument,
  StudioJobSummary,
} from "@/app/types/studio";

import type { StudioNavigator } from "../StudioNavigator";
import { isLoreEntryKind } from "../studioConstants";
import type {
  InspectorBeatModel,
  InspectorLoreStatusModel,
  SettingsFormState,
  StudioInspectorModel,
} from "../studioInspectorTypes";
import { buildProposalAuditView } from "./proposalAuditView";
import type { useExportDownload } from "./useExportDownload";
import type { useExportHistory } from "./useExportHistory";
import type { useLazyInspectorHistories } from "./useLazyInspectorHistories";
import type { BeatLifecycleState } from "./useStudioBeatActions";
import type { useStudioGeneration } from "./useStudioGeneration";
import type { LoreStatusLifecycleState } from "./useStudioLoreStatusActions";

type NavigatorProps = ComponentProps<typeof StudioNavigator>;

export interface StudioNavigatorModel
  extends Omit<NavigatorProps, "onNavigateSection" | "onCreateDocument" | "onMoveDocument"> {
  createDocument: (kind: DocumentKind) => void | Promise<void>;
  moveDocument: (documentId: string, direction: -1 | 1) => void | Promise<void>;
}

export function buildStudioNavigatorProps(
  model: StudioNavigatorModel,
  navigate: NavigateFunction,
): NavigatorProps {
  const { createDocument, moveDocument, ...state } = model;
  return {
    ...state,
    onNavigateSection: (nextSection) => navigate(`/projects/${model.project.id}/${nextSection}`),
    onCreateDocument: createDocument,
    onMoveDocument: moveDocument,
  };
}

/**
 * Adapt the active shell summary into the concrete Lore editor seam. The
 * returned submit function preserves the mutation owner's completion Promise.
 */
export function buildLoreStatusModel(
  document: Pick<DocumentSummary, "id" | "kind" | "lore_status"> | null,
  changeLoreStatus: (documentId: string, status: LoreStatus) => Promise<void>,
  lifecycle: LoreStatusLifecycleState,
): InspectorLoreStatusModel | null {
  if (
    document === null ||
    !isLoreEntryKind(document.kind) ||
    document.lore_status === null ||
    document.lore_status === undefined
  ) {
    return null;
  }
  const documentId = document.id;
  return {
    documentId,
    savedStatus: document.lore_status,
    isSaving: lifecycle.isSaving,
    error: lifecycle.error,
    attemptedStatus: lifecycle.attemptedStatus,
    submit: (status) => changeLoreStatus(documentId, status),
  };
}

/**
 * Adapt the active shell summary into the chapter beat seam (#466). The
 * returned link function preserves the mutation owner's completion Promise;
 * only chapters associate with outline beats.
 */
export function buildBeatModel(
  document: Pick<DocumentSummary, "id" | "kind" | "beat_ref"> | null,
  linkBeat: (documentId: string, beat: string | null) => Promise<void>,
  lifecycle: BeatLifecycleState,
): InspectorBeatModel | null {
  if (document === null || document.kind !== "chapter") return null;
  const documentId = document.id;
  return {
    documentId,
    beatRef: document.beat_ref,
    isSaving: lifecycle.isSaving,
    error: lifecycle.error,
    attemptedTitle: lifecycle.attemptedTitle,
    link: (beat) => linkBeat(documentId, beat),
  };
}

type ExportHistory = ReturnType<typeof useExportHistory>;
type ReviewHistory = ReturnType<typeof useLazyInspectorHistories>["review"];

/** Narrow document commands and their active identity (#444, #466). */
interface InspectorNarrowCommands {
  readonly activeSummary: DocumentSummary | null;
  readonly activeDocument: StudioDocument | null;
  readonly changeLoreStatus: (documentId: string, status: LoreStatus) => Promise<void>;
  readonly loreStatusFor: (documentId: string) => LoreStatusLifecycleState;
  readonly linkBeat: (documentId: string, beat: string | null) => Promise<void>;
  readonly beatFor: (documentId: string) => BeatLifecycleState;
}

/** Per-tab inputs the page model already owns (#412). */
export interface StudioInspectorModelInputs {
  readonly projectId: string;
  readonly copilot: ReturnType<typeof useStudioGeneration>["copilot"];
  readonly jobs: {
    readonly jobs: StudioJobSummary[];
    readonly hasOlderJobs: boolean;
    readonly onLoadJobs: () => void | Promise<void>;
    readonly onLoadOlderJobs: () => void | Promise<void>;
    readonly onRetryJob: (jobId: string) => void | Promise<void>;
  };
  readonly export: ReturnType<typeof useExportDownload> & { readonly history: ExportHistory };
  readonly review: {
    readonly history: ReviewHistory;
    readonly actionError: string | null;
    readonly onRunReview: () => void | Promise<void>;
  };
  readonly history: {
    readonly revisions: RevisionSummary[];
    readonly loadedRevisionId: string | null;
    readonly historyInitialized: boolean;
    readonly hasOlderRevisions: boolean;
    readonly isLoadingOlder: boolean;
    readonly isLoadingHistory: boolean;
    readonly onLoadOlderRevisions: () => void | Promise<void>;
    readonly onRestoreRevision: (revisionId: string) => void | Promise<void>;
  };
  readonly settings: {
    readonly settingsForm: SettingsFormState;
    readonly providers: ProviderInfo[];
    readonly error: string | null;
    readonly onUpdateSettings: (event: FormEvent) => Promise<void>;
    readonly setSettingsForm: Dispatch<SetStateAction<SettingsFormState>>;
  };
  readonly narrowCommands: InspectorNarrowCommands;
}

const IDLE_LORE_LIFECYCLE: LoreStatusLifecycleState = {
  isSaving: false,
  error: null,
  attemptedStatus: null,
};
const IDLE_BEAT_LIFECYCLE: BeatLifecycleState = {
  isSaving: false,
  error: null,
  attemptedTitle: null,
};

/**
 * Assemble the per-tab Inspector model once at the page boundary (#412)
 * instead of forwarding a props corridor through StudioPageView ->
 * Inspector -> Panels.
 */
export function buildStudioInspectorModel({
  projectId,
  copilot,
  jobs,
  export: exportPanel,
  review,
  history,
  settings,
  narrowCommands,
}: StudioInspectorModelInputs): StudioInspectorModel {
  const { activeSummary, activeDocument, ...commands } = narrowCommands;
  const narrowDocument = activeDocument?.id === activeSummary?.id ? activeSummary : null;
  return {
    copilot: {
      instruction: copilot.instruction,
      proposal: copilot.proposal,
      streamingText: copilot.streamingText,
      onRunProposal: copilot.runProposal,
      onAcceptProposal: copilot.acceptProposal,
      onStopProposal: () => copilot.stopProposal(),
      ...buildProposalAuditView(
        copilot.proposalOutcomeUnknown,
        copilot.proposalAuditStatus,
        copilot.retryProposalAudit,
      ),
      unknownAttemptOperation: copilot.unknownAttemptOperation,
      setInstruction: copilot.setInstruction,
      setProposal: copilot.setProposal,
    },
    export: {
      exports: exportPanel.history.exports,
      historyInitialized: exportPanel.history.historyInitialized,
      isLoadingHistory: exportPanel.history.isLoadingHistory,
      historyError: exportPanel.history.historyError,
      onRetryHistory: exportPanel.history.onRetryHistory,
      hasOlderExports: exportPanel.history.hasOlderExports,
      isLoadingOlderExports: exportPanel.history.isLoadingOlderExports,
      olderExportsError: exportPanel.history.olderError,
      onLoadOlderExports: exportPanel.history.onLoadOlderExports,
      exportingFormat: exportPanel.exportingFormat,
      retryingFormat: exportPanel.retryingFormat,
      failedFormat: exportPanel.failedFormat,
      errorForExport: exportPanel.exportError,
      onExport: exportPanel.exportProject,
      onRetryExport: exportPanel.retryExport,
    },
    review: {
      latestReview: review.history.data[0] ?? null,
      historyInitialized: review.history.initialized,
      isLoadingHistory: review.history.isLoading,
      historyError: review.history.error,
      actionError: review.actionError,
      onRetryHistory: review.history.retry,
      onRunReview: review.onRunReview,
    },
    history: {
      revisions: history.revisions,
      loadedRevisionId: history.loadedRevisionId,
      historyInitialized: history.historyInitialized,
      hasOlderRevisions: history.hasOlderRevisions,
      isLoadingOlder: history.isLoadingOlder,
      isLoadingHistory: history.isLoadingHistory,
      onLoadOlderRevisions: history.onLoadOlderRevisions,
      onRestoreRevision: history.onRestoreRevision,
    },
    jobs: {
      jobs: jobs.jobs,
      hasOlderJobs: jobs.hasOlderJobs,
      onLoadJobs: jobs.onLoadJobs,
      onLoadOlderJobs: jobs.onLoadOlderJobs,
      onRetryJob: jobs.onRetryJob,
    },
    usage: { projectId },
    settings: {
      settingsForm: settings.settingsForm,
      providers: settings.providers,
      error: settings.error,
      onUpdateSettings: settings.onUpdateSettings,
      setSettingsForm: settings.setSettingsForm,
    },
    loreStatus: buildLoreStatusModel(
      narrowDocument,
      commands.changeLoreStatus,
      activeDocument ? commands.loreStatusFor(activeDocument.id) : IDLE_LORE_LIFECYCLE,
    ),
    beat: buildBeatModel(
      narrowDocument,
      commands.linkBeat,
      activeDocument ? commands.beatFor(activeDocument.id) : IDLE_BEAT_LIFECYCLE,
    ),
  };
}
