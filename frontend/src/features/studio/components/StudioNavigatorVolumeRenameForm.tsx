import type { FormEvent, KeyboardEvent, RefObject } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";

interface StudioNavigatorVolumeRenameFormProps {
  readonly isMutationBusy: boolean;
  /** This volume's own in-flight rename, for the save control's busy state. */
  readonly isRenamingThis: boolean;
  /** The server's rename refusal for this volume; keeps the form open. */
  readonly renameError: string | null;
  readonly renameFieldRef: RefObject<HTMLInputElement | null>;
  readonly saveButtonRef: RefObject<HTMLButtonElement | null>;
  readonly titleDraft: string;
  readonly volumeTitle: string;
  /** Cancels the rename and returns focus to the rename trigger. */
  readonly onCancel: () => void;
  readonly onKeyDown: (event: KeyboardEvent<HTMLFormElement>) => void;
  readonly onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  readonly onTitleChange: (value: string) => void;
}

/**
 * The inline rename surface for one volume: the title field prefilled
 * with the current title, save and cancel controls, and the server's
 * rename refusal rendered inline as the form's alert. Escape cancels
 * through the form's key handler; the field takes focus on open.
 */
export function StudioNavigatorVolumeRenameForm({
  isMutationBusy,
  isRenamingThis,
  renameError,
  renameFieldRef,
  saveButtonRef,
  titleDraft,
  volumeTitle,
  onCancel,
  onKeyDown,
  onSubmit,
  onTitleChange,
}: StudioNavigatorVolumeRenameFormProps) {
  const { t } = useTranslation();

  return (
    <form
      aria-label={t("navigator.volume.renameForm", { title: volumeTitle })}
      className="volume-group__form"
      onKeyDown={onKeyDown}
      onSubmit={onSubmit}
    >
      <input
        aria-label={t("navigator.volume.renameField", { title: volumeTitle })}
        disabled={isMutationBusy}
        onChange={(event) => onTitleChange(event.target.value)}
        ref={renameFieldRef}
        type="text"
        value={titleDraft}
      />
      <button
        aria-busy={isRenamingThis || undefined}
        aria-label={
          isRenamingThis
            ? t("navigator.volume.savingRename", { title: volumeTitle })
            : t("navigator.volume.saveRename", { title: volumeTitle })
        }
        disabled={isMutationBusy || titleDraft.trim() === ""}
        ref={saveButtonRef}
        type="submit"
      >
        {isRenamingThis
          ? t("navigator.volume.savingRename", { title: volumeTitle })
          : t("navigator.volume.saveRename", { title: volumeTitle })}
      </button>
      <button
        aria-label={t("navigator.volume.cancelRename", { title: volumeTitle })}
        disabled={isRenamingThis}
        onClick={onCancel}
        type="button"
      >
        {t("navigator.volume.cancel")}
      </button>
      {renameError !== null ? (
        <p aria-live="assertive" className="volume-group__error" role="alert">
          {renameError}
        </p>
      ) : null}
    </form>
  );
}
