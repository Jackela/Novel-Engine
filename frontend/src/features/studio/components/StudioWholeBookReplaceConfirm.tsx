import type { RefObject } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";

import type { WholeBookCommand } from "../hooks/useWholeBookFocusReturn";
import type { WholeBookChapter } from "../hooks/useWholeBookLoop";

interface StudioWholeBookReplaceConfirmProps {
  /** Returns focus to the Start command that opened the surface. */
  readonly cancelConfirmation: () => void;
  /** The plural-aware count unit ("chapter"/"chapters") for scope labels. */
  readonly chaptersUnit: (count: number) => string;
  readonly emptyActionRef: RefObject<HTMLButtonElement | null>;
  /** Dry-run list: chapters a confirmed run would replace (#DR-007). */
  readonly occupiedChapters: readonly WholeBookChapter[];
  /** Replacing occupied chapters; absent, only the empty scope runs. */
  readonly onConfirmReplace: WholeBookCommand | undefined;
  readonly onStart: WholeBookCommand;
  readonly replaceActionRef: RefObject<HTMLButtonElement | null>;
  /** Closes the surface and runs the picked scope through the command ledger. */
  readonly runConfirmation: (command: WholeBookCommand) => void;
  /** How many of the remaining chapters are empty and may start without confirmation. */
  readonly safeCount: number;
}

/**
 * The replacement-scope confirmation for a whole-book run: the
 * dry-run list naming every chapter a confirmed run would replace,
 * the empty scope offered first (and focused so keyboard authors
 * read the list before firing), the replacement scope, and cancel —
 * which returns focus to the Start command that opened it, mirroring
 * the navigator's delete confirmation.
 */
export function StudioWholeBookReplaceConfirm({
  cancelConfirmation,
  chaptersUnit,
  emptyActionRef,
  occupiedChapters,
  onConfirmReplace,
  onStart,
  replaceActionRef,
  runConfirmation,
  safeCount,
}: StudioWholeBookReplaceConfirmProps) {
  const { t } = useTranslation();

  return (
    <>
      <p className="whole-book__hint">{t("wholeBook.confirm.message")}</p>
      <ul aria-label={t("wholeBook.confirm.listLabel")} className="whole-book__hint">
        {occupiedChapters.map((chapter) => (
          <li key={chapter.id}>{chapter.title}</li>
        ))}
      </ul>
      {safeCount > 0 ? (
        <button
          className="ui-command"
          onClick={() => runConfirmation(onStart)}
          ref={emptyActionRef}
          type="button"
        >
          {t("wholeBook.action.generateEmpty", {
            count: safeCount,
            unit: chaptersUnit(safeCount),
          })}
        </button>
      ) : null}
      <button
        className="ui-command"
        onClick={() => runConfirmation(onConfirmReplace ?? onStart)}
        ref={replaceActionRef}
        type="button"
      >
        {t("wholeBook.action.replaceOccupied", {
          count: occupiedChapters.length,
          unit: chaptersUnit(occupiedChapters.length),
        })}
      </button>
      <button className="ui-command" onClick={cancelConfirmation} type="button">
        {t("wholeBook.action.cancel")}
      </button>
    </>
  );
}
