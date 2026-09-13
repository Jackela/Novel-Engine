import { Loader2, Trash2 } from "lucide-react";
import { type KeyboardEvent, useEffect, useRef } from "react";

import type { DocumentSummary, Volume } from "@/app/types/studio";

import type {
  CommandFocusFallback,
  CommandTriggerElement,
  InspectorCommand,
} from "../hooks/useCommandFocusRestoration";

/** Navigator per-row commands and their exact pending/error identities (#481). */
export interface NavigatorRowCommands {
  readonly onDeleteDocument: (documentId: string) => void | Promise<void>;
  readonly onPlaceChapter: (documentId: string, volumeId: string) => void | Promise<void>;
  readonly deletingDocument: { readonly documentId: string } | null;
  readonly placingDocument: { readonly documentId: string; readonly volumeId: string } | null;
  readonly deletionErrorFor: (documentId: string) => string | null;
  readonly placementErrorFor: (documentId: string) => string | null;
}

type RunCommand = (
  target: CommandTriggerElement,
  command: InspectorCommand,
  fallback?: CommandFocusFallback | null,
) => void | Promise<void>;

interface StudioNavigatorRowActionsProps {
  document: DocumentSummary;
  volumes: Volume[] | null;
  isMutationBusy: boolean;
  rowCommands: NavigatorRowCommands | null;
  /** The Navigator owns which row's confirmation is open (#481). */
  isConfirmingDelete: boolean;
  onConfirmingDeleteChange: (open: boolean) => void;
  runCommand: RunCommand;
  /** A surviving neighbor to receive focus when this row disappears. */
  focusFallback: CommandFocusFallback;
}

/**
 * One row's command cluster (#480/#481): the reading-group Move buttons, the
 * chapter's volume placement select (other volumes only — the current one
 * would degrade into a hidden move-to-tail reorder), and the irreversible
 * delete command behind an inline confirmation that names the document and
 * its Draft loss. Escape cancels; focus moves deliberately between trigger
 * and confirmation and returns after the command settles.
 */
export function StudioNavigatorRowActions({
  document,
  volumes,
  isMutationBusy,
  rowCommands,
  isConfirmingDelete,
  onConfirmingDeleteChange,
  runCommand,
  focusFallback,
}: StudioNavigatorRowActionsProps) {
  const deleteButtonRef = useRef<HTMLButtonElement | null>(null);
  const confirmButtonRef = useRef<HTMLButtonElement | null>(null);
  const selectRef = useRef<HTMLSelectElement | null>(null);

  const deletingThis =
    rowCommands !== null && rowCommands.deletingDocument?.documentId === document.id;
  const placing = rowCommands !== null ? rowCommands.placingDocument : null;
  const placingThis = placing !== null && placing.documentId === document.id;
  const deletionError = rowCommands ? rowCommands.deletionErrorFor(document.id) : null;
  const placementError = rowCommands ? rowCommands.placementErrorFor(document.id) : null;

  // Deliberate focus movement: opening the confirmation hands focus to its
  // confirm control so keyboard authors review the warning before firing.
  useEffect(() => {
    if (isConfirmingDelete) confirmButtonRef.current?.focus();
  }, [isConfirmingDelete]);

  const cancelDelete = () => {
    onConfirmingDeleteChange(false);
    deleteButtonRef.current?.focus();
  };
  const onConfirmKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") {
      event.stopPropagation();
      cancelDelete();
    }
  };

  const currentVolumeId = document.volume_id ?? volumes?.[0]?.id ?? null;
  const otherVolumes =
    volumes === null || currentVolumeId === null
      ? []
      : volumes.filter((volume) => volume.id !== currentVolumeId);
  const attemptedVolumeTitle = placingThis
    ? (volumes?.find((volume) => volume.id === placing.volumeId)?.title ?? null)
    : null;

  return (
    <>
      <span className="document-row__actions">
        {document.kind === "chapter" && otherVolumes.length > 0 && rowCommands ? (
          <select
            aria-busy={placingThis || undefined}
            aria-label={
              placingThis && attemptedVolumeTitle !== null
                ? `Placing ${document.title} in ${attemptedVolumeTitle}`
                : `Place ${document.title} in volume`
            }
            disabled={isMutationBusy}
            onChange={(event) => {
              const volumeId = event.target.value;
              if (volumeId === "") return;
              runCommand(
                event.currentTarget,
                () => rowCommands.onPlaceChapter(document.id, volumeId),
                () => selectRef.current,
              );
            }}
            ref={selectRef}
            value=""
          >
            <option disabled value="">
              Move to volume…
            </option>
            {otherVolumes.map((volume) => (
              <option key={volume.id} value={volume.id}>
                {volume.title}
              </option>
            ))}
          </select>
        ) : null}
        <button
          aria-busy={deletingThis || undefined}
          aria-label={`${deletingThis ? "Deleting" : "Delete"} ${document.title}`}
          disabled={isMutationBusy}
          onClick={() => onConfirmingDeleteChange(true)}
          ref={deleteButtonRef}
          title={deletingThis ? "Deleting" : "Delete"}
          type="button"
        >
          {deletingThis ? (
            <Loader2 aria-hidden="true" className="ui-spin" />
          ) : (
            <Trash2 aria-hidden="true" />
          )}
        </button>
      </span>
      {isConfirmingDelete ? (
        // biome-ignore lint/a11y/useSemanticElements: this confirmation strip is not a form control group; <fieldset> would misrepresent semantics and drag in default fieldset styling.
        <div
          aria-label={`Delete ${document.title} confirmation`}
          className="document-row__confirm"
          onKeyDown={onConfirmKeyDown}
          role="group"
        >
          <p>Permanently delete {document.title}? Unsaved changes are lost.</p>
          <span className="document-row__confirm-actions">
            <button
              aria-busy={deletingThis || undefined}
              aria-label={`${deletingThis ? "Deleting" : "Confirm delete"} ${document.title}`}
              disabled={isMutationBusy}
              onClick={(event) => {
                if (!rowCommands) return;
                void runCommand(
                  event.currentTarget,
                  () => rowCommands.onDeleteDocument(document.id),
                  focusFallback,
                );
              }}
              ref={confirmButtonRef}
              type="button"
            >
              {deletingThis ? "Deleting…" : "Delete"}
            </button>
            <button
              aria-label={`Cancel delete ${document.title}`}
              disabled={deletingThis}
              onClick={cancelDelete}
              type="button"
            >
              Cancel
            </button>
          </span>
          {deletionError !== null ? (
            <p aria-live="assertive" className="document-row__error" role="alert">
              {deletionError}
            </p>
          ) : null}
        </div>
      ) : null}
      {!isConfirmingDelete && placementError !== null ? (
        <p aria-live="assertive" className="document-row__error" role="alert">
          {placementError}
        </p>
      ) : null}
    </>
  );
}
