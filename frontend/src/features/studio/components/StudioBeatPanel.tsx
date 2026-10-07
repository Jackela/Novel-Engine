import { useCallback, useLayoutEffect, useRef } from "react";

import { useBeatCandidates } from "../hooks/useBeatCandidates";
import { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";
import { StudioBeatEntryForm } from "./StudioBeatEntryForm";

interface StudioBeatPanelProps {
  projectId: string;
  documentId: string;
  beatRef: string | null;
  attemptedTitle?: string | null;
  isSaving?: boolean;
  error?: string | null;
  onLink: (beat: string | null) => Promise<void>;
}

/**
 * The chapter beat-association command surface (#466, DR-043): choose the
 * chapter's linked outline beat from the outline's own catalog, or clear the
 * association. The selection submits the requested title; `beatRef` is the
 * stored-reference authority patched from the successful command's normalized
 * requested value — never from the independently resolved beat display.
 */
export function StudioBeatPanel({
  projectId,
  documentId,
  beatRef,
  attemptedTitle = null,
  isSaving = false,
  error = null,
  onLink,
}: StudioBeatPanelProps) {
  const selectRef = useRef<HTMLSelectElement | null>(null);
  const linkButtonRef = useRef<HTMLButtonElement | null>(null);
  const activeDocumentIdRef = useRef(documentId);
  const runWithFocusRestoration = useCommandFocusRestoration(isSaving);
  const {
    candidates,
    outline,
    isLoading,
    error: candidatesError,
    refresh,
  } = useBeatCandidates(projectId, documentId);

  useLayoutEffect(() => {
    activeDocumentIdRef.current = documentId;
  }, [documentId]);

  const linkWithFocusRestoration = useCallback(
    (trigger: HTMLButtonElement, beat: string | null) => {
      const originDocumentId = documentId;
      void runWithFocusRestoration(
        trigger,
        () => onLink(beat),
        // A success keeps the initiating command disabled (`requested ===
        // beatRef`, or Clear with no reference left), so the catalog select is
        // the semantic landing zone — but only for the same document.
        () => (activeDocumentIdRef.current === originDocumentId ? selectRef.current : null),
      );
    },
    [documentId, onLink, runWithFocusRestoration],
  );

  // The keyed form resets local selection at the document boundary, while the
  // persistent owner above can resolve a returning document's semantic target.
  return (
    <StudioBeatEntryForm
      key={documentId}
      beatRef={beatRef}
      attemptedTitle={attemptedTitle}
      isSaving={isSaving}
      error={error}
      candidates={candidates}
      outline={outline}
      isLoadingCandidates={isLoading}
      candidatesError={candidatesError}
      onRefreshCandidates={refresh}
      onLinkCommand={linkWithFocusRestoration}
      selectRef={selectRef}
      linkButtonRef={linkButtonRef}
    />
  );
}
