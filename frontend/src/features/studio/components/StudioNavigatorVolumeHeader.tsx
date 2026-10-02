import { ArrowDown, ArrowUp, Loader2, Pencil, Trash2 } from "lucide-react";
import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";
import type { Volume } from "@/app/types/studio";

import {
  type CommandFocusFallback,
  type CommandTriggerElement,
  useCommandFocusRestoration,
} from "../hooks/useCommandFocusRestoration";
import { StudioNavigatorVolumeDeleteConfirm } from "./StudioNavigatorVolumeDeleteConfirm";

/** Navigator volume-management commands with their exact pending/error identities. */
export interface NavigatorVolumeCommands {
  readonly onAddVolume: (title: string) => void | Promise<void>;
  readonly onRenameVolume: (volumeId: string, title: string) => void | Promise<void>;
  readonly onDeleteVolume: (volumeId: string) => void | Promise<void>;
  readonly onMoveVolume: (volumeId: string, direction: -1 | 1) => void | Promise<void>;
  readonly isCreatingVolume: boolean;
  readonly createError: string | null;
  readonly renamingVolume: { readonly volumeId: string } | null;
  readonly renameErrorFor: (volumeId: string) => string | null;
  readonly deletingVolume: { readonly volumeId: string } | null;
  readonly deleteErrorFor: (volumeId: string) => string | null;
  readonly movingVolume: { readonly volumeId: string; readonly direction: -1 | 1 } | null;
  readonly moveErrorFor: (volumeId: string) => string | null;
}

interface StudioNavigatorVolumeHeaderProps {
  volume: Volume;
  index: number;
  volumeCount: number;
  /** Absent renders the title alone (pre-management tree). */
  commands: NavigatorVolumeCommands | null;
  isMutationBusy: boolean;
  /** A surviving focus target when this volume disappears after deletion. */
  focusFallback: CommandFocusFallback;
}

type RunCommand = (
  target: CommandTriggerElement,
  command: () => void | Promise<void>,
  fallback?: CommandFocusFallback | null,
) => void | Promise<void>;

/**
 * One volume's header cluster: reorder up/down (the navigator's document
 * reorder pattern, not a second drag system), inline rename, and the
 * irreversible delete behind a confirmation that names the volume and its
 * chapter merge. Escape cancels either surface; focus moves deliberately
 * between trigger and confirmation and returns after the command settles.
 * Delete refusals — notably the server's at-least-one-volume guard — render
 * inside the open confirmation; reorder refusals render under the header.
 */
