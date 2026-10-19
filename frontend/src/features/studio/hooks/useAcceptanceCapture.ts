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
  /** Inactive commits still belong to their original shell; an advanced active baseline wins. */
  readonly isCurrent: (baseRevisionId?: string) => boolean;
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
      const capturedDraft = ownerRef.current === owner && owner.documentId === documentId;
      const expectedRevisionId = capturedDraft ? loadedRevision.current : undefined;
      const isCurrent = (baseRevisionId?: string) => {
        const currentOwner = ownerRef.current;
        const targetIsActive =
          currentOwner?.projectId === owner.projectId && currentOwner.documentId === documentId;
        const baseline = expectedRevisionId ?? baseRevisionId;
        return (
          (!capturedDraft || loadedRevision.current === expectedRevisionId) &&
          (!targetIsActive ||
            draftRef.current.activeDocument === null ||
            baseline === undefined ||
            draftRef.current.activeDocument.current_revision_id === baseline)
        );
      };
      if (!capturedDraft) return { isCurrent };
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
