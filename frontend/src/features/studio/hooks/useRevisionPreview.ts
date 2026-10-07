import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/app/api";
import { translateActive } from "@/app/i18n/translate";
import type { RevisionDetail } from "@/app/types/revision";
import type { StudioDocument } from "@/app/types/studio";

import { toErrorMessage } from "./toErrorMessage";

/** The project/document scope plus the loaded current body the diff compares against (DR-011). */
export interface RevisionPreviewScope {
  readonly projectId: string;
  readonly documentId: string;
  readonly currentContent: string;
}

/**
 * The preview/diff scope of one loaded document: its identity plus the
 * current body the diff compares against. Null when no document is open.
 */
export function revisionPreviewScope(
  projectId: string,
  document: Pick<StudioDocument, "id" | "content_markdown"> | null,
): RevisionPreviewScope | null {
  return document === null
    ? null
    : { projectId, documentId: document.id, currentContent: document.content_markdown };
}

export type RevisionPreviewState =
  | { readonly status: "idle" }
  | { readonly status: "loading" }
  | { readonly status: "loaded"; readonly revision: RevisionDetail }
  | { readonly status: "error"; readonly message: string };

export interface RevisionPreviewController {
  readonly isOpen: (revisionId: string) => boolean;
  readonly stateFor: (revisionId: string) => RevisionPreviewState;
  readonly toggle: (revisionId: string) => void;
  readonly retry: (revisionId: string) => void;
}

const IDLE_STATE: RevisionPreviewState = { status: "idle" };

/**
 * Localized failure text with the raw transport detail in parentheses when one
 * exists, so the panel stays readable in either language while a permanent
 * failure (for example a 404) is still distinguishable from a transient one.
 */
function previewFailureMessage(reason: unknown): string {
  const fallback = translateActive("history.preview.error");
  const detail = toErrorMessage(reason, fallback);
  return detail === fallback ? fallback : `${fallback} (${detail})`;
}

/**
 * Lazy, read-only revision-body previews for one document scope (DR-011).
 * Opening a row fetches its body once over the single-revision endpoint;
 * closing it keeps that body cached, and switching documents drops both the
 * cache and the open row. Stale responses are discarded per revision by
 * request sequence, so concurrent reads for different rows settle
 * independently. A response publishes only while that row is still the
 * loading entry for the same sequence: the document switch clears the cache
 * during render, so a read issued before the switch cannot write into the
 * reset cache even when no newer request supersedes it. A revision whose
 * read was issued therefore settles away from "loading".
 */
export function useRevisionPreview(
  scope: RevisionPreviewScope | null | undefined,
): RevisionPreviewController {
  const [openRevisionId, setOpenRevisionId] = useState<string | null>(null);
  const [states, setStates] = useState<Record<string, RevisionPreviewState>>({});
  const scopeKey =
    scope === null || scope === undefined ? null : `${scope.projectId}:${scope.documentId}`;
  const [resolvedScopeKey, setResolvedScopeKey] = useState(scopeKey);
  const requestSequenceRef = useRef(new Map<string, number>());
  if (resolvedScopeKey !== scopeKey) {
    // React's documented reset-when-a-prop-changes pattern: adjusting during
    // render drops the previous document's cache and open row without an
    // effect, so no stale preview can paint for the new scope. The sequence
    // map is left alone here; writing it during render would leak across a
    // discarded replay. A late response no-ops because this reset removes
    // the loading row it would have published into.
    setResolvedScopeKey(scopeKey);
    setOpenRevisionId(null);
    setStates({});
  }
  const scopeRef = useRef(scope);
  useEffect(() => {
    // Latest-value ref for the event callbacks; synced after commit so no
    // render work mutates it (React may replay discarded renders).
    scopeRef.current = scope;
  }, [scope]);

  const load = useCallback((revisionId: string) => {
    const currentScope = scopeRef.current;
    if (!currentScope) return;
    const sequence = (requestSequenceRef.current.get(revisionId) ?? 0) + 1;
    requestSequenceRef.current.set(revisionId, sequence);
    /**
     * Applies one settled read. Fails closed (returns the previous map) when
     * the row is no longer the loading owner of this sequence: a document
     * switch has cleared it, or a newer read for the same revision has taken
     * the sequence. The check lives inside the updater because a resolved
     * promise can run before the scope effect, and a check outside setState
     * can pass against a cache the reset has already replaced.
     */
    const publish = (next: RevisionPreviewState) => {
      setStates((current) => {
        if (current[revisionId]?.status !== "loading") return current;
        if (requestSequenceRef.current.get(revisionId) !== sequence) return current;
        return { ...current, [revisionId]: next };
      });
    };
    setStates((current) => ({ ...current, [revisionId]: { status: "loading" } }));
    void api
      .revision(currentScope.projectId, currentScope.documentId, revisionId)
      .then((revision) => {
        publish({ status: "loaded", revision });
      })
      .catch((reason: unknown) => {
        publish({ status: "error", message: previewFailureMessage(reason) });
      });
  }, []);

  const toggle = useCallback(
    (revisionId: string) => {
      setOpenRevisionId((current) => (current === revisionId ? null : revisionId));
      const cached = states[revisionId];
      if (cached?.status === "loaded" || cached?.status === "loading") return;
      load(revisionId);
    },
    [load, states],
  );

  const retry = useCallback((revisionId: string) => load(revisionId), [load]);

  return {
    isOpen: (revisionId) => openRevisionId === revisionId,
    stateFor: (revisionId) => states[revisionId] ?? IDLE_STATE,
    toggle,
    retry,
  };
}
