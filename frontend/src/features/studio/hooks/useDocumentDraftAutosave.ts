import { useEffect, type Dispatch, type MutableRefObject, type SetStateAction } from 'react';

import { HttpError, api } from '@/app/api';
import type { Project, SaveState, StudioDocument } from '@/app/types/studio';

interface DraftRefValue {
  readonly draft: string;
  readonly titleDraft: string;
  readonly activeDocument: StudioDocument | null;
}

interface PersistedDraft {
  readonly documentId: string;
  readonly draft: string;
  readonly titleDraft: string;
}

interface AutosaveOptions {
  readonly activeDocument: StudioDocument | null;
  readonly draft: string;
  readonly titleDraft: string;
  readonly saveState: SaveState;
  readonly draftRef: MutableRefObject<DraftRefValue>;
  readonly lastPersistedDraft: MutableRefObject<PersistedDraft | null>;
  readonly loadedRevision: MutableRefObject<string | null>;
  readonly saveStateRef: MutableRefObject<SaveState>;
  readonly conflictActionPendingRef: MutableRefObject<boolean>;
  readonly saveTimerRef: MutableRefObject<number | null>;
  readonly saveInFlightRef: MutableRefObject<boolean>;
  readonly persistDraft: (
    document: StudioDocument,
    content: string,
    title: string,
    baseRevisionId: string,
  ) => Promise<StudioDocument>;
  readonly refreshLatestDocument: (documentId: string) => Promise<StudioDocument>;
  readonly setCurrentSaveState: (nextSaveState: SaveState) => void;
  readonly setError: Dispatch<SetStateAction<string | null>>;
}

function errorMessage(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback;
}

export function useDocumentDraftAutosave({
  activeDocument,
  draft,
  titleDraft,
  saveState,
  draftRef,
  lastPersistedDraft,
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
    const persisted = lastPersistedDraft.current;
    if (
      persisted?.documentId === activeDocument.id &&
      persisted.draft === draft &&
      persisted.titleDraft === titleDraft
    ) {
      if (saveState === 'saving') setCurrentSaveState('saved');
      return;
    }
    const unchanged =
      draft === activeDocument.content_markdown && titleDraft === activeDocument.title;
    if (unchanged) {
      setCurrentSaveState('idle');
      return;
    }
    if (saveStateRef.current === 'conflict' || conflictActionPendingRef.current) return;
    setCurrentSaveState('saving');
    if (saveTimerRef.current) window.clearTimeout(saveTimerRef.current);
    saveTimerRef.current = window.setTimeout(async () => {
      const {
        draft: currentDraft,
        titleDraft: currentTitle,
        activeDocument: currentDocument,
      } = draftRef.current;
      if (!currentDocument) return;
      if (saveInFlightRef.current) return;
      saveInFlightRef.current = true;
      try {
        await persistDraft(
          currentDocument,
          currentDraft,
          currentTitle,
          loadedRevision.current ?? currentDocument.current_revision_id,
        );
      } catch (reason) {
        const isConflict = reason instanceof HttpError && reason.status === 409;
        setCurrentSaveState(isConflict ? 'conflict' : 'error');
        setError(errorMessage(reason, 'Unable to save.'));
        if (isConflict) {
          void refreshLatestDocument(currentDocument.id).catch(() => undefined);
        }
      } finally {
        saveInFlightRef.current = false;
      }
    }, 1500);
    return () => {
      if (saveTimerRef.current) window.clearTimeout(saveTimerRef.current);
    };
  }, [
    activeDocument,
    draft,
    titleDraft,
    saveState,
    persistDraft,
    refreshLatestDocument,
    setCurrentSaveState,
    setError,
    draftRef,
    lastPersistedDraft,
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
): Promise<{ readonly project: Project; readonly document: StudioDocument }> {
  const project = await api.project(projectId);
  const document = project.documents?.find((candidate) => candidate.id === documentId);
  if (!document) throw new Error('The document is no longer available.');
  return { project, document };
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
