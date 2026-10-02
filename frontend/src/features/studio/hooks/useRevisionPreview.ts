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
 * cache and the open row. Stale responses are discarded by request sequence,
 * so a slow ancestor read can never overwrite a newer scope's state.
 */
export function useRevisionPreview(
  scope: RevisionPreviewScope | null | undefined,
): RevisionPreviewController {
  const [openRevisionId, setOpenRevisionId] = useState<string | null>(null);
  const [states, setStates] = useState<Record<string, RevisionPreviewState>>({});
  const scopeKey =
    scope === null || scope === undefined ? null : `${scope.projectId}:${scope.documentId}`;
  const [resolvedScopeKey, setResolvedScopeKey] = useState(scopeKey);
  if (resolvedScopeKey !== scopeKey) {
    // React's documented reset-when-a-prop-changes pattern: adjusting during
    // render drops the previous document's cache and open row without an
    // effect, so no stale preview can paint for the new scope.
    setResolvedScopeKey(scopeKey);
    setOpenRevisionId(null);
    setStates({});
  }
  const requestRef = useRef(0);
  const scopeRef = useRef(scope);
  useEffect(() => {
    // Latest-value ref for the event callbacks; synced after commit so no
    // render work mutates it (React may replay discarded renders).
    scopeRef.current = scope;
  }, [scope]);

  const load = useCallback((revisionId: string) => {
    const currentScope = scopeRef.current;
    if (!currentScope) return;
    const request = requestRef.current + 1;
    requestRef.current = request;
    setStates((current) => ({ ...current, [revisionId]: { status: "loading" } }));
    void api
      .revision(currentScope.projectId, currentScope.documentId, revisionId)
      .then((revision) => {
        if (requestRef.current !== request) return;
        setStates((current) => ({ ...current, [revisionId]: { status: "loaded", revision } }));
      })
      .catch((reason: unknown) => {
        if (requestRef.current !== request) return;
        setStates((current) => ({
          ...current,
          [revisionId]: {
            status: "error",
            message: previewFailureMessage(reason),
          },
        }));
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
