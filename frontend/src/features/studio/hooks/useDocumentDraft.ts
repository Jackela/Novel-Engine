import type { Dispatch, SetStateAction } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { Project, SaveState, StudioDocument } from "@/app/types/studio";
import {
  type DraftStates,
  draftStateFor,
  materializeActiveDraftState,
  type PersistedDraft,
  replaceOwnerBaseline,
  replaceOwnerState,
  stateForActiveDocument,
  stateForOwner,
} from "./documentDraftState";
import { reconcileCommittedDraft } from "./reconcileCommittedDraft";
import { toErrorMessage } from "./toErrorMessage";
import { useAcceptanceCapture } from "./useAcceptanceCapture";
import { useDocumentDraftActions } from "./useDocumentDraftActions";
import { saveDocumentDraft, useDocumentDraftAutosave } from "./useDocumentDraftAutosave";
import { useDocumentDraftOwner } from "./useDocumentDraftOwner";
import { useRevisionCache } from "./useRevisionCache";

export function useDocumentDraft(
  activeDocument: StudioDocument | null,
  projectId: string,
  setProject: Dispatch<SetStateAction<Project | null>>,
  setError: Dispatch<SetStateAction<string | null>>,
  setRevisionError: Dispatch<SetStateAction<string | null>> = setError,
  setRestoreError: Dispatch<SetStateAction<string | null>> = setError,
) {
  const { owner, ownerRef, mountedRef, isCurrentOwner, isCurrentProject } = useDocumentDraftOwner(
    projectId,
    activeDocument?.id ?? null,
  );
  const [draftStates, setDraftStates] = useState<DraftStates>(() => ({
    [owner.key]: draftStateFor(activeDocument, owner.key),
  }));
  const saveTimer = useRef<number | null>(null);
  const saveInFlight = useRef(new Set<string>());
  const persistedDraftsRef = useRef(new Map<string, PersistedDraft>());
  const activeDraftState = stateForActiveDocument(draftStates, activeDocument, owner.key);
  const { draft, titleDraft, saveState } = activeDraftState;

  // Persist a clean aggregate advance into the owner cache. The render-time
  // projection makes the new baseline visible immediately; materializing it
  // here ensures a later commit can still reconcile against that baseline
  // after the author has switched to another document.
  useEffect(() => {
    setDraftStates((current) => materializeActiveDraftState(current, activeDocument, owner.key));
  }, [activeDocument, owner.key]);

  const loadedRevision = useMemo(
    () => ({ current: activeDraftState.loadedRevisionId, ownerToken: owner.token }),
    [activeDraftState.loadedRevisionId, owner.token],
  );
  const draftRef = useRef({
    draft,
    titleDraft,
    activeDocument,
    editVersion: activeDraftState.editVersion,
    ownerToken: owner.token,
  });
  const saveStateRef = useRef(saveState);
  const conflictActionPendingRef = useRef<typeof owner.token | null>(null);

  useEffect(() => {
    draftRef.current = {
      draft,
      titleDraft,
      activeDocument,
      editVersion: activeDraftState.editVersion,
      ownerToken: owner.token,
    };
  }, [activeDocument, activeDraftState.editVersion, draft, owner.token, titleDraft]);

  useEffect(() => {
    saveStateRef.current = saveState;
  }, [saveState]);

  const reportRevisionError = useCallback(
    (reason: unknown) => {
      if (isCurrentOwner(owner)) {
        setRevisionError(toErrorMessage(reason, "Unable to load revisions."));
      }
    },
    [isCurrentOwner, owner, setRevisionError],
  );
  const clearRevisionError = useCallback(() => {
    if (isCurrentOwner(owner)) setRevisionError(null);
  }, [isCurrentOwner, owner, setRevisionError]);
  const {
    revisions,
    historyInitialized,
    hasOlderRevisions,
    isLoadingOlder,
    refreshDocumentRevisions,
    loadOlderRevisions,
  } = useRevisionCache(
    projectId,
    activeDocument?.id ?? null,
    reportRevisionError,
    clearRevisionError,
  );

  const setDraft = useCallback<Dispatch<SetStateAction<string>>>(
    (nextDraft) => {
      if (!isCurrentOwner(owner)) return;
      setDraftStates((current) => {
        if (!isCurrentOwner(owner)) return current;
        const currentState = stateForActiveDocument(
          current,
          draftRef.current.activeDocument,
          owner.key,
        );
        const draft = typeof nextDraft === "function" ? nextDraft(currentState.draft) : nextDraft;
        if (draft === currentState.draft) return current;
        return replaceOwnerState(current, {
          ...currentState,
          draft,
          editVersion: currentState.editVersion + 1,
          saveState: currentState.saveState === "conflict" ? "conflict" : "saving",
        });
      });
    },
    [isCurrentOwner, owner],
  );

  const setTitleDraft = useCallback<Dispatch<SetStateAction<string>>>(
    (nextTitle) => {
      if (!isCurrentOwner(owner)) return;
      setDraftStates((current) => {
        if (!isCurrentOwner(owner)) return current;
        const currentState = stateForActiveDocument(
          current,
          draftRef.current.activeDocument,
          owner.key,
        );
        const titleDraft =
          typeof nextTitle === "function" ? nextTitle(currentState.titleDraft) : nextTitle;
        if (titleDraft === currentState.titleDraft) return current;
        return replaceOwnerState(current, {
          ...currentState,
          titleDraft,
          editVersion: currentState.editVersion + 1,
          saveState: currentState.saveState === "conflict" ? "conflict" : "saving",
        });
      });
    },
    [isCurrentOwner, owner],
  );

  const setCurrentSaveState = useCallback(
    (nextSaveState: SaveState) => {
      if (!isCurrentProject(owner)) return;
      if (ownerRef.current?.key === owner.key) saveStateRef.current = nextSaveState;
      setDraftStates((current) =>
        isCurrentProject(owner)
          ? replaceOwnerState(current, {
              ...stateForOwner(current, activeDocument, owner.key),
              saveState: nextSaveState,
            })
          : current,
      );
    },
    [activeDocument, isCurrentProject, owner, ownerRef],
  );

  const applyDocument = useCallback(
    (document: StudioDocument, nextSaveState: SaveState, rememberPersisted: boolean) => {
      if (
        !isCurrentOwner(owner) ||
        document.project_id !== owner.projectId ||
        document.id !== owner.documentId
      ) {
        return;
      }
      loadedRevision.current = document.current_revision_id;
      saveStateRef.current = nextSaveState;
      if (rememberPersisted) {
        persistedDraftsRef.current.set(owner.key, {
          ownerKey: owner.key,
          draft: document.content_markdown,
          titleDraft: document.title,
        });
      }
      setDraftStates((current) =>
        replaceOwnerBaseline(current, document, owner.key, nextSaveState),
      );
    },
    [isCurrentOwner, loadedRevision, owner],
  );

  const reconcileCommittedDocument = useCallback(
    (document: StudioDocument, expectation: Parameters<typeof reconcileCommittedDraft>[2]) =>
      reconcileCommittedDraft(
        {
          owner,
          mountedRef,
          ownerRef,
          draftRef,
          loadedRevision,
          saveStateRef,
          persistedDraftsRef,
          setProject,
          setDraftStates,
        },
        document,
        expectation,
      ),
    [loadedRevision, mountedRef, owner, ownerRef, setProject],
  );

  const captureAcceptance = useAcceptanceCapture(
    owner,
    ownerRef,
    draftRef,
    reconcileCommittedDocument,
    refreshDocumentRevisions,
    setError,
  );

  const persistDraft = useCallback(
    async (
      document: StudioDocument,
      content: string,
      title: string,
      baseRevisionId: string,
      editVersion: number,
    ): Promise<StudioDocument | null> => {
      if (
        !isCurrentOwner(owner) ||
        document.project_id !== owner.projectId ||
        document.id !== owner.documentId
      ) {
        return null;
      }
      const saved = await saveDocumentDraft(projectId, document, content, title, baseRevisionId);
      const outcome = reconcileCommittedDocument(saved, {
        editVersion,
        successState: "saved",
        draft: content,
        titleDraft: title,
      });
      if (outcome !== null) {
        void refreshDocumentRevisions(document.id);
        if (outcome !== "conflict") setError(null);
      }
      return saved;
    },
    [
      isCurrentOwner,
      owner,
      projectId,
      reconcileCommittedDocument,
      refreshDocumentRevisions,
      setError,
    ],
  );

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

  useDocumentDraftAutosave({
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
    loadOlderRevisions,
    captureAcceptance,
    restoreRevision,
    isConflictActionPending,
    loadLatest,
    retryOverwrite,
  };
}
