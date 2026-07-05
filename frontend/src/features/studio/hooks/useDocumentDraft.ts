import { useCallback, useEffect, useRef, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';

import { HttpError, api } from '@/app/api';
import type { Project, Revision, SaveState, StudioDocument } from '@/app/types/studio';

function errorMessage(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback;
}

interface DraftState {
  readonly documentId: string | null;
  readonly draft: string;
  readonly titleDraft: string;
  readonly saveState: SaveState;
}

interface RevisionState {
  readonly documentId: string | null;
  readonly revisions: Revision[];
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
  onActiveDocumentChanged?: () => void,
) {
  const [draftState, setDraftState] = useState<DraftState>(() => draftStateFor(activeDocument));
  const activeDocumentId = activeDocument?.id ?? null;
  const [revisionState, setRevisionState] = useState<RevisionState>(() => ({
    documentId: activeDocumentId,
    revisions: [],
  }));
  const loadedRevision = useRef<string | null>(null);
  const saveTimer = useRef<number | null>(null);
  const activeDraftState = stateForDocument(draftState, activeDocument);
  const { draft, titleDraft, saveState } = activeDraftState;
  const revisions = revisionState.documentId === activeDocumentId ? revisionState.revisions : [];
  const draftRef = useRef({ draft, titleDraft, activeDocument });

  useEffect(() => {
    draftRef.current = { draft, titleDraft, activeDocument };
  }, [draft, titleDraft, activeDocument]);

  const loadRevisions = useCallback(
    (documentId: string) => {
      void api
        .revisions(projectId, documentId)
        .then((response) => {
          setRevisionState({ documentId, revisions: response.revisions });
        })
        .catch((reason: unknown) => {
          setError(errorMessage(reason, 'Unable to load revisions.'));
        });
    },
    [projectId, setError],
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
      loadRevisions(document.id);
    },
    [loadRevisions],
  );

  useEffect(() => {
    if (activeDocumentId === null) {
      loadedRevision.current = null;
      return;
    }
    const currentDocument = draftRef.current.activeDocument;
    if (!currentDocument || currentDocument.id !== activeDocumentId) return;
    onActiveDocumentChanged?.();
    loadedRevision.current = currentDocument.current_revision_id;
    loadRevisions(activeDocumentId);
  }, [activeDocumentId, loadRevisions, onActiveDocumentChanged]);

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
        void api
          .revisions(projectId, currentDocument.id)
          .then((response) => {
            setRevisionState({
              documentId: currentDocument.id,
              revisions: response.revisions,
            });
          })
          .catch((reason: unknown) => {
            setError(errorMessage(reason, 'Unable to load revisions.'));
          });
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
  }, [draft, titleDraft, activeDocument, projectId, setCurrentSaveState, setError, setProject]);

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
        const response = await api.revisions(projectId, activeDocument.id);
        setRevisionState({
          documentId: activeDocument.id,
          revisions: response.revisions,
        });
      } catch (reason) {
        setError(errorMessage(reason, 'Unable to restore revision.'));
      }
    },
    [activeDocument, projectId, setError, setProject],
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
