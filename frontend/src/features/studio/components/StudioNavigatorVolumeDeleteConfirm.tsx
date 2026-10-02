import { type KeyboardEvent, useEffect, useRef } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";

import {
  type CommandFocusFallback,
  useCommandFocusRestoration,
} from "../hooks/useCommandFocusRestoration";

interface StudioNavigatorVolumeDeleteConfirmProps {
  volumeTitle: string;
  isMutationBusy: boolean;
  isDeleting: boolean;
  error: string | null;
  onCancel: () => void;
  onConfirm: () => void | Promise<void>;
  /** A surviving focus target when this volume disappears after deletion. */
  focusFallback: CommandFocusFallback;
}

/**
 * The delete confirmation strip for one volume: it names the volume and its
 * chapter merge, focuses its confirm control on open, cancels on Escape, and
 * renders the server's refusal — notably the at-least-one-volume guard —
 * inside the open strip.
 */
export function StudioNavigatorVolumeDeleteConfirm({
  volumeTitle,
  isMutationBusy,
  isDeleting,
  error,
  onCancel,
  onConfirm,
  focusFallback,
}: StudioNavigatorVolumeDeleteConfirmProps) {
  const { t } = useTranslation();
  const confirmButtonRef = useRef<HTMLButtonElement | null>(null);
  const runCommand = useCommandFocusRestoration(isMutationBusy);

  useEffect(() => {
    confirmButtonRef.current?.focus();
  }, []);

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") {
      event.stopPropagation();
      onCancel();
    }
  };

  return (
    // biome-ignore lint/a11y/useSemanticElements: this confirmation strip is not a form control group; <fieldset> would misrepresent semantics and drag in default fieldset styling.
    <div
      aria-label={t("navigator.volume.confirmHeading", { title: volumeTitle })}
      className="volume-group__confirm"
      onKeyDown={onKeyDown}
      role="group"
    >
      <p>{t("navigator.volume.confirmBody", { title: volumeTitle })}</p>
      <span className="volume-group__confirm-actions">
        <button
          aria-busy={isDeleting || undefined}
          aria-label={
            isDeleting
              ? t("navigator.volume.deleting", { title: volumeTitle })
              : t("navigator.volume.confirmDelete", { title: volumeTitle })
          }
          disabled={isMutationBusy}
          onClick={(event) => {
            void runCommand(event.currentTarget, onConfirm, focusFallback);
          }}
          ref={confirmButtonRef}
          type="button"
        >
          {isDeleting
            ? t("navigator.volume.confirmingAction")
            : t("navigator.volume.confirmAction")}
        </button>
        <button
          aria-label={t("navigator.volume.cancelDelete", { title: volumeTitle })}
          disabled={isDeleting}
          onClick={onCancel}
          type="button"
        >
          {t("navigator.volume.cancel")}
        </button>
      </span>
      {error !== null ? (
        <p aria-live="assertive" className="volume-group__error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
