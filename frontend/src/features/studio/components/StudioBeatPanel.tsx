import type { FormEvent, MouseEvent, RefObject } from "react";
import { useCallback, useLayoutEffect, useRef, useState } from "react";

import type { BeatCandidate, BeatOutlineAuthority } from "@/app/beatContract";
import { useTranslation } from "@/app/i18n/useTranslation";
import { useBeatCandidates } from "../hooks/useBeatCandidates";
import { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";

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
    <BeatEntryForm
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

/**
 * The options the catalog select offers: the outline's beats in document
 * order, preceded by a still-stored reference the outline no longer holds, so
 * a renamed heading never silently blanks the author's current association.
 */
function selectableTitles(candidates: readonly BeatCandidate[], current: string): string[] {
  const titles = candidates.map((candidate) => candidate.title);
  if (current === "" || titles.includes(current)) {
    return [...new Set(titles)];
  }
  return [current, ...new Set(titles)];
}

interface BeatEntryFormProps {
  readonly beatRef: string | null;
  readonly attemptedTitle: string | null;
  readonly isSaving: boolean;
  readonly error: string | null;
  readonly candidates: readonly BeatCandidate[];
  readonly outline: BeatOutlineAuthority | null;
  readonly isLoadingCandidates: boolean;
  readonly candidatesError: string | null;
  readonly onRefreshCandidates: () => void;
  readonly onLinkCommand: (trigger: HTMLButtonElement, beat: string | null) => void;
  readonly selectRef: RefObject<HTMLSelectElement | null>;
  readonly linkButtonRef: RefObject<HTMLButtonElement | null>;
}

function BeatEntryForm({
  beatRef,
  attemptedTitle,
  isSaving,
  error,
  candidates,
  outline,
  isLoadingCandidates,
  candidatesError,
  onRefreshCandidates,
  onLinkCommand,
  selectRef,
  linkButtonRef,
}: BeatEntryFormProps) {
  const [title, setTitle] = useState(attemptedTitle ?? beatRef ?? "");
  const { t } = useTranslation();
  const requested = title.trim();
  const titles = selectableTitles(candidates, title);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const linkButton = linkButtonRef.current;
    if (linkButton === null || isSaving || requested === "" || requested === beatRef) return;
    onLinkCommand(linkButton, requested);
  };

  const clearBeat = (event: MouseEvent<HTMLButtonElement>) => {
    if (isSaving || beatRef === null) return;
    onLinkCommand(event.currentTarget, null);
  };

  return (
    <form aria-label={t("beat.form.label")} className="studio-beat" onSubmit={handleSubmit}>
      <label className="studio-inspector__settings-field">
        <span>{t("beat.field.label")}</span>
        <select
          aria-label={t("beat.field.title")}
          disabled={isSaving}
          onChange={(event) => setTitle(event.target.value)}
          ref={selectRef}
          value={title}
        >
          <option value="">{t("beat.option.none")}</option>
          {titles.map((candidate) => (
            <option key={candidate} value={candidate}>
              {candidate}
            </option>
          ))}
        </select>
      </label>
      <p className="studio-beat__hint">{t("beat.hint")}</p>
      {outline !== null && outline.outline_count > 1 ? (
        <p className="studio-beat__notice">
          {t("beat.notice.outlineAuthority", {
            count: outline.outline_count,
            title: outline.title,
          })}
        </p>
      ) : null}
      {candidatesError !== null ? (
        <p aria-live="assertive" className="studio-beat__error" role="alert">
          {candidatesError}
        </p>
      ) : null}
      <div className="studio-inspector__actions">
        <button
          aria-busy={isSaving}
          className="ui-command ui-command--primary"
          disabled={isSaving || requested === "" || requested === beatRef}
          ref={linkButtonRef}
          type="submit"
        >
          {isSaving ? t("common.action.saving") : t("beat.action.link")}
        </button>
        <button
          className="ui-command"
          disabled={isSaving || beatRef === null}
          onClick={clearBeat}
          type="button"
        >
          {t("beat.action.clear")}
        </button>
        <button
          aria-label={t("beat.action.refresh")}
          className="ui-command"
          disabled={isSaving || isLoadingCandidates}
          onClick={onRefreshCandidates}
          type="button"
        >
          {isLoadingCandidates ? t("beat.status.loadingCandidates") : t("beat.action.refresh")}
        </button>
      </div>
      {error ? (
        <p aria-live="assertive" className="studio-beat__error" role="alert">
          {error}
        </p>
      ) : null}
      <p aria-live="polite" className="sr-only">
        {isSaving ? t("beat.status.saving") : ""}
      </p>
    </form>
  );
}
