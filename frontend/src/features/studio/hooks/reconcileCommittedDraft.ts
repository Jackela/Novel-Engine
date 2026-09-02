import type { Dispatch, MutableRefObject, SetStateAction } from "react";

import type { Project, SaveState, StudioDocument } from "@/app/types/studio";

import {
  type CommitExpectation,
  type DocumentDraftOwner,
  type DraftSnapshot,
  type DraftStates,
  hasNewerLocalEdit,
  type PersistedDraft,
  type ReconcileCommitOutcome,
  type ReconcileCommittedDocument,
  reconcileOwnerCommit,
  type VisibleDraftState,
} from "./documentDraftState";
import { summarizeDocument } from "./projectState";

interface ReconciliationOptions {
  readonly owner: DocumentDraftOwner;
  readonly mountedRef: MutableRefObject<boolean>;
  readonly ownerRef: MutableRefObject<DocumentDraftOwner | null>;
  readonly draftRef: MutableRefObject<DraftSnapshot>;
  readonly loadedRevision: MutableRefObject<string | null>;
  readonly saveStateRef: MutableRefObject<SaveState>;
  readonly persistedDraftsRef: MutableRefObject<Map<string, PersistedDraft>>;
  readonly setProject: Dispatch<SetStateAction<Project | null>>;
  readonly setDraftStates: Dispatch<SetStateAction<DraftStates>>;
}

/** Reconciles an already-committed document without publishing into another owner. */
export function reconcileCommittedDraft(
  options: ReconciliationOptions,
  document: StudioDocument,
  expectation: CommitExpectation,
): ReconcileCommitOutcome | null {
  const { owner } = options;
  if (
    !options.mountedRef.current ||
    document.project_id !== owner.projectId ||
    document.id !== owner.documentId
  ) {
    return null;
  }
  options.persistedDraftsRef.current.set(owner.key, {
    ownerKey: owner.key,
    draft: document.content_markdown,
    titleDraft: document.title,
  });
  options.setProject((current) =>
    options.mountedRef.current && current?.id === owner.projectId
      ? {
          ...current,
          documents: current.documents.map((candidate) =>
            candidate.id === document.id ? summarizeDocument(document) : candidate,
          ),
        }
      : current,
  );
  const visibleState: VisibleDraftState | undefined =
    options.ownerRef.current?.token === owner.token &&
    options.draftRef.current.ownerToken === owner.token
      ? {
          draft: options.draftRef.current.draft,
          titleDraft: options.draftRef.current.titleDraft,
          editVersion: options.draftRef.current.editVersion,
          loadedRevisionId: options.loadedRevision.current,
        }
      : undefined;
  options.setDraftStates((current) =>
    options.mountedRef.current
      ? reconcileOwnerCommit(current, document, owner.key, expectation, visibleState)
      : current,
  );
  if (options.ownerRef.current?.key !== owner.key) return "inactive-owner";
  const nextSaveState = hasNewerLocalEdit(options.draftRef.current, expectation)
    ? "conflict"
    : expectation.successState;
  options.loadedRevision.current = document.current_revision_id;
  options.saveStateRef.current = nextSaveState;
  return nextSaveState;
}

/** Captures the draft version that an external commit is allowed to replace. */
export function captureCommittedDraftReconciler(
  snapshot: DraftSnapshot,
  reconcile: ReconcileCommittedDocument,
  onReconciled: (document: StudioDocument, outcome: ReconcileCommitOutcome) => void,
): (document: StudioDocument) => void {
  const expectation: CommitExpectation = {
    editVersion: snapshot.editVersion,
    successState: "saved",
    draft: snapshot.draft,
    titleDraft: snapshot.titleDraft,
  };
  return (document) => {
    const outcome = reconcile(document, expectation);
    if (outcome !== null) onReconciled(document, outcome);
  };
}
