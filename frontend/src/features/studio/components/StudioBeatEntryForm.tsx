import type { FormEvent, MouseEvent, RefObject } from "react";
import { useState } from "react";
import type { BeatCandidate, BeatOutlineAuthority } from "@/app/beatContract";
import { useTranslation } from "@/app/i18n/useTranslation";

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

interface StudioBeatEntryFormProps {
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

export function StudioBeatEntryForm({
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
}: StudioBeatEntryFormProps) {
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
