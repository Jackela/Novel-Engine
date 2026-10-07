import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";

import type { CommandFocusFallback, CommandTriggerElement } from "./useCommandFocusRestoration";

/** Runs one navigator command from its trigger, restoring focus after it settles. */
export type RunCommand = (
  target: CommandTriggerElement,
  command: () => void | Promise<void>,
  fallback?: CommandFocusFallback | null,
) => void | Promise<void>;

/**
 * Inline rename state machine for one volume header. Opening rename
 * targets its field; Escape cancels and returns focus to the trigger,
 * and a submitted rename returns focus to the trigger once the command
 * settles. A submitted rename closes itself when the command settles
 * without a refusal (React's reset-when-props-change pattern —
 * adjusting state during render closes the form one render earlier
 * than an effect could). Failure semantics: a null `onRenameVolume`
 * mirrors an absent command set and blocks submission; a refusal
 * arrives through `renameError` and keeps the form open to render it.
 */
export function useVolumeRename({
  isMutationBusy,
  onRenameVolume,
  renamingThis,
  renameError,
  runCommand,
  volumeTitle,
}: {
  readonly isMutationBusy: boolean;
  readonly onRenameVolume: ((title: string) => void | Promise<void>) | null;
  readonly renamingThis: boolean;
  readonly renameError: string | null;
  readonly runCommand: RunCommand;
  readonly volumeTitle: string;
}) {
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameSubmitted, setRenameSubmitted] = useState(false);
  const [titleDraft, setTitleDraft] = useState("");
  const renameButtonRef = useRef<HTMLButtonElement | null>(null);
  const renameFieldRef = useRef<HTMLInputElement | null>(null);
  const saveButtonRef = useRef<HTMLButtonElement | null>(null);
  const renameFocusPendingRef = useRef(false);

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
    setTitleDraft(volumeTitle);
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
    if (!onRenameVolume || title === "" || isMutationBusy || saveButton === null) return;
    setRenameSubmitted(true);
    renameFocusPendingRef.current = true;
    void runCommand(
      saveButton,
      () => onRenameVolume(title),
      () => renameButtonRef.current,
    );
  };

  return {
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
  };
}
