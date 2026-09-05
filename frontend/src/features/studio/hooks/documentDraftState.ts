import type { SaveState, StudioDocument } from "@/app/types/studio";

export interface DocumentDraftOwner {
  readonly key: string;
  readonly projectId: string;
  readonly documentId: string | null;
  readonly token: symbol;
}

export interface DraftState {
  readonly ownerKey: DocumentDraftOwner["key"];
  readonly draft: string;
  readonly titleDraft: string;
  readonly saveState: SaveState;
  readonly loadedRevisionId: string | null;
  /** Revisions this owner has already advanced beyond; never inferred from wall-clock order. */
  readonly supersededRevisionIds: ReadonlySet<string>;
  readonly editVersion: number;
}

export type DraftStates = Readonly<Record<DocumentDraftOwner["key"], DraftState>>;

export interface PersistedDraft {
  readonly ownerKey: DocumentDraftOwner["key"];
  readonly draft: string;
  readonly titleDraft: string;
}

export interface DraftSnapshot {
  readonly draft: string;
  readonly titleDraft: string;
  readonly activeDocument: StudioDocument | null;
  readonly editVersion: number;
  readonly ownerToken: DocumentDraftOwner["token"];
}

export interface CommitExpectation {
  readonly editVersion: number;
  readonly successState: SaveState;
  readonly draft?: string;
  readonly titleDraft?: string;
  /** Adopt a newer server baseline while retaining local text as a conflict. */
  readonly preserveLocalDraft?: boolean;
}

export type ReconcileCommitOutcome = SaveState | "inactive-owner";

export type ReconcileCommittedDocument = (
  document: StudioDocument,
  expectation: CommitExpectation,
) => ReconcileCommitOutcome | null;

export type VisibleDraftState = Pick<
  DraftState,
  "draft" | "titleDraft" | "editVersion" | "loadedRevisionId"
>;

export function createDocumentDraftOwner(
  projectId: string,
  documentId: string | null,
): DocumentDraftOwner {
  const key = `${projectId}\u0000${documentId ?? ""}`;
  return { key, projectId, documentId, token: Symbol(key) };
}

export function draftStateFor(
  document: StudioDocument | null,
  ownerKey: DocumentDraftOwner["key"],
  saveState: SaveState = "idle",
): DraftState {
  return {
    ownerKey,
    draft: document?.content_markdown ?? "",
    titleDraft: document?.title ?? "",
    saveState,
    loadedRevisionId: document?.current_revision_id ?? null,
    supersededRevisionIds: new Set<string>(),
    editVersion: 0,
  };
}

export function stateForOwner(
  current: DraftStates,
  document: StudioDocument | null,
  ownerKey: DocumentDraftOwner["key"],
): DraftState {
  return current[ownerKey] ?? draftStateFor(document, ownerKey);
}

export function replaceOwnerState(current: DraftStates, next: DraftState): DraftStates {
  return current[next.ownerKey] === next ? current : { [next.ownerKey]: next };
}

function advanceRevisionLineage(current: DraftState, nextRevisionId: string): ReadonlySet<string> {
  const superseded = new Set(current.supersededRevisionIds);
  if (current.loadedRevisionId && current.loadedRevisionId !== nextRevisionId) {
    superseded.add(current.loadedRevisionId);
  }
  return superseded;
}

export function replaceOwnerBaseline(
  current: DraftStates,
  document: StudioDocument,
  ownerKey: DocumentDraftOwner["key"],
  saveState: SaveState,
): DraftStates {
  const currentState = stateForOwner(current, document, ownerKey);
  return replaceOwnerState(current, {
    ...draftStateFor(document, ownerKey, saveState),
    supersededRevisionIds: advanceRevisionLineage(currentState, document.current_revision_id),
  });
}

export function stateForActiveDocument(
  current: DraftStates,
  document: StudioDocument | null,
  ownerKey: DocumentDraftOwner["key"],
): DraftState {
  const cached = stateForOwner(current, document, ownerKey);
  if (
    document === null ||
    cached.loadedRevisionId === document.current_revision_id ||
    cached.supersededRevisionIds.has(document.current_revision_id)
  ) {
    return cached;
  }
  const matchesIncoming =
    cached.draft === document.content_markdown && cached.titleDraft === document.title;
  if (cached.editVersion > 0 && !matchesIncoming) {
    return {
      ...cached,
      saveState: "conflict",
      loadedRevisionId: document.current_revision_id,
      supersededRevisionIds: advanceRevisionLineage(cached, document.current_revision_id),
    };
  }
  return {
    ...draftStateFor(document, ownerKey),
    supersededRevisionIds: advanceRevisionLineage(cached, document.current_revision_id),
  };
}

export function materializeActiveDraftState(
  current: DraftStates,
  document: StudioDocument | null,
  ownerKey: DocumentDraftOwner["key"],
): DraftStates {
  const next = stateForActiveDocument(current, document, ownerKey);
  return current[ownerKey] === next ? current : replaceOwnerState(current, next);
}

export function hasNewerLocalEdit(
  current: Pick<DraftState, "draft" | "editVersion" | "titleDraft">,
  expectation: CommitExpectation,
): boolean {
  return (
    expectation.preserveLocalDraft === true ||
    current.editVersion > expectation.editVersion ||
    (expectation.draft !== undefined && current.draft !== expectation.draft) ||
    (expectation.titleDraft !== undefined && current.titleDraft !== expectation.titleDraft)
  );
}

export function reconcileOwnerCommit(
  current: DraftStates,
  document: StudioDocument,
  ownerKey: DocumentDraftOwner["key"],
  expectation: CommitExpectation,
  visibleState?: VisibleDraftState,
): DraftStates {
  const storedState = stateForOwner(current, document, ownerKey);
  const currentState = visibleState
    ? {
        ...storedState,
        ...visibleState,
        supersededRevisionIds: visibleState.loadedRevisionId
          ? advanceRevisionLineage(storedState, visibleState.loadedRevisionId)
          : storedState.supersededRevisionIds,
      }
    : storedState;
  const hasNewerEdit = hasNewerLocalEdit(currentState, expectation);
  return replaceOwnerState(current, {
    ...currentState,
    draft: hasNewerEdit ? currentState.draft : document.content_markdown,
    titleDraft: hasNewerEdit ? currentState.titleDraft : document.title,
    saveState: hasNewerEdit ? "conflict" : expectation.successState,
    loadedRevisionId: document.current_revision_id,
    supersededRevisionIds: advanceRevisionLineage(currentState, document.current_revision_id),
    editVersion: hasNewerEdit ? currentState.editVersion : 0,
  });
}
