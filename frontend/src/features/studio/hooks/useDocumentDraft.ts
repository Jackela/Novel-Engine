import { useCallback, useEffect, useRef, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';

import { HttpError, api } from '@/app/api';
import type { Project, SaveState, StudioDocument } from '@/app/types/studio';

import { useRevisionCache } from './useRevisionCache';

function errorMessage(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback;
}

interface DraftState {
  readonly documentId: string | null;
  readonly draft: string;
  readonly titleDraft: string;
  readonly saveState: SaveState;
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
  const activeDraftState = stateForDocument(draftState, activeDocument);
  const { draft, titleDraft, saveState } = activeDraftState;
  const draftRef = useRef({ draft, titleDraft, activeDocument });

  useEffect(() => {
    draftRef.current = { draft, titleDraft, activeDocument };
  }, [draft, titleDraft, activeDocument]);

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
    setDraftState((current) => ({
      ...stateForDocument(current, draftRef.current.activeDocument),
      saveState: nextSaveState,
    }));
  }, []);

  const resetFor = useCallback(
    (document: StudioDocument, nextSaveState: SaveState = 'idle') => {
      loadedRevision.current = document.current_revision_id;
      setDraftState(draftStateFor(document, nextSaveState));
      refreshDocumentRevisions(document.id);
    },
    [refreshDocumentRevisions],
  );

  useEffect(() => {
    if (!activeDocument) return;
    const unchanged =
      draft === activeDocument.content_markdown && titleDraft === activeDocument.title;
    if (unchanged) {
      setCurrentSaveState('idle');
      return;
    }
    setCurrentSaveState('saving');
    if (saveTimer.current) window.clearTimeout(saveTimer.current);
    saveTimer.current = window.setTimeout(async () => {
      const {
        draft: currentDraft,
        titleDraft: currentTitle,
        activeDocument: currentDocument,
      } = draftRef.current;
      if (!currentDocument) return;
      try {
        const saved = await api.saveDocument(projectId, currentDocument.id, {
          content_markdown: currentDraft,
          base_revision_id: loadedRevision.current ?? currentDocument.current_revision_id,
          title: currentTitle,
        });
        loadedRevision.current = saved.current_revision_id;
        setProject((current) =>
          current
            ? {
                ...current,
                documents: current.documents?.map((document) =>
                  document.id === saved.id ? saved : document,
                ),
              }
            : current,
        );
        setDraftState((current) => ({
          ...stateForDocument(current, currentDocument),
          titleDraft: saved.title,
          saveState: 'saved',
        }));
        refreshDocumentRevisions(currentDocument.id);
      } catch (reason) {
        setCurrentSaveState(
          reason instanceof HttpError && reason.status === 409 ? 'conflict' : 'error',
        );
        setError(errorMessage(reason, 'Unable to save.'));
      }
    }, 1500);
    return () => {
      if (saveTimer.current) window.clearTimeout(saveTimer.current);
    };
  }, [
    draft,
    titleDraft,
    activeDocument,
    projectId,
    refreshDocumentRevisions,
    setCurrentSaveState,
    setError,
    setProject,
  ]);

  const restoreRevision = useCallback(
    async (revisionId: string) => {
      if (!activeDocument) return;
      try {
        const restored = await api.restoreRevision(
          projectId,
          activeDocument.id,
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
        refreshDocumentRevisions(activeDocument.id);
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
  };
}
