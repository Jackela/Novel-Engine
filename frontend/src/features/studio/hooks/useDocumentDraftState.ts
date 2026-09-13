import type { Dispatch, SetStateAction } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { SaveState, StudioDocument } from "@/app/types/studio";

import {
  type DocumentDraftOwner,
  type DraftStates,
  draftStateFor,
  materializeActiveDraftState,
  replaceOwnerState,
  stateForActiveDocument,
  stateForOwner,
} from "./documentDraftState";

interface UseDocumentDraftStateOptions {
  readonly activeDocument: StudioDocument | null;
  readonly owner: DocumentDraftOwner;
  readonly isCurrentOwner: (candidate: DocumentDraftOwner) => boolean;
}

/**
 * Owns the per-owner Draft text state: visible draft, title, save state, the
 * refs mirroring them for async readers, and the guarded text mutators.
 */
export function useDocumentDraftState({
  activeDocument,
  owner,
  isCurrentOwner,
}: UseDocumentDraftStateOptions) {
  const [draftStates, setDraftStates] = useState<DraftStates>(() => ({
    [owner.key]: draftStateFor(activeDocument, owner.key),
  }));
  const activeDraftState = stateForActiveDocument(draftStates, activeDocument, owner.key);
  const { draft, titleDraft, saveState } = activeDraftState;

  // Only the selected Document owns a Draft. A temporary body-loading state
  // preserves this owner; selecting another Document replaces its local state.
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
      if (!isCurrentOwner(owner)) return;
      saveStateRef.current = nextSaveState;
      setDraftStates((current) =>
        isCurrentOwner(owner)
          ? replaceOwnerState(current, {
              ...stateForOwner(current, activeDocument, owner.key),
              saveState: nextSaveState,
            })
          : current,
      );
    },
    [activeDocument, isCurrentOwner, owner],
  );

  return {
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
  };
}
