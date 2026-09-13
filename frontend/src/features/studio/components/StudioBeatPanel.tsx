import type { FormEvent, MouseEvent, RefObject } from "react";
import { useCallback, useLayoutEffect, useRef, useState } from "react";

import { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";

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
  const inputRef = useRef<HTMLInputElement | null>(null);
  const linkButtonRef = useRef<HTMLButtonElement | null>(null);
  const activeDocumentIdRef = useRef(documentId);
  const runWithFocusRestoration = useCommandFocusRestoration(isSaving);

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
        // beatRef`, or Clear with no reference left), so the beat input is
        // the semantic landing zone — but only for the same document.
        () => (activeDocumentIdRef.current === originDocumentId ? inputRef.current : null),
      );
    },
    [documentId, onLink, runWithFocusRestoration],
  );

  // The keyed form resets local title at the document boundary, while the
  // persistent owner above can resolve a returning document's semantic target.
  return (
    <BeatEntryForm
      key={documentId}
      beatRef={beatRef}
      attemptedTitle={attemptedTitle}
      isSaving={isSaving}
      error={error}
      onLinkCommand={linkWithFocusRestoration}
      inputRef={inputRef}
      linkButtonRef={linkButtonRef}
    />
  );
}

interface BeatEntryFormProps {
  readonly beatRef: string | null;
  readonly attemptedTitle: string | null;
  readonly isSaving: boolean;
  readonly error: string | null;
  readonly onLinkCommand: (trigger: HTMLButtonElement, beat: string | null) => void;
  readonly inputRef: RefObject<HTMLInputElement | null>;
  readonly linkButtonRef: RefObject<HTMLButtonElement | null>;
}

function BeatEntryForm({
  beatRef,
  attemptedTitle,
  isSaving,
  error,
  onLinkCommand,
  inputRef,
  linkButtonRef,
}: BeatEntryFormProps) {
  const [title, setTitle] = useState(attemptedTitle ?? beatRef ?? "");
  const requested = title.trim();

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
    <form aria-label="Chapter beat" className="studio-beat" onSubmit={handleSubmit}>
      <label className="studio-inspector__settings-field">
        <span>Beat</span>
        <input
          aria-label="Beat title"
          disabled={isSaving}
          onChange={(event) => setTitle(event.target.value)}
          ref={inputRef}
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
          ref={linkButtonRef}
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
        <p aria-live="assertive" className="studio-beat__error" role="alert">
          {error}
        </p>
      ) : null}
      <p aria-live="polite" className="sr-only">
        {isSaving ? "Saving chapter beat." : ""}
      </p>
    </form>
  );
}
