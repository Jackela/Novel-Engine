import {
  type Dispatch,
  type MutableRefObject,
  type SetStateAction,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import { HttpError } from "@/app/api";
import { translateActive } from "@/app/i18n/translate";
import type { SaveState, StudioDocument } from "@/app/types/studio";
import type { DraftSnapshot, PersistedDraft } from "./documentDraftState";
import { flushDraftNow } from "./flushDraftNow";
import { toErrorMessage } from "./toErrorMessage";
import { useDocumentDraftRescue } from "./useDocumentDraftRescue";

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

interface AutosaveHandle {
  readonly retrySave: () => void;
  readonly saveNow: () => void;
}

interface SaveAttempt {
  readonly ownerKey: string;
  readonly draft: string;
  readonly titleDraft: string;
}

/** Debounce applied to a fresh Draft edit before the first autosave attempt. */
const AUTOSAVE_DEBOUNCE_MS = 1500;

/**
 * Backoff schedule for automatic retries after a transport-level save failure.
 * The last entry caps the interval so a long outage keeps retrying without
 * hammering the service.
 */
const AUTOSAVE_RETRY_DELAYS_MS = [5_000, 15_000, 30_000] as const;

/**
 * Autosaves the active Draft: a debounced first attempt, capped-backoff
 * automatic retries after a failed save, and a manual retry handle for the
 * error surface. Leaving a dirty Document is handled by
 * {@link useDocumentDraftRescue}, which writes the newest local text before
 * the editor moves on.
 *
 * Failure semantics: a retry never publishes state for a stale owner — the
 * attempt re-checks ownership and the newest Draft through refs. Conflict
 * responses never reach the retry path; they stay on the explicit
 * conflict-action surface.
 */
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
}: AutosaveOptions): AutosaveHandle {
  const [pendingAutosaves, setPendingAutosaves] = useState<ReadonlySet<string>>(() => new Set());
  const isAutosavePending = pendingAutosaves.has(ownerKey);
  const retryTimerRef = useRef<number | null>(null);
  const retryAttemptRef = useRef(0);
  const attemptRef = useRef<SaveAttempt | null>(null);
  const scheduleRetryRef = useRef<() => void>(() => {});

  const clearRetryTimer = useCallback(() => {
    if (retryTimerRef.current !== null) {
      window.clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }
  }, []);

  const executeSave = useCallback(async () => {
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
    attemptRef.current = { ownerKey, draft: currentDraft, titleDraft: currentTitle };
    setPendingAutosaves((current) => new Set(current).add(ownerKey));
    try {
      await persistDraft(
        currentDocument,
        currentDraft,
        currentTitle,
        loadedRevision.current ?? currentDocument.current_revision_id,
        editVersion,
      );
      retryAttemptRef.current = 0;
      clearRetryTimer();
    } catch (reason) {
      if (!isCurrentProject()) return;
      const isConflict = reason instanceof HttpError && reason.status === 409;
      if (!isConflict) {
        setCurrentSaveState("error");
        if (isCurrentOwner()) {
          setError(toErrorMessage(reason, translateActive("errors.saveDocument")));
        }
        scheduleRetryRef.current();
        return;
      }
      // Land the winning body before publishing the conflict surface (#472):
      // conflict actions refuse to start while this save still holds the
      // saveInFlight lock, so an early "Save conflict" renders clickable
      // buttons that silently swallow the discard click and strand the
      // editor in conflict once the recovery tail settles.
      let recoveryError: string | null = null;
      try {
        await refreshLatestDocument(currentDocument.id);
      } catch (refreshReason) {
        recoveryError = toErrorMessage(refreshReason, translateActive("errors.refreshDocument"));
      }
      setCurrentSaveState("conflict");
      if (isCurrentOwner()) {
        setError(recoveryError ?? toErrorMessage(reason, translateActive("errors.saveDocument")));
      }
    } finally {
      saveInFlightRef.current.delete(ownerKey);
      attemptRef.current = null;
      // Recheck a new lifecycle's Draft when the old request releases its
      // lock, even when that request's error must remain invisible.
      setPendingAutosaves((current) => {
        const next = new Set(current);
        next.delete(ownerKey);
        return next;
      });
    }
  }, [
    clearRetryTimer,
    draftRef,
    isCurrentOwner,
    isCurrentProject,
    loadedRevision,
    ownerKey,
    ownerToken,
    persistDraft,
    refreshLatestDocument,
    saveInFlightRef,
    setCurrentSaveState,
    setError,
  ]);

  const scheduleRetry = useCallback(() => {
    const delay =
      AUTOSAVE_RETRY_DELAYS_MS[
        Math.min(retryAttemptRef.current, AUTOSAVE_RETRY_DELAYS_MS.length - 1)
      ];
    retryAttemptRef.current += 1;
    clearRetryTimer();
    retryTimerRef.current = window.setTimeout(() => {
      retryTimerRef.current = null;
      if (saveStateRef.current !== "error") return;
      setCurrentSaveState("saving");
      void executeSave();
    }, delay);
  }, [clearRetryTimer, executeSave, saveStateRef, setCurrentSaveState]);

  useEffect(() => {
    scheduleRetryRef.current = scheduleRetry;
  }, [scheduleRetry]);

  // An owner switch abandons the previous owner's retry schedule; the new
  // owner starts with a clean attempt counter.
  // biome-ignore lint/correctness/useExhaustiveDependencies: ownerKey is an intentional change trigger for this cleanup-only effect; the reset and cleared timer communicate through refs, not by reading the key.
  useEffect(() => {
    retryAttemptRef.current = 0;
    return () => clearRetryTimer();
  }, [clearRetryTimer, ownerKey]);

  const getInFlightAttempt = useCallback(() => attemptRef.current, []);

  useDocumentDraftRescue({
    ownerKey,
    activeDocument,
    draft,
    titleDraft,
    saveState,
    loadedRevision,
    saveInFlightRef,
    getInFlightAttempt,
  });

  const retrySave = useCallback(() => {
    if (saveStateRef.current !== "error") return;
    clearRetryTimer();
    retryAttemptRef.current = 0;
    setCurrentSaveState("saving");
    void executeSave();
  }, [clearRetryTimer, executeSave, saveStateRef, setCurrentSaveState]);

  /**
   * Flushes the draft on demand for the Ctrl/Cmd+S shortcut; the debounce,
   * in-flight, conflict, and DR-001 retry semantics live in
   * {@link flushDraftNow}.
   */
  const saveNow = useCallback(() => {
    flushDraftNow({
      ownerKey,
      ownerToken,
      isCurrentOwner,
      draftRef,
      persistedDraftsRef,
      saveStateRef,
      saveTimerRef,
      saveInFlightRef,
      setCurrentSaveState,
      executeSave,
      retrySave,
    });
  }, [
    draftRef,
    executeSave,
    isCurrentOwner,
    ownerKey,
    ownerToken,
    persistedDraftsRef,
    retrySave,
    saveInFlightRef,
    saveStateRef,
    saveTimerRef,
    setCurrentSaveState,
  ]);

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
      isAutosavePending ||
      conflictActionPendingRef.current === ownerToken
    ) {
      return;
    }
    clearRetryTimer();
    setCurrentSaveState("saving");
    if (saveTimerRef.current) window.clearTimeout(saveTimerRef.current);
    saveTimerRef.current = window.setTimeout(() => {
      void executeSave();
    }, AUTOSAVE_DEBOUNCE_MS);
    return () => {
      if (saveTimerRef.current) window.clearTimeout(saveTimerRef.current);
    };
  }, [
    activeDocument,
    ownerKey,
    ownerToken,
    draft,
    titleDraft,
    saveState,
    isAutosavePending,
    clearRetryTimer,
    executeSave,
    setCurrentSaveState,
    persistedDraftsRef,
    saveStateRef,
    conflictActionPendingRef,
    saveTimerRef,
  ]);

  return { retrySave, saveNow };
}
