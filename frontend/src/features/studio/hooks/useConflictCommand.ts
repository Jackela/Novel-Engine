import { useRef, useState } from "react";

import type { SaveState } from "@/app/types/studio";

import { useCommandFocusRestoration } from "./useCommandFocusRestoration";

type EditorCommand = "loadLatest" | "retryOverwrite" | "retrySave";

/**
 * Conflict-resolution command ownership: one in-flight conflict
 * command at a time. `pendingCommand` names the busy command so the
 * conflict surfaces can mark it, and `conflictActionsDisabled` gates
 * every conflict action while a command runs, a conflict action is
 * already pending, or a save is in flight. Settled commands restore
 * focus to the document title, the pane's semantic landing zone.
 */
export function useConflictCommand(saveState: SaveState, isConflictActionPending: boolean) {
  const titleRef = useRef<HTMLInputElement>(null);
  const pendingCommandRef = useRef<EditorCommand | null>(null);
  const [pendingCommand, setPendingCommand] = useState<EditorCommand | null>(null);
  const conflictActionsDisabled =
    pendingCommand !== null || isConflictActionPending || saveState === "saving";
  const runWithFocusRestoration = useCommandFocusRestoration(conflictActionsDisabled);

  const runConflictCommand = (
    commandKey: EditorCommand,
    target: HTMLButtonElement,
    command: (() => void | Promise<void>) | undefined,
  ) => {
    if (command === undefined || conflictActionsDisabled || pendingCommandRef.current !== null)
      return;
    pendingCommandRef.current = commandKey;
    setPendingCommand(commandKey);
    void runWithFocusRestoration(
      target,
      async () => {
        try {
          await command();
        } finally {
          if (pendingCommandRef.current === commandKey) pendingCommandRef.current = null;
          setPendingCommand((current) => (current === commandKey ? null : current));
        }
      },
      () => titleRef.current,
    );
  };

  return { conflictActionsDisabled, pendingCommand, runConflictCommand, titleRef };
}
