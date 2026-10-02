import { useTranslation } from "@/app/i18n/useTranslation";
import type { RevisionSummary } from "@/app/types/studio";

import { diffHistoryLines, type HistoryDiffKind, historyDiffRows } from "../historyLineDiff";
import type { RevisionPreviewState } from "../hooks/useRevisionPreview";

interface StudioHistoryRevisionPreviewProps {
  readonly revision: RevisionSummary;
  readonly state: RevisionPreviewState;
  /** The loaded current revision body the diff compares against. */
  readonly currentContent: string;
  readonly onRetry: () => void;
}

const DIFF_MARKERS: Record<HistoryDiffKind, string> = { context: " ", added: "+", removed: "-" };

/**
 * DR-011: one expanded history row's read-only preview — the fetched body
 * plus its line-level diff against the loaded current revision. Purely
 * presentational: the panel owns lazy loading, retry, and which row is open.
 */
export function StudioHistoryRevisionPreview({
  revision,
  state,
  currentContent,
  onRetry,
}: StudioHistoryRevisionPreviewProps) {
  const { t } = useTranslation();
  if (state.status === "loading") {
    return (
      <section aria-busy="true" className="history-preview">
        <p className="history-preview__status" role="status">
          {t("history.preview.loading")}
        </p>
      </section>
    );
  }
  if (state.status === "error") {
    return (
      <section
        aria-label={t("history.preview.heading", { number: revision.revision_number })}
        className="history-preview"
      >
        <p className="history-preview__error" role="alert">
          {state.message}
        </p>
        <button className="ui-command" onClick={onRetry} type="button">
          {t("history.preview.retry")}
        </button>
      </section>
    );
  }
  if (state.status !== "loaded") return null;
  const rows = historyDiffRows(diffHistoryLines(state.revision.content_markdown, currentContent));
  const added = rows.filter((row) => row.kind === "added").length;
  const removed = rows.filter((row) => row.kind === "removed").length;
  return (
    <section
      aria-label={t("history.preview.heading", { number: state.revision.revision_number })}
      className="history-preview"
    >
      <h3>{t("history.preview.heading", { number: state.revision.revision_number })}</h3>
      <pre className="history-preview__body">{state.revision.content_markdown}</pre>
      <h4>{t("history.diff.heading")}</h4>
      <p className="history-diff__summary">{t("history.diff.summary", { added, removed })}</p>
      {added === 0 && removed === 0 ? (
        <p className="history-diff__none">{t("history.diff.none")}</p>
      ) : (
        <pre className="history-diff">
          {rows.map((row) => (
            <span
              className={`history-diff__line history-diff__line--${row.kind}`}
              data-diff={row.kind}
              key={row.key}
            >
              {`${DIFF_MARKERS[row.kind]}${row.text}`}
            </span>
          ))}
        </pre>
      )}
    </section>
  );
}
