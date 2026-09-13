import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import { useCallback, useEffect, useRef } from "react";

import type { Project, SaveState, StudioDocument } from "@/app/types/studio";

import {
  type DocumentDraftOwner,
  type DraftSnapshot,
  type DraftStates,
  type PersistedDraft,
  replaceOwnerBaseline,
} from "./documentDraftState";
import { reconcileCommittedDraft } from "./reconcileCommittedDraft";
import { useAcceptanceCapture } from "./useAcceptanceCapture";
import { usePersistDocumentDraftAndRefreshHistory } from "./useDocumentRevisionHistory";

interface UseDocumentDraftCommitOptions {
  readonly projectId: string;
  readonly owner: DocumentDraftOwner;
  readonly ownerRef: MutableRefObject<DocumentDraftOwner | null>;
  readonly mountedRef: MutableRefObject<boolean>;
  readonly isCurrentOwner: (candidate: DocumentDraftOwner) => boolean;
  readonly draftRef: MutableRefObject<DraftSnapshot>;
  readonly saveStateRef: MutableRefObject<SaveState>;
  readonly loadedRevision: MutableRefObject<string | null>;
  readonly setDraftStates: Dispatch<SetStateAction<DraftStates>>;
  readonly refreshDocumentRevisions: (
    documentId: string,
    expectedRevisionId: string,
  ) => Promise<void>;
  readonly setProject: Dispatch<SetStateAction<Project | null>>;
  readonly setError: Dispatch<SetStateAction<string | null>>;
  readonly setRestoreError: Dispatch<SetStateAction<string | null>>;
}

/**
 * Owns committing Draft edits back to the project: baseline adoption,
 * committed-document reconciliation, acceptance capture, and persistence,
 * including the persisted-draft bookkeeping reset on owner change.
 */
export function useDocumentDraftCommit({
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
}: UseDocumentDraftCommitOptions) {
  const persistedDraftsRef = useRef(new Map<string, PersistedDraft>());

  useEffect(() => {
    if (!isCurrentOwner(owner)) return;
    persistedDraftsRef.current.clear();
    setError(null);
    setRestoreError(null);
  }, [isCurrentOwner, owner, setError, setRestoreError]);

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
    [isCurrentOwner, loadedRevision, owner, saveStateRef, setDraftStates],
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
    [
      draftRef,
      loadedRevision,
      mountedRef,
      owner,
      ownerRef,
      saveStateRef,
      setDraftStates,
      setProject,
    ],
  );

  const captureAcceptance = useAcceptanceCapture(
    owner,
    ownerRef,
    draftRef,
    reconcileCommittedDocument,
    refreshDocumentRevisions,
    setError,
  );

  const persistDraft = usePersistDocumentDraftAndRefreshHistory({
    projectId,
    owner,
    isCurrentOwner,
    reconcileCommittedDocument,
    refreshDocumentRevisions,
    setError,
  });

  return {
    persistedDraftsRef,
    applyDocument,
    reconcileCommittedDocument,
    captureAcceptance,
    persistDraft,
  };
}
