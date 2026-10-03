import { useTranslation } from "@/app/i18n/useTranslation";

import {
  BODY_BUDGET_LIMIT_BYTES,
  bodyBudgetLevel,
  draftWordCount,
  formatBudgetBytes,
  utf8ByteLength,
} from "../bodyBudget";

interface StudioBodyBudgetProps {
  /** The editor's live text; the indicator measures the draft, not the saved revision. */
  draft: string;
}

/**
 * DR-048: the editor's body-budget indicator — the draft's word count and
 * UTF-8 size against the server's documented 1 MiB save limit. Warning at the
 * near-limit share and naming the remedy (split the chapter) keeps an
 * oversized draft from becoming a save that can never succeed. Display-only:
 * the limit stays the server's, and the draft remains in the editor either
 * way.
 */
export function StudioBodyBudget({ draft }: StudioBodyBudgetProps) {
  const { t } = useTranslation();
  const bytes = utf8ByteLength(draft);
  const level = bodyBudgetLevel(bytes);
  const limit = formatBudgetBytes(BODY_BUDGET_LIMIT_BYTES);
  const words = draftWordCount(draft);
  return (
    <span className={`editor-body-budget editor-body-budget--${level}`} data-level={level}>
      {t("editor.budget.summary", {
        used: formatBudgetBytes(bytes),
        limit,
        words: t("editor.wordCount", {
          count: words,
          unit: words === 1 ? t("noun.word") : t("noun.words"),
        }),
      })}
      {level === "ok" ? null : (
        <span aria-live="assertive" role={level === "over" ? "alert" : "status"}>
          {level === "over"
            ? t("editor.budget.over", { limit })
            : t("editor.budget.near", { limit })}
        </span>
      )}
    </span>
  );
}
