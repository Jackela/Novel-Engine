import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import { useCallback } from "react";

import { HttpError } from "@/app/api";
import type { Project, SaveState, StudioDocument } from "@/app/types/studio";

import type {
  DocumentDraftOwner,
  DraftSnapshot,
  ReconcileCommittedDocument,
} from "./documentDraftState";
import { toErrorMessage } from "./toErrorMessage";
import { useAbortableDocumentRefresh } from "./useAbortableDocumentRefresh";
import { useConflictActionGate } from "./useConflictActionGate";
import { restoreDocumentRevision } from "./useDocumentDraftAutosave";

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

/**
 * Owns the explicit conflict and restore commands for one project/document
 * identity. The abortable refresh registry and the conflict-action pending
 * gate live in dedicated state hooks; this facade composes them into the
 * guarded command surface.
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
  const { refreshLatestDocument } = useAbortableDocumentRefresh({
    owner,
    projectId,
    isCurrentOwner,
    isCurrentProject,
    loadedRevision,
    setProject,
  });
  const { beginConflictAction, finishConflictAction, isConflictActionPending } =
    useConflictActionGate({ owner, isCurrentOwner, conflictActionPendingRef });

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
    beginConflictAction();
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
    beginConflictAction,
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
    beginConflictAction();
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
    beginConflictAction,
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
          if (outcome !== "conflict" && isCurrentOwner(owner)) setRestoreError(null);
        }
      } catch (reason) {
        if (reason instanceof HttpError && reason.status === 409) {
          if (isCurrentOwner(owner)) setCurrentSaveState("conflict");
          try {
            const latestDocument = await refreshLatestDocument(activeDocument.id);
            if (!latestDocument) return;
            if (isCurrentOwner(owner)) {
              reconcileCommittedDocument(latestDocument, {
                editVersion: restoreEditVersion,
                successState: "conflict",
                preserveLocalDraft: true,
              });
              setRestoreError(
                "The document changed before the revision could be restored. The latest revision is ready; resolve the local draft or try restoring again.",
              );
            }
          } catch (refreshReason) {
            if (isCurrentOwner(owner)) {
              setRestoreError(
                toErrorMessage(refreshReason, "Unable to refresh the latest document."),
              );
            }
          }
          return;
        }
        if (isCurrentOwner(owner)) {
          setRestoreError(toErrorMessage(reason, "Unable to restore revision."));
        }
      }
    },
    [
      activeDocument,
      draftRef,
      isCurrentOwner,
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
