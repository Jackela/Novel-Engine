import { Layers } from "lucide-react";
import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";

import type { NavigatorVolumeCommands } from "./StudioNavigatorVolumeHeader";

interface StudioNavigatorVolumeCreateProps {
  commands: NavigatorVolumeCommands;
  isMutationBusy: boolean;
}

/**
 * The chapter group's "add volume" affordance: a trigger that expands into an
 * inline title field (Enter submits, Escape cancels, focus returns to the
 * trigger). Server refusals — empty or duplicate titles — stay readable
 * inside the open form as its inline alert; the form closes once a submitted
 * create settles without a refusal.
 */
export function StudioNavigatorVolumeCreate({
  commands,
  isMutationBusy,
}: StudioNavigatorVolumeCreateProps) {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const fieldRef = useRef<HTMLInputElement | null>(null);
  const refocusTriggerRef = useRef(false);

  const busy = commands.isCreatingVolume;
  const error = commands.createError;

  useEffect(() => {
    if (isOpen) fieldRef.current?.focus();
  }, [isOpen]);
  // The trigger unmounts while the form is open, so focus returns only after
  // the closing render remounts it.
  useEffect(() => {
    if (!isOpen && refocusTriggerRef.current) {
      refocusTriggerRef.current = false;
      triggerRef.current?.focus();
    }
  }, [isOpen]);
  // A submitted create closes as soon as its command settles without a
  // refusal: adjusting state during render (React's documented
  // reset-when-props-change pattern) closes the form one render earlier than
  // an effect could, so no stale frame shows the settled submission.
  if (isOpen && submitted && !busy && error === null) {
    setSubmitted(false);
    setIsOpen(false);
    setTitle("");
  }

  const close = () => {
    refocusTriggerRef.current = true;
    setIsOpen(false);
    setTitle("");
  };
  const onKeyDown = (event: KeyboardEvent<HTMLFormElement>) => {
    if (event.key === "Escape") {
      event.stopPropagation();
      close();
    }
  };
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = title.trim();
    if (trimmed === "" || isMutationBusy) return;
    setSubmitted(true);
    // The trigger only remounts after the closing render; the ref flag tells
    // the focus effect below that this close is one that should return focus.
    refocusTriggerRef.current = true;
    void commands.onAddVolume(trimmed);
  };

  if (!isOpen) {
    return (
      <div className="volume-group__create">
        <button
          aria-label={t("navigator.volume.add")}
          disabled={isMutationBusy}
          onClick={() => setIsOpen(true)}
          ref={triggerRef}
          title={t("navigator.volume.add")}
          type="button"
        >
          <Layers aria-hidden="true" />
          {t("navigator.volume.add")}
        </button>
      </div>
    );
  }

  return (
    <div className="volume-group__create">
      <form
        aria-label={t("navigator.volume.form")}
        className="volume-group__form"
        onKeyDown={onKeyDown}
        onSubmit={submit}
      >
        <input
          aria-label={t("navigator.volume.titleField")}
          disabled={busy}
          onChange={(event) => setTitle(event.target.value)}
          placeholder={t("navigator.volume.titleField")}
          ref={fieldRef}
          type="text"
          value={title}
        />
        <button
          aria-busy={busy || undefined}
          aria-label={busy ? t("navigator.volume.creating") : t("navigator.volume.create")}
          disabled={isMutationBusy || title.trim() === ""}
          type="submit"
        >
          {busy ? t("navigator.volume.creating") : t("navigator.volume.create")}
        </button>
        <button
          aria-label={t("navigator.volume.cancelAdd")}
          disabled={busy}
          onClick={close}
          type="button"
        >
          {t("navigator.volume.cancel")}
        </button>
        {error !== null ? (
          <p aria-live="assertive" className="volume-group__error" role="alert">
            {error}
          </p>
        ) : null}
      </form>
    </div>
  );
}
