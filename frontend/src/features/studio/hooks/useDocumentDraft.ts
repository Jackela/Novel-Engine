import { useCallback, useEffect, useRef, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';

import { HttpError } from '@/app/api';
import type { Project, SaveState, StudioDocument } from '@/app/types/studio';

import { useRevisionCache } from './useRevisionCache';
import {
  loadLatestDocument,
  restoreDocumentRevision,
  saveDocumentDraft,
  useDocumentDraftAutosave,
} from './useDocumentDraftAutosave';

function errorMessage(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback;
}

interface DraftState {
  readonly documentId: string | null;
  readonly draft: string;
  readonly titleDraft: string;
  readonly saveState: SaveState;
}

interface PersistedDraft {
  readonly documentId: string;
  readonly draft: string;
  readonly titleDraft: string;
}

function draftStateFor(document: StudioDocument | null, saveState: SaveState = 'idle'): DraftState {
  return {
    documentId: document?.id ?? null,
    draft: document?.content_markdown ?? '',
    titleDraft: document?.title ?? '',
    saveState,
  };
}

function stateForDocument(current: DraftState, document: StudioDocument | null): DraftState {
  return current.documentId === document?.id ? current : draftStateFor(document);
}

export function useDocumentDraft(
  activeDocument: StudioDocument | null,
  projectId: string,
  setProject: Dispatch<SetStateAction<Project | null>>,
  setError: Dispatch<SetStateAction<string | null>>,
) {
  const [draftState, setDraftState] = useState<DraftState>(() => draftStateFor(activeDocument));
  const activeDocumentId = activeDocument?.id ?? null;
  const loadedRevision = useRef<string | null>(activeDocument?.current_revision_id ?? null);
  const saveTimer = useRef<number | null>(null);
  const saveInFlight = useRef(false);
  const lastPersistedDraft = useRef<PersistedDraft | null>(null);
  const activeDraftState = stateForDocument(draftState, activeDocument);
  const { draft, titleDraft, saveState } = activeDraftState;
  const draftRef = useRef({ draft, titleDraft, activeDocument });
  const [isConflictActionPending, setIsConflictActionPending] = useState(false);
  const saveStateRef = useRef(saveState);
  const conflictActionPendingRef = useRef(isConflictActionPending);

  useEffect(() => {
    draftRef.current = { draft, titleDraft, activeDocument };
  }, [draft, titleDraft, activeDocument]);

  useEffect(() => {
    saveStateRef.current = saveState;
    conflictActionPendingRef.current = isConflictActionPending;
  }, [isConflictActionPending, saveState]);

  useEffect(() => {
    loadedRevision.current = activeDocument?.current_revision_id ?? null;
  }, [activeDocument?.current_revision_id]);

  const reportRevisionError = useCallback(
    (reason: unknown) => {
      setError(errorMessage(reason, 'Unable to load revisions.'));
    },
    [setError],
  );
  const { revisions, refreshDocumentRevisions } = useRevisionCache(
    projectId,
    activeDocumentId,
    reportRevisionError,
  );

  const setDraft = useCallback<Dispatch<SetStateAction<string>>>((nextDraft) => {
    setDraftState((current) => {
      const currentState = stateForDocument(current, draftRef.current.activeDocument);
      return {
        ...currentState,
        draft: typeof nextDraft === 'function' ? nextDraft(currentState.draft) : nextDraft,
      };
    });
  }, []);

  const setTitleDraft = useCallback<Dispatch<SetStateAction<string>>>((nextTitle) => {
    setDraftState((current) => {
      const currentState = stateForDocument(current, draftRef.current.activeDocument);
      return {
        ...currentState,
        titleDraft:
          typeof nextTitle === 'function' ? nextTitle(currentState.titleDraft) : nextTitle,
      };
    });
  }, []);

  const setCurrentSaveState = useCallback((nextSaveState: SaveState) => {
    saveStateRef.current = nextSaveState;
    setDraftState((current) => ({
      ...stateForDocument(current, draftRef.current.activeDocument),
      saveState: nextSaveState,
    }));
  }, []);

  const resetFor = useCallback(
    (document: StudioDocument, nextSaveState: SaveState = 'idle') => {
      loadedRevision.current = document.current_revision_id;
      lastPersistedDraft.current = {
        documentId: document.id,
        draft: document.content_markdown,
        titleDraft: document.title,
      };
      setDraftState(draftStateFor(document, nextSaveState));
      refreshDocumentRevisions(document.id);
    },
    [refreshDocumentRevisions],
  );

  const refreshLatestDocument = useCallback(
    async (documentId: string): Promise<StudioDocument> => {
      const { project, document } = await loadLatestDocument(projectId, documentId);
      loadedRevision.current = document.current_revision_id;
      setProject(project);
      return document;
    },
    [projectId, setProject],
  );

  const persistDraft = useCallback(
    async (
      document: StudioDocument,
      content: string,
      title: string,
      baseRevisionId: string,
    ): Promise<StudioDocument> => {
      const saved = await saveDocumentDraft(projectId, document, content, title, baseRevisionId);
      loadedRevision.current = saved.current_revision_id;
      saveStateRef.current = 'saved';
      lastPersistedDraft.current = {
        documentId: saved.id,
        draft: content,
        titleDraft: saved.title,
      };
      setProject((current) =>
        current
          ? {
              ...current,
              documents: current.documents?.map((currentDocument) =>
                currentDocument.id === saved.id ? saved : currentDocument,
              ),
            }
          : current,
      );
      setDraftState((current) => ({
        ...stateForDocument(current, document),
        titleDraft: saved.title,
        saveState: 'saved',
      }));
      refreshDocumentRevisions(document.id);
      setError(null);
      return saved;
    },
    [projectId, refreshDocumentRevisions, setError, setProject],
  );

  useDocumentDraftAutosave({
    activeDocument,
    draft,
    titleDraft,
    saveState,
    draftRef,
    lastPersistedDraft,
    loadedRevision,
    saveStateRef,
    conflictActionPendingRef,
    saveTimerRef: saveTimer,
    saveInFlightRef: saveInFlight,
    persistDraft,
    refreshLatestDocument,
    setCurrentSaveState,
    setError,
  });

  const loadLatest = useCallback(async () => {
    if (!activeDocument || conflictActionPendingRef.current || saveInFlight.current) return;
    if (saveTimer.current) window.clearTimeout(saveTimer.current);
    setIsConflictActionPending(true);
    conflictActionPendingRef.current = true;
    try {
      const latestDocument = await refreshLatestDocument(activeDocument.id);
      lastPersistedDraft.current = {
        documentId: latestDocument.id,
        draft: latestDocument.content_markdown,
        titleDraft: latestDocument.title,
      };
      saveStateRef.current = 'idle';
      setDraftState(draftStateFor(latestDocument));
      refreshDocumentRevisions(latestDocument.id);
      setError(null);
    } catch (reason) {
      setCurrentSaveState('error');
      setError(errorMessage(reason, 'Unable to load the latest document.'));
    } finally {
      setIsConflictActionPending(false);
      conflictActionPendingRef.current = false;
    }
  }, [
    activeDocument,
    refreshDocumentRevisions,
    refreshLatestDocument,
    setCurrentSaveState,
    setError,
  ]);

  const retryOverwrite = useCallback(async () => {
    if (!activeDocument || conflictActionPendingRef.current || saveInFlight.current) return;
    if (saveTimer.current) window.clearTimeout(saveTimer.current);
    setIsConflictActionPending(true);
    conflictActionPendingRef.current = true;
    saveInFlight.current = true;
    const { draft: currentDraft, titleDraft: currentTitle } = draftRef.current;
    try {
      const latestDocument = await refreshLatestDocument(activeDocument.id);
      setCurrentSaveState('saving');
      await persistDraft(
        latestDocument,
        currentDraft,
        currentTitle,
        latestDocument.current_revision_id,
      );
    } catch (reason) {
      setCurrentSaveState(
        reason instanceof HttpError && reason.status === 409 ? 'conflict' : 'error',
      );
      setError(errorMessage(reason, 'Unable to overwrite the latest document.'));
    } finally {
      saveInFlight.current = false;
      setIsConflictActionPending(false);
      conflictActionPendingRef.current = false;
    }
  }, [activeDocument, persistDraft, refreshLatestDocument, setCurrentSaveState, setError]);

  const restoreRevision = useCallback(
    async (revisionId: string) => {
      if (!activeDocument) return;
      try {
        const restored = await restoreDocumentRevision(
          projectId,
          activeDocument,
          revisionId,
          loadedRevision.current ?? activeDocument.current_revision_id,
        );
        loadedRevision.current = restored.current_revision_id;
        setDraftState((current) => {
          const currentState = stateForDocument(current, activeDocument);
          return draftStateFor(restored, currentState.saveState);
        });
        setProject((current) =>
          current
            ? {
                ...current,
                documents: current.documents?.map((document) =>
                  document.id === restored.id ? restored : document,
                ),
              }
            : current,
        );
        await refreshDocumentRevisions(activeDocument.id);
      } catch (reason) {
        setError(errorMessage(reason, 'Unable to restore revision.'));
      }
    },
    [activeDocument, projectId, refreshDocumentRevisions, setError, setProject],
  );

  return {
    draft,
    setDraft,
    titleDraft,
    setTitleDraft,
    saveState,
    loadedRevision,
    revisions,
    resetFor,
    restoreRevision,
    isConflictActionPending,
    loadLatest,
    retryOverwrite,
  };
}
