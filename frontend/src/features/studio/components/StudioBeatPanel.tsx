import type { FormEvent } from "react";
import { useState } from "react";

interface StudioBeatPanelProps {
  documentId: string;
  beatRef: string | null;
  attemptedTitle?: string | null;
  isSaving?: boolean;
  error?: string | null;
  onLink: (beat: string | null) => Promise<void>;
}

/**
 * The chapter beat-association command surface (#466): set the chapter's
 * linked outline beat title, or clear the association. The input submits the
 * requested title; `beatRef` is the stored-reference authority patched from
 * the successful command's normalized requested value — never from the
 * independently resolved beat display.
 */
export function StudioBeatPanel({
  documentId,
  beatRef,
  attemptedTitle = null,
  isSaving = false,
  error = null,
  onLink,
}: StudioBeatPanelProps) {
  return (
    <BeatEntryForm
      key={documentId}
      beatRef={beatRef}
      attemptedTitle={attemptedTitle}
      isSaving={isSaving}
      error={error}
      onLink={onLink}
    />
  );
}

interface BeatEntryFormProps {
  readonly beatRef: string | null;
  readonly attemptedTitle: string | null;
  readonly isSaving: boolean;
  readonly error: string | null;
  readonly onLink: (beat: string | null) => Promise<void>;
}

function BeatEntryForm({ beatRef, attemptedTitle, isSaving, error, onLink }: BeatEntryFormProps) {
  const [title, setTitle] = useState(attemptedTitle ?? beatRef ?? "");
  const requested = title.trim();

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isSaving || requested === "" || requested === beatRef) return;
    void onLink(requested);
  };

  const clearBeat = () => {
    if (isSaving || beatRef === null) return;
    void onLink(null);
  };

  return (
    <form aria-label="Chapter beat" className="studio-beat" onSubmit={handleSubmit}>
      <label className="studio-inspector__settings-field">
        <span>Beat</span>
        <input
          aria-label="Beat title"
          disabled={isSaving}
          onChange={(event) => setTitle(event.target.value)}
          type="text"
          value={title}
        />
      </label>
      <p className="studio-beat__hint">
        Links the chapter to an outline beat by its heading title.
      </p>
      <div className="studio-inspector__actions">
        <button
          aria-busy={isSaving}
          className="ui-command ui-command--primary"
          disabled={isSaving || requested === "" || requested === beatRef}
          type="submit"
        >
          {isSaving ? "Saving…" : "Link beat"}
        </button>
        <button
          className="ui-command"
          disabled={isSaving || beatRef === null}
          onClick={clearBeat}
          type="button"
        >
          Clear
        </button>
      </div>
      {error ? (
        <p aria-live="polite" className="studio-beat__error" role="alert">
          {error}
        </p>
      ) : null}
      <p aria-live="polite" className="sr-only">
        {isSaving ? "Saving chapter beat." : ""}
      </p>
    </form>
  );
}
