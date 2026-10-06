import type { MutableRefObject } from "react";

import type { SaveState } from "@/app/types/studio";

import type { DraftSnapshot, PersistedDraft } from "./documentDraftState";

interface SaveNowContext {
  readonly ownerKey: string;
  readonly ownerToken: symbol;
  readonly isCurrentOwner: () => boolean;
  readonly draftRef: MutableRefObject<DraftSnapshot>;
  readonly persistedDraftsRef: MutableRefObject<Map<string, PersistedDraft>>;
  readonly saveStateRef: MutableRefObject<SaveState>;
  readonly saveTimerRef: MutableRefObject<number | null>;
  readonly saveInFlightRef: MutableRefObject<Set<string>>;
  readonly setCurrentSaveState: (nextSaveState: SaveState) => void;
  readonly executeSave: () => void;
  readonly retrySave: () => void;
}

/**
 * Flushes the active Draft on demand for the Ctrl/Cmd+S shortcut (DR-016):
 * cancels the pending debounce and persists through the same path the
 * autosave uses. Failure semantics: a no-op when the Draft has no
 * unpersisted edits, when a save is already in flight, or while the
 * conflict surface owns the resolution; the error state delegates to
 * `retrySave`, so a manual save keeps the DR-001 retry semantics.
 */
export function flushDraftNow(context: SaveNowContext): void {
  const { draftRef, ownerKey, ownerToken, isCurrentOwner, saveInFlightRef, saveStateRef } = context;
  const document = draftRef.current.activeDocument;
  if (
    document === null ||
    draftRef.current.ownerToken !== ownerToken ||
    !isCurrentOwner() ||
    saveInFlightRef.current.has(ownerKey)
  ) {
    return;
  }
  if (saveStateRef.current === "conflict") return;
  if (saveStateRef.current === "error") {
    context.retrySave();
    return;
  }
  const { draft, titleDraft } = draftRef.current;
  const persisted = context.persistedDraftsRef.current.get(ownerKey);
  const alreadyPersisted =
    persisted?.ownerKey === ownerKey &&
    persisted.draft === draft &&
    persisted.titleDraft === titleDraft;
  const unchanged = draft === document.content_markdown && titleDraft === document.title;
  if (unchanged || alreadyPersisted) return;
  if (context.saveTimerRef.current !== null) {
    window.clearTimeout(context.saveTimerRef.current);
    context.saveTimerRef.current = null;
  }
  context.setCurrentSaveState("saving");
  context.executeSave();
}
