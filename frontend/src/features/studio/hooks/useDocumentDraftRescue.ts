import { type MutableRefObject, useCallback, useEffect, useRef } from "react";

import type { SaveState, StudioDocument } from "@/app/types/studio";
import { saveDocumentDraft } from "./documentDraftPersistence";

export interface RescueCandidate {
  readonly ownerKey: string;
  readonly projectId: string;
  readonly document: StudioDocument;
  readonly draft: string;
  readonly titleDraft: string;
  readonly baseRevisionId: string;
}

interface DraftWriteAttempt {
  readonly ownerKey: string;
  readonly draft: string;
  readonly titleDraft: string;
}

interface RescueOptions {
  readonly ownerKey: string;
  readonly activeDocument: StudioDocument | null;
  readonly draft: string;
  readonly titleDraft: string;
  readonly saveState: SaveState;
  readonly loadedRevision: MutableRefObject<string | null>;
  readonly saveInFlightRef: MutableRefObject<Set<string>>;
  readonly getInFlightAttempt: () => DraftWriteAttempt | null;
}

/**
 * Rescues a dirty Draft when the editor leaves its owner: a document switch
 * hands the newest local text to one detached write, and an unmount (route
 * departure, tab close) does the same. Conflicts never enter the rescue path;
 * they stay on the explicit conflict surface.
 *
 * Failure semantics: the rescue write is fire-and-forget by design — the
 * editor has already left the Document, so a failed rescue stays silent and
 * the next open reads the server state. A write that an in-flight autosave
 * already covers with identical text is skipped to avoid a duplicate request
 * racing its own base revision.
 */
export function useDocumentDraftRescue({
  ownerKey,
  activeDocument,
  draft,
  titleDraft,
  saveState,
  loadedRevision,
  saveInFlightRef,
  getInFlightAttempt,
}: RescueOptions): void {
  const candidateRef = useRef<RescueCandidate | null>(null);

  const writeRescue = useCallback(
    (candidate: RescueCandidate) => {
      const attempt = getInFlightAttempt();
      const identicalAttemptInFlight =
        saveInFlightRef.current.has(candidate.ownerKey) &&
        attempt !== null &&
        attempt.ownerKey === candidate.ownerKey &&
        attempt.draft === candidate.draft &&
        attempt.titleDraft === candidate.titleDraft;
      if (identicalAttemptInFlight) return;
      void (async () => {
        try {
          await saveDocumentDraft(
            candidate.projectId,
            candidate.document,
            candidate.draft,
            candidate.titleDraft,
            candidate.baseRevisionId,
          );
        } catch {
          // Detached rescue write: the editor already left this Document, so
          // a failure is deliberately silent; the next open reads the server
          // state and the original save path owns user-visible errors.
        }
      })();
    },
    [getInFlightAttempt, saveInFlightRef],
  );

  useEffect(() => {
    const dirty =
      activeDocument !== null &&
      (draft !== activeDocument.content_markdown || titleDraft !== activeDocument.title);
    const previous = candidateRef.current;
    if (previous !== null && previous.ownerKey !== ownerKey) {
      writeRescue(previous);
    }
    candidateRef.current =
      dirty && saveState !== "conflict"
        ? {
            ownerKey,
            projectId: activeDocument.project_id,
            document: activeDocument,
            draft,
            titleDraft,
            baseRevisionId: loadedRevision.current ?? activeDocument.current_revision_id,
          }
        : null;
  }, [activeDocument, draft, loadedRevision, ownerKey, saveState, titleDraft, writeRescue]);

  useEffect(
    () => () => {
      const candidate = candidateRef.current;
      candidateRef.current = null;
      if (candidate !== null) writeRescue(candidate);
    },
    [writeRescue],
  );
}
