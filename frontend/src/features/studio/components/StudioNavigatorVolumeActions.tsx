import { ArrowDown, ArrowUp, Loader2, Pencil, Trash2 } from "lucide-react";
import { type RefObject, useRef } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";

import type { RunCommand } from "../hooks/useVolumeRename";

interface StudioNavigatorVolumeActionsProps {
  readonly deleteButtonRef: RefObject<HTMLButtonElement | null>;
  /** This volume's own in-flight delete, for the trigger's busy state. */
  readonly deletingThis: boolean;
  readonly index: number;
  readonly isMutationBusy: boolean;
  readonly movingDown: boolean;
  readonly movingUp: boolean;
  /** Opens the irreversible delete confirmation for this volume. */
  readonly onDeleteClick: () => void;
  /** Moves this volume one step; the caller owns the command identity. */
  readonly onMove: (direction: -1 | 1) => void | Promise<void>;
  /** Opens the inline rename form for this volume. */
  readonly onRename: () => void;
  readonly renameButtonRef: RefObject<HTMLButtonElement | null>;
  readonly runCommand: RunCommand;
  readonly volumeCount: number;
  readonly volumeTitle: string;
}

/**
 * One volume's management controls: reorder up/down (the navigator's
 * document reorder pattern, not a second drag system), the inline
 * rename trigger, and the irreversible delete trigger. Every command
 * runs through the shared focus restoration, so focus returns to the
 * semantically opposite trigger when the exact one cannot survive
 * the command — up moves restore to the down trigger and vice versa.
 */
export function StudioNavigatorVolumeActions({
  deleteButtonRef,
  deletingThis,
  index,
  isMutationBusy,
  movingDown,
  movingUp,
  onDeleteClick,
  onMove,
  onRename,
  renameButtonRef,
  runCommand,
  volumeCount,
  volumeTitle,
}: StudioNavigatorVolumeActionsProps) {
  const { t } = useTranslation();
  const upButtonRef = useRef<HTMLButtonElement | null>(null);
  const downButtonRef = useRef<HTMLButtonElement | null>(null);

  return (
    <span className="volume-group__actions">
      <button
        aria-busy={movingUp || undefined}
        aria-label={
          movingUp
            ? t("navigator.volume.movingUp", { title: volumeTitle })
            : t("navigator.volume.moveUp", { title: volumeTitle })
        }
        disabled={isMutationBusy || index === 0}
        onClick={(event) => {
          void runCommand(
            event.currentTarget,
            () => onMove(-1),
            () => downButtonRef.current,
          );
        }}
        ref={upButtonRef}
        title={movingUp ? t("navigator.volume.movingUpTitle") : t("navigator.volume.moveUpTitle")}
        type="button"
      >
        <ArrowUp aria-hidden="true" />
      </button>
      <button
        aria-busy={movingDown || undefined}
        aria-label={
          movingDown
            ? t("navigator.volume.movingDown", { title: volumeTitle })
            : t("navigator.volume.moveDown", { title: volumeTitle })
        }
        disabled={isMutationBusy || index === volumeCount - 1}
        onClick={(event) => {
          void runCommand(
            event.currentTarget,
            () => onMove(1),
            () => upButtonRef.current,
          );
        }}
        ref={downButtonRef}
        title={
          movingDown ? t("navigator.volume.movingDownTitle") : t("navigator.volume.moveDownTitle")
        }
        type="button"
      >
        <ArrowDown aria-hidden="true" />
      </button>
      <button
        aria-label={t("navigator.volume.rename", { title: volumeTitle })}
        disabled={isMutationBusy}
        onClick={onRename}
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
            ? t("navigator.volume.deleting", { title: volumeTitle })
            : t("navigator.volume.delete", { title: volumeTitle })
        }
        disabled={isMutationBusy}
        onClick={onDeleteClick}
        ref={deleteButtonRef}
        title={
          deletingThis ? t("navigator.volume.deletingTitle") : t("navigator.volume.deleteTitle")
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
  );
}
