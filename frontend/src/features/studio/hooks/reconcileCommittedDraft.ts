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
  const activeOwner = options.ownerRef.current;
  // An inactive commit updates the shell; its body is read afresh on return.
  // Never recreate a Draft or retain an inactive body for that Document.
  if (activeOwner?.key !== owner.key) return "inactive-owner";
  options.persistedDraftsRef.current.set(owner.key, {
    ownerKey: owner.key,
    draft: document.content_markdown,
    titleDraft: document.title,
  });
  const sameLifecycle = activeOwner.token === owner.token;
  const visibleState: VisibleDraftState | undefined =
    sameLifecycle && options.draftRef.current.ownerToken === activeOwner.token
      ? {
          draft: options.draftRef.current.draft,
          titleDraft: options.draftRef.current.titleDraft,
          editVersion: options.draftRef.current.editVersion,
          loadedRevisionId: options.loadedRevision.current,
        }
      : undefined;
  // A -> B -> A starts a new edit counter. Compare against that lifecycle's
  // clean baseline, never the discarded edit version or text from old A.
  const activeExpectation = sameLifecycle
    ? expectation
    : { editVersion: 0, successState: expectation.successState };
  options.setDraftStates((current) =>
    options.mountedRef.current && options.ownerRef.current === activeOwner
      ? reconcileOwnerCommit(current, document, owner.key, activeExpectation, visibleState)
      : current,
  );
  const nextSaveState = hasNewerLocalEdit(options.draftRef.current, activeExpectation)
    ? "conflict"
    : expectation.successState;
  if (sameLifecycle) options.loadedRevision.current = document.current_revision_id;
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
