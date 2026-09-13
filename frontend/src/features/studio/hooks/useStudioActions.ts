import type { Dispatch, SetStateAction } from "react";

import type { Project, ReviewsPage } from "@/app/types/studio";
import type { SettingsFormState } from "../studioInspectorTypes";
import { useProjectSettingsUpdate } from "./useProjectSettingsUpdate";
import type { StudioActionErrorPublishers } from "./useStudioActionOwner";
import { useStudioActionOwner } from "./useStudioActionOwner";
import { useStudioBeatActions } from "./useStudioBeatActions";
import { useStudioChapterPlacement } from "./useStudioChapterPlacement";
import { useStudioDocumentActions } from "./useStudioDocumentActions";
import { useStudioDocumentDeletion } from "./useStudioDocumentDeletion";
import { useStudioJobActions } from "./useStudioJobActions";
import type { JobsFreshLoadInitiator } from "./useStudioJobs";
import { useStudioLoreStatusActions } from "./useStudioLoreStatusActions";

export type { StudioActionErrorPublishers };

interface UseStudioActionsOptions {
  project: Project | null;
  projectId: string;
  setProject: Dispatch<SetStateAction<Project | null>>;
  setReviewPage: (page: ReviewsPage) => void;
  setError: Dispatch<SetStateAction<string | null>>;
  errorPublishers?: Partial<StudioActionErrorPublishers>;
  setActiveId: Dispatch<SetStateAction<string | null>>;
  settingsForm: SettingsFormState;
  setSettingsForm?: Dispatch<SetStateAction<SettingsFormState>>;
  onSettingsSessionLost?: () => void;
  onSettingsProjectMissing?: () => void;
  loadJobs: (initiator?: JobsFreshLoadInitiator) => Promise<void>;
  isProposalActionGated?: () => boolean;
}

const PROPOSAL_ACTIONS_UNGATED = () => false;

/**
 * Composition facade over the studio action domains: one mounted owner per
 * project generation, one sub-hook per state domain, and the flat action
 * surface pinned by the page model and its tests.
 */
export function useStudioActions({
  project,
  projectId,
  setProject,
  setReviewPage,
  setError,
  errorPublishers,
  setActiveId,
  settingsForm,
  setSettingsForm,
  onSettingsSessionLost,
  onSettingsProjectMissing,
  loadJobs,
  isProposalActionGated = PROPOSAL_ACTIONS_UNGATED,
}: UseStudioActionsOptions) {
  const { currentOwner, isCurrentOwner, publishError, clearSharedError } = useStudioActionOwner({
    projectId,
    setError,
    errorPublishers,
  });

  const documentActions = useStudioDocumentActions({
    project,
    projectId,
    setProject,
    setActiveId,
    currentOwner,
    isCurrentOwner,
    publishError,
  });
  const deletionActions = useStudioDocumentDeletion({
    project,
    projectId,
    setProject,
    setActiveId,
    currentOwner,
    isCurrentOwner,
  });
  const placementActions = useStudioChapterPlacement({
    project,
    projectId,
    setProject,
    currentOwner,
    isCurrentOwner,
  });
  const loreStatusActions = useStudioLoreStatusActions({
    project,
    projectId,
    setProject,
    currentOwner,
    isCurrentOwner,
    clearSharedError,
  });
  const beatActions = useStudioBeatActions({
    project,
    projectId,
    setProject,
    currentOwner,
    isCurrentOwner,
    clearSharedError,
  });
  const settingsUpdate = useProjectSettingsUpdate({
    project,
    projectId,
    settingsForm,
    setProject,
    setSettingsForm,
    setSettingsError: errorPublishers?.settings ?? setError,
    onSessionLost: onSettingsSessionLost,
    onProjectMissing: onSettingsProjectMissing,
  });
  const jobActions = useStudioJobActions({
    projectId,
    currentOwner,
    isCurrentOwner,
    publishError,
    setReviewPage,
    loadJobs,
    isProposalActionGated,
  });

  return {
    createDocument: documentActions.createDocument,
    moveDocument: documentActions.moveDocument,
    deleteDocument: deletionActions.deleteDocument,
    deletionFor: deletionActions.deletionFor,
    deletingDocument: deletionActions.deletingDocument,
    placeChapter: placementActions.placeChapter,
    placementFor: placementActions.placementFor,
    placingDocument: placementActions.placingDocument,
    runReview: jobActions.runReview,
    updateProjectSettings: settingsUpdate.updateProjectSettings,
    retryJob: jobActions.retryJob,
    changeLoreStatus: loreStatusActions.changeLoreStatus,
    loreStatusFor: loreStatusActions.loreStatusFor,
    linkBeat: beatActions.linkBeat,
    beatFor: beatActions.beatFor,
    pending: {
      ...documentActions.pending,
      ...jobActions.pending,
    },
    creatingDocumentKind: documentActions.creatingDocumentKind,
    movingDocument: documentActions.movingDocument,
    isCreatingDocument: documentActions.isCreatingDocument,
    isMovingDocument: documentActions.isMovingDocument,
    isRunningReview: jobActions.pending.runReview,
    isUpdatingSettings: settingsUpdate.isUpdatingSettings,
    isRetryingJob: jobActions.pending.retryJob,
    retryingJobId: jobActions.retryingJobId,
  };
}
