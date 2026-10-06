import type { Dispatch, SetStateAction } from "react";
import { useCallback, useEffect, useRef } from "react";

import type { Project, StudioDocument } from "@/app/types/studio";

import { useConflictServerPreview } from "./useConflictServerPreview";
import { useDocumentDraftActions } from "./useDocumentDraftActions";
import { useDocumentDraftAutosave } from "./useDocumentDraftAutosave";
import { useDocumentDraftCommit } from "./useDocumentDraftCommit";
import { useDocumentDraftOwner } from "./useDocumentDraftOwner";
import { useDocumentDraftState } from "./useDocumentDraftState";
import { useDocumentRevisionHistory } from "./useDocumentRevisionHistory";

/**
 * Composition facade for the Document Draft: per-owner text state, commit
 * and persistence, revision history, conflict actions, and autosave, wired
 * behind the stable return shape consumed by the studio page model.
 */
export function useDocumentDraft(
  activeDocument: StudioDocument | null,
  projectId: string,
  setProject: Dispatch<SetStateAction<Project | null>>,
  setError: Dispatch<SetStateAction<string | null>>,
  setRevisionError: Dispatch<SetStateAction<string | null>> = setError,
  setRestoreError: Dispatch<SetStateAction<string | null>> = setError,
  selectedDocumentId: string | null = activeDocument?.id ?? null,
) {
  const { owner, ownerRef, mountedRef, isCurrentOwner, isCurrentProject } = useDocumentDraftOwner(
    projectId,
    selectedDocumentId,
  );
  const saveTimer = useRef<number | null>(null);
  const saveInFlight = useRef(new Set<string>());
  const conflictActionPendingRef = useRef<typeof owner.token | null>(null);

  const {
    draft,
    titleDraft,
    saveState,
    loadedRevision,
    draftRef,
    saveStateRef,
    setDraftStates,
    setDraft,
    setTitleDraft,
    setCurrentSaveState,
  } = useDocumentDraftState({ activeDocument, owner, isCurrentOwner });

  const {
    revisions,
    historyInitialized,
    hasOlderRevisions,
    isLoadingOlder,
    isLoadingHistory,
    refreshDocumentRevisions,
    loadOlderRevisions,
  } = useDocumentRevisionHistory(
    projectId,
    activeDocument?.id ?? null,
    owner,
    isCurrentOwner,
    setRevisionError,
  );

  const {
    persistedDraftsRef,
    applyDocument,
    reconcileCommittedDocument,
    captureAcceptance,
    persistDraft,
  } = useDocumentDraftCommit({
    projectId,
    owner,
    ownerRef,
    mountedRef,
    isCurrentOwner,
    draftRef,
    saveStateRef,
    loadedRevision,
    setDraftStates,
    refreshDocumentRevisions,
    setProject,
    setError,
    setRestoreError,
  });

  const isCurrentDraftOwner = useCallback(() => isCurrentOwner(owner), [isCurrentOwner, owner]);
  const isCurrentDraftProject = useCallback(
    () => isCurrentProject(owner),
    [isCurrentProject, owner],
  );

  const {
    isConflictActionPending,
    loadLatest,
    refreshLatestDocument,
    restoreRevision,
    retryOverwrite,
  } = useDocumentDraftActions({
    activeDocument,
    projectId,
    owner,
    isCurrentOwner,
    isCurrentProject,
    loadedRevision,
    saveTimerRef: saveTimer,
    saveInFlightRef: saveInFlight,
    conflictActionPendingRef,
    draftRef,
    applyDocument,
    persistDraft,
    reconcileCommittedDocument,
    refreshDocumentRevisions,
    setCurrentSaveState,
    setProject,
    setError,
    setRestoreError,
  });

  const { retrySave, saveNow } = useDocumentDraftAutosave({
    ownerKey: owner.key,
    ownerToken: owner.token,
    isCurrentOwner: isCurrentDraftOwner,
    isCurrentProject: isCurrentDraftProject,
    activeDocument,
    draft,
    titleDraft,
    saveState,
    draftRef,
    persistedDraftsRef,
    loadedRevision,
    saveStateRef,
    conflictActionPendingRef,
    saveTimerRef: saveTimer,
    saveInFlightRef: saveInFlight,
    persistDraft,
    refreshLatestDocument,
    setCurrentSaveState,
    setError,
  });

  // DR-012: the conflict panel's read-only server-version view. It reads
  // through the DR-011 endpoint and never touches the draft or the project.
  const serverVersionPreview = useConflictServerPreview({
    activeDocument,
    projectId,
    owner,
    isCurrentOwner,
    conflictVisible: saveState === "conflict",
  });

  // Browser-close guard for the debounce window and any failed or in-flight
  // save: only unpersisted text raises it, so a settled Document never nags.
  const hasUnpersistedEdits =
    activeDocument !== null &&
    (draft !== activeDocument.content_markdown || titleDraft !== activeDocument.title);
  useEffect(() => {
    if (!hasUnpersistedEdits) return;
    const warnBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warnBeforeUnload);
    return () => window.removeEventListener("beforeunload", warnBeforeUnload);
  }, [hasUnpersistedEdits]);

  return {
    draft,
    setDraft,
    titleDraft,
    setTitleDraft,
    saveState,
    loadedRevision,
    revisions,
    historyInitialized,
    hasOlderRevisions,
    isLoadingOlder,
    isLoadingHistory,
    loadOlderRevisions,
    captureAcceptance,
    restoreRevision,
    isConflictActionPending,
    loadLatest,
    retryOverwrite,
    retrySave,
    saveNow,
    serverVersionPreview,
  };
}
