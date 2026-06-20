import { useCallback, useEffect, useRef, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';

import { HttpError, api } from '@/app/api';
import type { Project, Revision, SaveState, StudioDocument } from '@/app/types/studio';

function errorMessage(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback;
}

export function useDocumentDraft(
  activeDocument: StudioDocument | null,
  projectId: string,
  setProject: Dispatch<SetStateAction<Project | null>>,
  setError: Dispatch<SetStateAction<string | null>>,
  onActiveDocumentChanged?: () => void,
) {
  const [draft, setDraft] = useState('');
  const [titleDraft, setTitleDraft] = useState('');
  const [saveState, setSaveState] = useState<SaveState>('idle');
  const [revisions, setRevisions] = useState<Revision[]>([]);
  const loadedRevision = useRef<string | null>(null);
  const saveTimer = useRef<number | null>(null);
  const draftRef = useRef({ draft, titleDraft, activeDocument: null as StudioDocument | null });

  useEffect(() => {
    draftRef.current = { draft, titleDraft, activeDocument };
  }, [draft, titleDraft, activeDocument]);

  const resetFor = useCallback(
    (document: StudioDocument, nextSaveState: SaveState = 'idle') => {
      loadedRevision.current = document.current_revision_id;
      setDraft(document.content_markdown);
      setTitleDraft(document.title);
      setSaveState(nextSaveState);
      void api
        .revisions(projectId, document.id)
        .then((response) => {
          setRevisions(response.revisions);
        })
        .catch((reason: unknown) => {
          setError(errorMessage(reason, 'Unable to load revisions.'));
        });
    },
    [projectId, setError],
  );

  useEffect(() => {
    if (!activeDocument) return;
    onActiveDocumentChanged?.();
    resetFor(activeDocument);
    // Only reset when the active document identity changes, not when its content is mutated.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- Reset draft for a new document id; content changes are handled by user edits and autosave.
  }, [activeDocument?.id, onActiveDocumentChanged, resetFor]);

  useEffect(() => {
    if (!activeDocument) return;
    const unchanged =
      draft === activeDocument.content_markdown && titleDraft === activeDocument.title;
    if (unchanged) {
      setSaveState('idle');
      return;
    }
    setSaveState('saving');
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
        setTitleDraft(saved.title);
        setSaveState('saved');
        void api
          .revisions(projectId, currentDocument.id)
          .then((response) => {
            setRevisions(response.revisions);
          })
          .catch((reason: unknown) => {
            setError(errorMessage(reason, 'Unable to load revisions.'));
          });
      } catch (reason) {
        setSaveState(reason instanceof HttpError && reason.status === 409 ? 'conflict' : 'error');
        setError(errorMessage(reason, 'Unable to save.'));
      }
    }, 1500);
    return () => {
      if (saveTimer.current) window.clearTimeout(saveTimer.current);
    };
  }, [draft, titleDraft, activeDocument, projectId, setError, setProject]);

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
        setDraft(restored.content_markdown);
        setTitleDraft(restored.title);
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
        setRevisions(response.revisions);
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
