import type { Dispatch, SetStateAction } from "react";
import { useCallback, useState } from "react";

import { api } from "@/app/api";
import type { Project } from "@/app/types/studio";

import { projectDocumentOwnerKey } from "./projectDocumentOwnerKey";
import { removeProjectDocument } from "./projectState";
import { toErrorMessage } from "./toErrorMessage";
import { usePendingAction } from "./usePendingAction";

const DELETION_KEYS = ["deleteDocument"] as const;

interface DocumentDeletionOwner {
  readonly projectId: string;
}

interface ScopedDeletingDocument {
  readonly projectId: string;
  readonly documentId: string;
}

/** The inline failure a row's confirmation strip renders (#481). */
interface ScopedDeletionFailure {
  readonly key: string;
  readonly message: string;
}

interface UseStudioDocumentDeletionOptions<Owner extends DocumentDeletionOwner> {
  readonly project: Project | null;
  readonly projectId: string;
  readonly setProject: Dispatch<SetStateAction<Project | null>>;
  readonly setActiveId: Dispatch<SetStateAction<string | null>>;
  readonly currentOwner: () => Owner | null;
  readonly isCurrentOwner: (owner: Owner) => boolean;
}

export interface DocumentDeletionLifecycleState {
  readonly isDeleting: boolean;
  readonly error: string | null;
}

/**
 * Navigator document deletion (#481): one irreversible, single-flight
 * document-level command. Success removes exactly its summary row from the
 * shell — no follow-up shell read — and releases an active selection that
 * pointed at the deleted document, letting the route-compatible fallback
 * take over. Refusals (snapshot conflict, transport) stay on the initiating
 * row as its inline error; the confirmation itself owns the discard warning.
 */
export function useStudioDocumentDeletion<Owner extends DocumentDeletionOwner>({
  project,
  projectId,
  setProject,
  setActiveId,
  currentOwner,
  isCurrentOwner,
}: UseStudioDocumentDeletionOptions<Owner>) {
  const { pending, begin, finish } =
    usePendingAction<(typeof DELETION_KEYS)[number]>(DELETION_KEYS);
  const [deletingState, setDeletingState] = useState<ScopedDeletingDocument | null>(null);
  const [failure, setFailure] = useState<ScopedDeletionFailure | null>(null);

  const deleteDocument = useCallback(
    async (documentId: string) => {
      const owner = currentOwner();
      if (!owner || !project || !begin("deleteDocument")) return;
      setDeletingState({ projectId: owner.projectId, documentId });
      setFailure(null);
      try {
        await api.deleteDocument(project.id, documentId);
        if (!isCurrentOwner(owner)) return;
        setProject((current) =>
          isCurrentOwner(owner) && current?.id === owner.projectId
            ? removeProjectDocument(current, documentId)
            : current,
        );
        setActiveId((current) =>
          isCurrentOwner(owner) && current === documentId ? null : current,
        );
      } catch (reason) {
        if (isCurrentOwner(owner)) {
          setFailure({
            key: projectDocumentOwnerKey(owner.projectId, documentId),
            message: toErrorMessage(reason, "Unable to delete the document."),
          });
        }
      } finally {
        // Single-flight: no newer invocation can hold this key, so the
        // scoped busy identity and the pending slot release unconditionally;
        // shell/error publications above stay owner-guarded.
        setDeletingState((current) =>
          current?.projectId === owner.projectId && current.documentId === documentId
            ? null
            : current,
        );
        finish("deleteDocument");
      }
    },
    [begin, currentOwner, finish, isCurrentOwner, project, setActiveId, setProject],
  );

  const deletionFor = useCallback(
    (documentId: string): DocumentDeletionLifecycleState => {
      const isDeleting =
        deletingState !== null &&
        deletingState.projectId === projectId &&
        deletingState.documentId === documentId;
      const error =
        failure?.key === projectDocumentOwnerKey(projectId, documentId) ? failure.message : null;
      return { isDeleting, error };
    },
    [deletingState, failure, projectId],
  );

  return {
    deleteDocument,
    deletionFor,
    deletingDocument:
      deletingState?.projectId === projectId ? { documentId: deletingState.documentId } : null,
    isDeletingDocument: pending.deleteDocument,
  };
}
