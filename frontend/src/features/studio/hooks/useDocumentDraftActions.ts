import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import { useCallback, useEffect, useRef, useState } from "react";

import { HttpError } from "@/app/api";
import type { Project, SaveState, StudioDocument } from "@/app/types/studio";

import type {
  DocumentDraftOwner,
  DraftSnapshot,
  ReconcileCommittedDocument,
} from "./documentDraftState";
import { mergeProjectDocument } from "./projectState";
import { toErrorMessage } from "./toErrorMessage";
import { loadLatestDocument, restoreDocumentRevision } from "./useDocumentDraftAutosave";

interface DraftSnapshotRef {
  readonly current: DraftSnapshot;
}

interface UseDocumentDraftActionsArgs {
  readonly activeDocument: StudioDocument | null;
  readonly projectId: string;
  readonly owner: DocumentDraftOwner;
  readonly isCurrentOwner: (candidate: DocumentDraftOwner) => boolean;
  readonly isCurrentProject: (candidate: DocumentDraftOwner) => boolean;
  readonly loadedRevision: MutableRefObject<string | null>;
  readonly saveTimerRef: MutableRefObject<number | null>;
  readonly saveInFlightRef: MutableRefObject<Set<DocumentDraftOwner["key"]>>;
  readonly conflictActionPendingRef: MutableRefObject<DocumentDraftOwner["token"] | null>;
  readonly draftRef: DraftSnapshotRef;
  readonly applyDocument: (
    document: StudioDocument,
    nextSaveState: SaveState,
    rememberPersisted: boolean,
  ) => void;
  readonly persistDraft: (
    document: StudioDocument,
    content: string,
    title: string,
    baseRevisionId: string,
    editVersion: number,
  ) => Promise<StudioDocument | null>;
  readonly reconcileCommittedDocument: ReconcileCommittedDocument;
  readonly refreshDocumentRevisions: (
    documentId: string,
    expectedRevisionId: string,
  ) => Promise<void>;
  readonly setCurrentSaveState: (nextSaveState: SaveState) => void;
  readonly setProject: Dispatch<SetStateAction<Project | null>>;
  readonly setError: Dispatch<SetStateAction<string | null>>;
  readonly setRestoreError: Dispatch<SetStateAction<string | null>>;
}

interface ConflictActionState {
  readonly ownerToken: DocumentDraftOwner["token"];
  readonly pending: boolean;
}

function abortOwnerRequests(
  requests: Map<DocumentDraftOwner["token"], Set<AbortController>>,
  ownerToken: DocumentDraftOwner["token"],
): void {
  const controllers = requests.get(ownerToken);
  if (!controllers) return;
  for (const controller of controllers) controller.abort();
  requests.delete(ownerToken);
}

function abortAllRequests(requests: Map<DocumentDraftOwner["token"], Set<AbortController>>): void {
  for (const ownerToken of requests.keys()) abortOwnerRequests(requests, ownerToken);
}

/**
 * Owns the explicit conflict and restore commands for one project/document
 * identity. It is the only layer that starts abortable aggregate refreshes;
 * callers supply guarded state publications and draft persistence.
 */
