import { useEffect } from "react";

import type { StudioDocument } from "@/app/types/studio";

/**
 * DR-016: Ctrl/Cmd+S must flush the draft instead of opening the
 * browser's save dialog. The listener lives on the window while a
 * Document is open so the shortcut works from the title, the body,
 * and the surrounding chrome.
 */
export function useSaveNowShortcut(
  activeDocument: StudioDocument | null,
  onSaveNow: (() => void) | undefined,
) {
  useEffect(() => {
    if (!activeDocument || !onSaveNow) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (!(event.ctrlKey || event.metaKey) || event.altKey || event.shiftKey) return;
      if (event.key.toLowerCase() !== "s") return;
      event.preventDefault();
      onSaveNow();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [activeDocument, onSaveNow]);
}
