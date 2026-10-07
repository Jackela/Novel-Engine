import { useRef, useState } from "react";

import type { Volume } from "@/app/types/studio";

import {
  type CommandFocusFallback,
  useCommandFocusRestoration,
} from "../hooks/useCommandFocusRestoration";
import { type RunCommand, useVolumeRename } from "../hooks/useVolumeRename";
import { StudioNavigatorVolumeActions } from "./StudioNavigatorVolumeActions";
import { StudioNavigatorVolumeDeleteConfirm } from "./StudioNavigatorVolumeDeleteConfirm";
import { StudioNavigatorVolumeRenameForm } from "./StudioNavigatorVolumeRenameForm";

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

/**
 * One volume's header cluster: reorder up/down (the navigator's
 * document reorder pattern, not a second drag system), inline rename,
 * and the irreversible delete behind a confirmation that names the
 * volume and its chapter merge. Escape cancels either surface; focus
 * moves deliberately between trigger and confirmation and returns
 * after the command settles. Delete refusals — notably the server's
 * at-least-one-volume guard — render inside the open confirmation;
 * reorder refusals render under the header.
 */
export function StudioNavigatorVolumeHeader({
  volume,
  index,
  volumeCount,
  commands,
  isMutationBusy,
  focusFallback,
}: StudioNavigatorVolumeHeaderProps) {
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false);
  const deleteButtonRef = useRef<HTMLButtonElement | null>(null);
  const runCommand: RunCommand = useCommandFocusRestoration(isMutationBusy);

  const renamingThis = commands !== null && commands.renamingVolume?.volumeId === volume.id;
  const deletingThis = commands !== null && commands.deletingVolume?.volumeId === volume.id;
  const movingThis = commands !== null && commands.movingVolume?.volumeId === volume.id;
  const movingUp = movingThis && commands.movingVolume?.direction === -1;
  const movingDown = movingThis && commands.movingVolume?.direction === 1;
  const renameError = commands?.renameErrorFor(volume.id) ?? null;
  const deleteError = commands?.deleteErrorFor(volume.id) ?? null;
  const moveError = commands?.moveErrorFor(volume.id) ?? null;

  const {
    cancelRename,
    isRenaming,
    onRenameKeyDown,
    openRename,
    renameButtonRef,
    renameFieldRef,
    saveButtonRef,
    setTitleDraft,
    submitRename,
    titleDraft,
  } = useVolumeRename({
    isMutationBusy,
    onRenameVolume: commands !== null ? (title) => commands.onRenameVolume(volume.id, title) : null,
    renamingThis,
    renameError,
    runCommand,
    volumeTitle: volume.title,
  });

  const cancelDelete = () => {
    setIsConfirmingDelete(false);
    deleteButtonRef.current?.focus();
  };

  return (
    <div className="volume-group__head">
      <div className="volume-group__head-row">
        <p className="studio-nav__volume-header">{volume.title}</p>
        {commands !== null ? (
          <StudioNavigatorVolumeActions
            deleteButtonRef={deleteButtonRef}
            deletingThis={deletingThis}
            index={index}
            isMutationBusy={isMutationBusy}
            movingDown={movingDown}
            movingUp={movingUp}
            onDeleteClick={() => setIsConfirmingDelete(true)}
            onMove={(direction) => commands.onMoveVolume(volume.id, direction)}
            onRename={openRename}
            renameButtonRef={renameButtonRef}
            runCommand={runCommand}
            volumeCount={volumeCount}
            volumeTitle={volume.title}
          />
        ) : null}
      </div>
      {isRenaming ? (
        <StudioNavigatorVolumeRenameForm
          isMutationBusy={isMutationBusy}
          isRenamingThis={renamingThis}
          renameError={renameError}
          renameFieldRef={renameFieldRef}
          saveButtonRef={saveButtonRef}
          titleDraft={titleDraft}
          volumeTitle={volume.title}
          onCancel={cancelRename}
          onKeyDown={onRenameKeyDown}
          onSubmit={submitRename}
          onTitleChange={setTitleDraft}
        />
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
