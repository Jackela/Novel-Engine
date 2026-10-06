import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/app/api";
import { translateActive } from "@/app/i18n/translate";
import type { RevisionDetail } from "@/app/types/revision";
import type { StudioDocument } from "@/app/types/studio";

import type { DocumentDraftOwner } from "./documentDraftState";
import { toErrorMessage } from "./toErrorMessage";

export interface ServerVersionPreview {
  readonly isOpen: boolean;
  readonly isLoading: boolean;
  readonly error: string | null;
  /** The body of the current server revision the local draft would supersede. */
  readonly revision: RevisionDetail | null;
  /** The current server revision id at read time; the revision keep-local would replace. */
  readonly currentRevisionId: string | null;
}

export interface ServerVersionPreviewController extends ServerVersionPreview {
  readonly view: () => Promise<void>;
  readonly hide: () => void;
}

const CLOSED_PREVIEW: ServerVersionPreview = {
  isOpen: false,
  isLoading: false,
  error: null,
  revision: null,
  currentRevisionId: null,
};

interface UseConflictServerPreviewArgs {
  readonly activeDocument: StudioDocument | null;
  readonly projectId: string;
  readonly owner: DocumentDraftOwner;
  readonly isCurrentOwner: (candidate: DocumentDraftOwner) => boolean;
  /** The conflict surface is visible; leaving it closes any open preview. */
  readonly conflictVisible: boolean;
}

/**
 * DR-012 read-only server-version view for the save-conflict panel. Reads the
 * document's current revision, then its body through the DR-011 endpoint; it
 * publishes nothing into the draft, the project, or the revision cache, so
 * the author can compare before choosing keep local or load latest. A stale
 * response or a closed/left-conflict surface discards the read.
 */
export function useConflictServerPreview({
  activeDocument,
  projectId,
  owner,
  isCurrentOwner,
  conflictVisible,
}: UseConflictServerPreviewArgs): ServerVersionPreviewController {
  const [state, setState] = useState<ServerVersionPreview>(CLOSED_PREVIEW);
  const requestRef = useRef(0);
  // Latest-value visibility flag for the async read guards; synced after
  // commit so no render work mutates the ref.
  const conflictVisibleRef = useRef(conflictVisible);
  useEffect(() => {
    conflictVisibleRef.current = conflictVisible;
  }, [conflictVisible]);
  const [resolvedConflictVisible, setResolvedConflictVisible] = useState(conflictVisible);
  if (resolvedConflictVisible !== conflictVisible) {
    // React's documented reset-when-a-prop-changes pattern: leaving the
    // conflict surface closes any open preview during render, so no stale
    // frame paints and no effect is needed.
    setResolvedConflictVisible(conflictVisible);
    setState(CLOSED_PREVIEW);
  }

  const hide = useCallback(() => {
    requestRef.current += 1;
    setState(CLOSED_PREVIEW);
  }, []);

  const view = useCallback(async () => {
    if (!activeDocument) return;
    const request = requestRef.current + 1;
    requestRef.current = request;
    setState({ ...CLOSED_PREVIEW, isOpen: true, isLoading: true });
    try {
      const latest = await api.document(projectId, activeDocument.id);
      const revision = await api.revision(projectId, activeDocument.id, latest.current_revision_id);
      if (requestRef.current !== request || !isCurrentOwner(owner) || !conflictVisibleRef.current) {
        return;
      }
      setState({
        isOpen: true,
        isLoading: false,
        error: null,
        revision,
        currentRevisionId: latest.current_revision_id,
      });
    } catch (reason) {
      if (requestRef.current !== request || !isCurrentOwner(owner) || !conflictVisibleRef.current) {
        return;
      }
      setState({
        ...CLOSED_PREVIEW,
        isOpen: true,
        error: toErrorMessage(reason, translateActive("editor.conflict.server.error")),
      });
    }
  }, [activeDocument, isCurrentOwner, owner, projectId]);

  return { ...state, view, hide };
}
