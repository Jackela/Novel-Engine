import { type Dispatch, type MutableRefObject, type SetStateAction, useEffect } from "react";

import { api, HttpError } from "@/app/api";
import type { SaveState, StudioDocument } from "@/app/types/studio";

import type { DraftSnapshot, PersistedDraft } from "./documentDraftState";
import { toErrorMessage } from "./toErrorMessage";

interface AutosaveOptions {
  readonly ownerKey: string;
  readonly ownerToken: symbol;
  readonly isCurrentOwner: () => boolean;
  readonly isCurrentProject: () => boolean;
  readonly activeDocument: StudioDocument | null;
  readonly draft: string;
  readonly titleDraft: string;
  readonly saveState: SaveState;
  readonly draftRef: MutableRefObject<DraftSnapshot>;
  readonly persistedDraftsRef: MutableRefObject<Map<string, PersistedDraft>>;
  readonly loadedRevision: MutableRefObject<string | null>;
  readonly saveStateRef: MutableRefObject<SaveState>;
  readonly conflictActionPendingRef: MutableRefObject<symbol | null>;
  readonly saveTimerRef: MutableRefObject<number | null>;
  readonly saveInFlightRef: MutableRefObject<Set<string>>;
  readonly persistDraft: (
    document: StudioDocument,
    content: string,
    title: string,
    baseRevisionId: string,
    editVersion: number,
  ) => Promise<StudioDocument | null>;
  readonly refreshLatestDocument: (documentId: string) => Promise<StudioDocument | null>;
  readonly setCurrentSaveState: (nextSaveState: SaveState) => void;
  readonly setError: Dispatch<SetStateAction<string | null>>;
}

export function useDocumentDraftAutosave({
  ownerKey,
  ownerToken,
  isCurrentOwner,
  isCurrentProject,
  activeDocument,
  draft,
  titleDraft,
  saveState,
  draftRef,
  persistedDraftsRef,
  loadedRevision,
  saveStateRef,
  conflictActionPendingRef,
  saveTimerRef,
  saveInFlightRef,
  persistDraft,
  refreshLatestDocument,
  setCurrentSaveState,
  setError,
}: AutosaveOptions): void {
  useEffect(() => {
    if (!activeDocument) return;
    const persisted = persistedDraftsRef.current.get(ownerKey);
    if (
      persisted?.ownerKey === ownerKey &&
      persisted.draft === draft &&
      persisted.titleDraft === titleDraft
    ) {
      if (saveState === "saving") setCurrentSaveState("saved");
      return;
    }
    const unchanged =
      draft === activeDocument.content_markdown && titleDraft === activeDocument.title;
    if (unchanged) {
      setCurrentSaveState("idle");
      return;
    }
    if (
      saveStateRef.current === "conflict" ||
      saveStateRef.current === "error" ||
      conflictActionPendingRef.current === ownerToken
    ) {
      return;
    }
    setCurrentSaveState("saving");
    if (saveTimerRef.current) window.clearTimeout(saveTimerRef.current);
    saveTimerRef.current = window.setTimeout(async () => {
      const {
        draft: currentDraft,
        titleDraft: currentTitle,
        activeDocument: currentDocument,
        editVersion,
      } = draftRef.current;
      if (!currentDocument || draftRef.current.ownerToken !== ownerToken || !isCurrentOwner()) {
        return;
      }
      if (saveInFlightRef.current.has(ownerKey)) return;
      saveInFlightRef.current.add(ownerKey);
      try {
        await persistDraft(
          currentDocument,
          currentDraft,
          currentTitle,
          loadedRevision.current ?? currentDocument.current_revision_id,
          editVersion,
        );
      } catch (reason) {
        if (!isCurrentProject()) return;
        const isConflict = reason instanceof HttpError && reason.status === 409;
        setCurrentSaveState(isConflict ? "conflict" : "error");
        setError(toErrorMessage(reason, "Unable to save."));
        if (isConflict) {
          try {
            await refreshLatestDocument(currentDocument.id);
          } catch (refreshReason) {
            if (isCurrentProject()) {
              setError(toErrorMessage(refreshReason, "Unable to refresh the latest document."));
            }
          }
        }
      } finally {
        saveInFlightRef.current.delete(ownerKey);
      }
    }, 1500);
    return () => {
      if (saveTimerRef.current) window.clearTimeout(saveTimerRef.current);
    };
  }, [
    activeDocument,
    ownerKey,
    ownerToken,
    isCurrentOwner,
    isCurrentProject,
    draft,
    titleDraft,
    saveState,
    persistDraft,
    refreshLatestDocument,
    setCurrentSaveState,
    setError,
    draftRef,
    persistedDraftsRef,
    loadedRevision,
    saveStateRef,
    conflictActionPendingRef,
    saveTimerRef,
    saveInFlightRef,
  ]);
}

export function restoreDocumentRevision(
  projectId: string,
  document: StudioDocument,
  revisionId: string,
  baseRevisionId: string,
): Promise<StudioDocument> {
  return api.restoreRevision(projectId, document.id, revisionId, baseRevisionId);
}

export async function loadLatestDocument(
  projectId: string,
  documentId: string,
  signal?: AbortSignal,
): Promise<StudioDocument> {
  return api.document(projectId, documentId, { signal });
}

export function saveDocumentDraft(
  projectId: string,
  document: StudioDocument,
  content: string,
  title: string,
  baseRevisionId: string,
): Promise<StudioDocument> {
  return api.saveDocument(projectId, document.id, {
    content_markdown: content,
    base_revision_id: baseRevisionId,
    title,
  });
}
