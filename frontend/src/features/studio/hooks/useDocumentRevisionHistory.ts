import type { Dispatch, SetStateAction } from "react";
import { useCallback } from "react";

import type { StudioDocument } from "@/app/types/studio";

import type { DocumentDraftOwner, ReconcileCommittedDocument } from "./documentDraftState";
import { toErrorMessage } from "./toErrorMessage";
import { saveDocumentDraft } from "./useDocumentDraftAutosave";
import { useRevisionCache } from "./useRevisionCache";

interface PersistDocumentDraftAndRefreshHistoryContext {
  readonly projectId: string;
  readonly owner: DocumentDraftOwner;
  readonly isCurrentOwner: (candidate: DocumentDraftOwner) => boolean;
  readonly reconcileCommittedDocument: ReconcileCommittedDocument;
  readonly refreshDocumentRevisions: (
    documentId: string,
    expectedRevisionId: string,
  ) => Promise<void>;
  readonly setError: Dispatch<SetStateAction<string | null>>;
}

interface PersistDocumentDraftAndRefreshHistoryArgs
  extends PersistDocumentDraftAndRefreshHistoryContext {
  readonly document: StudioDocument;
  readonly content: string;
  readonly title: string;
  readonly baseRevisionId: string;
  readonly editVersion: number;
}

async function persistDocumentDraftAndRefreshHistory({
  projectId,
  owner,
  isCurrentOwner,
  reconcileCommittedDocument,
  refreshDocumentRevisions,
  setError,
  document,
  content,
  title,
  baseRevisionId,
  editVersion,
}: PersistDocumentDraftAndRefreshHistoryArgs): Promise<StudioDocument | null> {
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
    void refreshDocumentRevisions(document.id, saved.current_revision_id);
    if (outcome !== "conflict") setError(null);
  }
  return saved;
}

export function usePersistDocumentDraftAndRefreshHistory({
  projectId,
  owner,
  isCurrentOwner,
  reconcileCommittedDocument,
  refreshDocumentRevisions,
  setError,
}: PersistDocumentDraftAndRefreshHistoryContext) {
  return useCallback(
    (
      document: StudioDocument,
      content: string,
      title: string,
      baseRevisionId: string,
      editVersion: number,
    ) =>
      persistDocumentDraftAndRefreshHistory({
        projectId,
        owner,
        isCurrentOwner,
        reconcileCommittedDocument,
        refreshDocumentRevisions,
        setError,
        document,
        content,
        title,
        baseRevisionId,
        editVersion,
      }),
    [
      isCurrentOwner,
      owner,
      projectId,
      reconcileCommittedDocument,
      refreshDocumentRevisions,
      setError,
    ],
  );
}

export function useDocumentRevisionHistory(
  projectId: string,
  documentId: string | null,
  owner: DocumentDraftOwner,
  isCurrentOwner: (candidate: DocumentDraftOwner) => boolean,
  setRevisionError: Dispatch<SetStateAction<string | null>>,
) {
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

  return useRevisionCache(projectId, documentId, reportRevisionError, clearRevisionError);
}