export function StudioNavigatorVolumeHeader({
  volume,
  index,
  volumeCount,
  commands,
  isMutationBusy,
  focusFallback,
}: StudioNavigatorVolumeHeaderProps) {
  const { t } = useTranslation();
  const [isRenaming, setIsRenaming] = useState(false);
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false);
  const [titleDraft, setTitleDraft] = useState("");
  const renameButtonRef = useRef<HTMLButtonElement | null>(null);
  const renameFieldRef = useRef<HTMLInputElement | null>(null);
  const saveButtonRef = useRef<HTMLButtonElement | null>(null);
  const deleteButtonRef = useRef<HTMLButtonElement | null>(null);
  const upButtonRef = useRef<HTMLButtonElement | null>(null);
  const downButtonRef = useRef<HTMLButtonElement | null>(null);
  const [renameSubmitted, setRenameSubmitted] = useState(false);
  const renameFocusPendingRef = useRef(false);
  const runCommand: RunCommand = useCommandFocusRestoration(isMutationBusy);

  const renamingThis = commands !== null && commands.renamingVolume?.volumeId === volume.id;
  const deletingThis = commands !== null && commands.deletingVolume?.volumeId === volume.id;
  const movingThis = commands !== null && commands.movingVolume?.volumeId === volume.id;
  const movingUp = movingThis && commands.movingVolume?.direction === -1;
  const movingDown = movingThis && commands.movingVolume?.direction === 1;
  const renameError = commands?.renameErrorFor(volume.id) ?? null;
  const deleteError = commands?.deleteErrorFor(volume.id) ?? null;
  const moveError = commands?.moveErrorFor(volume.id) ?? null;

  // Deliberate focus movement: opening rename targets its field; the
  // confirmation component focuses its own confirm control on mount.
  useEffect(() => {
    if (isRenaming) renameFieldRef.current?.focus();
  }, [isRenaming]);

  // A submitted rename closes as soon as its command settles without a
  // refusal: adjusting state during render (React's documented
  // reset-when-props-change pattern) closes it one render earlier than an
  // effect could.
  if (isRenaming && renameSubmitted && !renamingThis && renameError === null) {
    setRenameSubmitted(false);
    setIsRenaming(false);
  }

  // The save control unmounts with the form, so the persistent trigger
  // reclaims focus after the closing render instead of dropping it to the
  // body.
  useEffect(() => {
    if (!isRenaming && renameFocusPendingRef.current) {
      renameFocusPendingRef.current = false;
      renameButtonRef.current?.focus();
    }
  }, [isRenaming]);

  const openRename = () => {
    setTitleDraft(volume.title);
    setRenameSubmitted(false);
    setIsRenaming(true);
  };
  const cancelRename = () => {
    setIsRenaming(false);
    renameButtonRef.current?.focus();
  };
  const onRenameKeyDown = (event: KeyboardEvent<HTMLFormElement>) => {
    if (event.key === "Escape") {
      event.stopPropagation();
      cancelRename();
    }
  };
  const submitRename = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const title = titleDraft.trim();
    const saveButton = saveButtonRef.current;
    if (!commands || title === "" || isMutationBusy || saveButton === null) return;
    setRenameSubmitted(true);
    renameFocusPendingRef.current = true;
    void runCommand(
      saveButton,
      () => commands.onRenameVolume(volume.id, title),
      () => renameButtonRef.current,
    );
  };

  const cancelDelete = () => {
    setIsConfirmingDelete(false);
    deleteButtonRef.current?.focus();
  };

  return (
    <div className="volume-group__head">
      <div className="volume-group__head-row">
        <p className="studio-nav__volume-header">{volume.title}</p>
        {commands !== null ? (
          <span className="volume-group__actions">
            <button
              aria-busy={movingUp || undefined}
              aria-label={
                movingUp
                  ? t("navigator.volume.movingUp", { title: volume.title })
                  : t("navigator.volume.moveUp", { title: volume.title })
              }
              disabled={isMutationBusy || index === 0}
              onClick={(event) => {
                void runCommand(
                  event.currentTarget,
                  () => commands.onMoveVolume(volume.id, -1),
                  () => downButtonRef.current,
                );
              }}
              ref={upButtonRef}
              title={
                movingUp ? t("navigator.volume.movingUpTitle") : t("navigator.volume.moveUpTitle")
              }
              type="button"
            >
              <ArrowUp aria-hidden="true" />
            </button>
            <button
              aria-busy={movingDown || undefined}
              aria-label={
                movingDown
                  ? t("navigator.volume.movingDown", { title: volume.title })
                  : t("navigator.volume.moveDown", { title: volume.title })
              }
              disabled={isMutationBusy || index === volumeCount - 1}
              onClick={(event) => {
                void runCommand(
                  event.currentTarget,
                  () => commands.onMoveVolume(volume.id, 1),
                  () => upButtonRef.current,
                );
              }}
              ref={downButtonRef}
              title={
                movingDown
                  ? t("navigator.volume.movingDownTitle")
                  : t("navigator.volume.moveDownTitle")
              }
              type="button"
            >
              <ArrowDown aria-hidden="true" />
            </button>
            <button
              aria-label={t("navigator.volume.rename", { title: volume.title })}
              disabled={isMutationBusy}
              onClick={openRename}
              ref={renameButtonRef}
              title={t("navigator.volume.renameTitle")}
              type="button"
            >
              <Pencil aria-hidden="true" />
            </button>
            <button
              aria-busy={deletingThis || undefined}
              aria-label={
                deletingThis
                  ? t("navigator.volume.deleting", { title: volume.title })
                  : t("navigator.volume.delete", { title: volume.title })
              }
              disabled={isMutationBusy}
              onClick={() => setIsConfirmingDelete(true)}
              ref={deleteButtonRef}
              title={
                deletingThis
                  ? t("navigator.volume.deletingTitle")
                  : t("navigator.volume.deleteTitle")
              }
              type="button"
            >
              {deletingThis ? (
                <Loader2 aria-hidden="true" className="ui-spin" />
              ) : (
                <Trash2 aria-hidden="true" />
              )}
            </button>
          </span>
        ) : null}
      </div>
      {isRenaming ? (
        <form
          aria-label={t("navigator.volume.renameForm", { title: volume.title })}
          className="volume-group__form"
          onKeyDown={onRenameKeyDown}
          onSubmit={submitRename}
        >
          <input
            aria-label={t("navigator.volume.renameField", { title: volume.title })}
            disabled={isMutationBusy}
            onChange={(event) => setTitleDraft(event.target.value)}
            ref={renameFieldRef}
            type="text"
            value={titleDraft}
          />
          <button
            aria-busy={renamingThis || undefined}
            aria-label={
              renamingThis
                ? t("navigator.volume.savingRename", { title: volume.title })
                : t("navigator.volume.saveRename", { title: volume.title })
            }
            disabled={isMutationBusy || titleDraft.trim() === ""}
            ref={saveButtonRef}
            type="submit"
          >
            {renamingThis
              ? t("navigator.volume.savingRename", { title: volume.title })
              : t("navigator.volume.saveRename", { title: volume.title })}
          </button>
          <button
            aria-label={t("navigator.volume.cancelRename", { title: volume.title })}
            disabled={renamingThis}
            onClick={cancelRename}
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
      ) : null}
      {isConfirmingDelete && commands !== null ? (
        <StudioNavigatorVolumeDeleteConfirm
          error={deleteError}
          focusFallback={focusFallback}
          isDeleting={deletingThis}
          isMutationBusy={isMutationBusy}
          onCancel={cancelDelete}
          onConfirm={() => commands.onDeleteVolume(volume.id)}
          volumeTitle={volume.title}
        />
      ) : null}
      {!isConfirmingDelete && moveError !== null ? (
        <p aria-live="assertive" className="volume-group__error" role="alert">
          {moveError}
        </p>
      ) : null}
    </div>
  );
}
