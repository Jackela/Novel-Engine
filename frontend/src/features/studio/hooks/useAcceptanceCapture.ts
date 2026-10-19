import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import { useCallback } from "react";

import type { StudioDocument } from "@/app/types/studio";

import type {
  DocumentDraftOwner,
  DraftSnapshot,
  ReconcileCommittedDocument,
} from "./documentDraftState";
import { captureCommittedDraftReconciler } from "./reconcileCommittedDraft";

export interface AcceptedDocumentCapture {
  readonly reconcile?: (document: StudioDocument) => void;
  /** Publication is valid only while the captured accepted baseline still owns the read. */
  readonly isCurrent: () => boolean;
}

export type CaptureAcceptedDocument = (documentId: string) => AcceptedDocumentCapture | undefined;

/** Captures the active draft and accepted baseline before an external acceptance starts. */
export function useAcceptanceCapture(
  owner: DocumentDraftOwner,
  ownerRef: MutableRefObject<DocumentDraftOwner | null>,
  draftRef: MutableRefObject<DraftSnapshot>,
  loadedRevision: MutableRefObject<string | null>,
  reconcile: ReconcileCommittedDocument,
  refreshRevisions: (documentId: string, expectedRevisionId: string) => Promise<void>,
  setError: Dispatch<SetStateAction<string | null>>,
): CaptureAcceptedDocument {
  return useCallback(
    (documentId: string) => {
      if (ownerRef.current !== owner || owner.documentId !== documentId) return undefined;
      const expectedRevisionId = loadedRevision.current;
      const isCurrent = () =>
        loadedRevision.current === expectedRevisionId &&
        (ownerRef.current?.key !== owner.key ||
          draftRef.current.activeDocument === null ||
          draftRef.current.activeDocument.current_revision_id === expectedRevisionId);
      const reconcileAcceptance = captureCommittedDraftReconciler(
        draftRef.current,
        reconcile,
        (document, outcome) => {
          void refreshRevisions(document.id, document.current_revision_id);
          if (outcome !== "conflict" && ownerRef.current === owner) setError(null);
        },
        expectedRevisionId ?? null,
      );
      return {
        isCurrent,
        reconcile: (document: StudioDocument) => {
          if (isCurrent()) reconcileAcceptance(document);
        },
      };
    },
    [draftRef, loadedRevision, owner, ownerRef, reconcile, refreshRevisions, setError],
  );
}