export function useDocumentDraftActions({
  activeDocument,
  projectId,
  owner,
  isCurrentOwner,
  isCurrentProject,
  loadedRevision,
  saveTimerRef,
  saveInFlightRef,
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
}: UseDocumentDraftActionsArgs) {
  const requestControllersRef = useRef(
    new Map<DocumentDraftOwner["token"], Set<AbortController>>(),
  );
  const [conflictActionState, setConflictActionState] = useState<ConflictActionState>({
    ownerToken: owner.token,
    pending: false,
  });
  const isConflictActionPending =
    conflictActionState.ownerToken === owner.token && conflictActionState.pending;

  useEffect(
    () => () => {
      abortOwnerRequests(requestControllersRef.current, owner.token);
    },
    [owner.token],
  );
  useEffect(() => () => abortAllRequests(requestControllersRef.current), []);

  const refreshLatestDocument = useCallback(
    async (documentId: string): Promise<StudioDocument | null> => {
      if (!isCurrentProject(owner) || documentId !== owner.documentId) return null;
      const controller = new AbortController();
      const ownerControllers =
        requestControllersRef.current.get(owner.token) ?? new Set<AbortController>();
      ownerControllers.add(controller);
      requestControllersRef.current.set(owner.token, ownerControllers);
      try {
        const document = await loadLatestDocument(projectId, documentId, controller.signal);
        if (!isCurrentProject(owner) || controller.signal.aborted) return null;
        if (isCurrentOwner(owner)) loadedRevision.current = document.current_revision_id;
        setProject((current) =>
          isCurrentProject(owner) && current?.id === owner.projectId
            ? mergeProjectDocument(current, document)
            : current,
        );
        return document;
      } finally {
        ownerControllers.delete(controller);
        if (ownerControllers.size === 0) requestControllersRef.current.delete(owner.token);
      }
    },
    [isCurrentOwner, isCurrentProject, loadedRevision, owner, projectId, setProject],
  );

  const finishConflictAction = useCallback(() => {
    if (!isCurrentOwner(owner)) return;
    setConflictActionState({ ownerToken: owner.token, pending: false });
    if (conflictActionPendingRef.current === owner.token) {
      conflictActionPendingRef.current = null;
    }
  }, [conflictActionPendingRef, isCurrentOwner, owner]);

  const loadLatest = useCallback(async () => {
    if (
      !activeDocument ||
      !isCurrentOwner(owner) ||
      conflictActionPendingRef.current === owner.token ||
      saveInFlightRef.current.has(owner.key)
    ) {
      return;
    }
    if (saveTimerRef.current) window.clearTimeout(saveTimerRef.current);
    setConflictActionState({ ownerToken: owner.token, pending: true });
    conflictActionPendingRef.current = owner.token;
    try {
      const latestDocument = await refreshLatestDocument(activeDocument.id);
      if (!latestDocument || !isCurrentOwner(owner)) return;
      applyDocument(latestDocument, "idle", true);
      void refreshDocumentRevisions(latestDocument.id, latestDocument.current_revision_id);
      setError(null);
    } catch (reason) {
      if (isCurrentOwner(owner)) {
        setCurrentSaveState("error");
        setError(toErrorMessage(reason, "Unable to load the latest document."));
      }
    } finally {
      finishConflictAction();
    }
  }, [
    activeDocument,
    applyDocument,
    conflictActionPendingRef,
    finishConflictAction,
    isCurrentOwner,
    owner,
    refreshDocumentRevisions,
    refreshLatestDocument,
    saveInFlightRef,
    saveTimerRef,
    setCurrentSaveState,
    setError,
  ]);

  const retryOverwrite = useCallback(async () => {
    if (
      !activeDocument ||
      !isCurrentOwner(owner) ||
      conflictActionPendingRef.current === owner.token ||
      saveInFlightRef.current.has(owner.key)
    ) {
      return;
    }
    if (saveTimerRef.current) window.clearTimeout(saveTimerRef.current);
    setConflictActionState({ ownerToken: owner.token, pending: true });
    conflictActionPendingRef.current = owner.token;
    saveInFlightRef.current.add(owner.key);
    const { draft, editVersion, titleDraft } = draftRef.current;
    try {
      const latestDocument = await refreshLatestDocument(activeDocument.id);
      if (!latestDocument || !isCurrentOwner(owner)) return;
      setCurrentSaveState("saving");
      await persistDraft(
        latestDocument,
        draft,
        titleDraft,
        latestDocument.current_revision_id,
        editVersion,
      );
    } catch (reason) {
      if (isCurrentOwner(owner)) {
        setCurrentSaveState(
          reason instanceof HttpError && reason.status === 409 ? "conflict" : "error",
        );
        setError(toErrorMessage(reason, "Unable to overwrite the latest document."));
      }
    } finally {
      saveInFlightRef.current.delete(owner.key);
      finishConflictAction();
    }
  }, [
    activeDocument,
    conflictActionPendingRef,
    draftRef,
    finishConflictAction,
    isCurrentOwner,
    owner,
    persistDraft,
    refreshLatestDocument,
    saveInFlightRef,
    saveTimerRef,
    setCurrentSaveState,
    setError,
  ]);

  const restoreRevision = useCallback(
    async (revisionId: string) => {
      if (!activeDocument || !isCurrentOwner(owner)) return;
      const restoreEditVersion = draftRef.current.editVersion;
      setRestoreError(null);
      try {
        const restored = await restoreDocumentRevision(
          projectId,
          activeDocument,
          revisionId,
          loadedRevision.current ?? activeDocument.current_revision_id,
        );
        const outcome = reconcileCommittedDocument(restored, {
          editVersion: restoreEditVersion,
          successState: "idle",
        });
        if (outcome !== null) {
          await refreshDocumentRevisions(activeDocument.id, restored.current_revision_id);
          if (outcome !== "conflict") setRestoreError(null);
        }
      } catch (reason) {
        if (reason instanceof HttpError && reason.status === 409) {
          if (isCurrentOwner(owner)) setCurrentSaveState("conflict");
          try {
            const latestDocument = await refreshLatestDocument(activeDocument.id);
            if (!latestDocument) return;
            reconcileCommittedDocument(latestDocument, {
              editVersion: restoreEditVersion,
              successState: "conflict",
              preserveLocalDraft: true,
            });
            if (isCurrentProject(owner)) {
              setRestoreError(
                "The document changed before the revision could be restored. The latest revision is ready; resolve the local draft or try restoring again.",
              );
            }
          } catch (refreshReason) {
            if (isCurrentProject(owner)) {
              setRestoreError(
                toErrorMessage(refreshReason, "Unable to refresh the latest document."),
              );
            }
          }
          return;
        }
        if (isCurrentProject(owner)) {
          setRestoreError(toErrorMessage(reason, "Unable to restore revision."));
        }
      }
    },
    [
      activeDocument,
      draftRef,
      isCurrentOwner,
      isCurrentProject,
      loadedRevision,
      owner,
      projectId,
      reconcileCommittedDocument,
      refreshDocumentRevisions,
      refreshLatestDocument,
      setCurrentSaveState,
      setRestoreError,
    ],
  );

  return {
    isConflictActionPending,
    loadLatest,
    refreshLatestDocument,
    restoreRevision,
    retryOverwrite,
  };
}
