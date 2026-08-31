import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import { useCallback } from "react";

import type { StudioDocument } from "@/app/types/studio";

import type {
  DocumentDraftOwner,
  DraftSnapshot,
  ReconcileCommittedDocument,
} from "./documentDraftState";
import { captureCommittedDraftReconciler } from "./reconcileCommittedDraft";

/** Captures the active draft version before an external acceptance starts. */
export function useAcceptanceCapture(
  owner: DocumentDraftOwner,
  ownerRef: MutableRefObject<DocumentDraftOwner | null>,
  draftRef: MutableRefObject<DraftSnapshot>,
  reconcile: ReconcileCommittedDocument,
  refreshRevisions: (documentId: string) => Promise<void>,
  setError: Dispatch<SetStateAction<string | null>>,
): (documentId: string) => ((document: StudioDocument) => void) | undefined {
  return useCallback(
    (documentId: string) =>
      ownerRef.current === owner && owner.documentId === documentId
        ? captureCommittedDraftReconciler(draftRef.current, reconcile, (document, outcome) => {
            void refreshRevisions(document.id);
            if (outcome !== "conflict") setError(null);
          })
        : undefined,
    [draftRef, owner, ownerRef, reconcile, refreshRevisions, setError],
  );
}
