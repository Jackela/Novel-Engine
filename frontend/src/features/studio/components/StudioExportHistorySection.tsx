import { ExternalLink } from "lucide-react";
import { useRef } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";
import type { StudioExport } from "@/app/types/studio";
import { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";

interface StudioExportHistorySectionProps {
  exports: StudioExport[];
  historyInitialized: boolean;
  isLoadingHistory: boolean;
  historyError: string | null;
  onRetryHistory: (() => void | Promise<void>) | undefined;
  hasOlderExports: boolean;
  isLoadingOlderExports: boolean;
  olderExportsError: string | null;
  onLoadOlderExports: (() => void | Promise<void>) | undefined;
}

/** The bounded export catalog list with its explicit older-page traversal (#460). */
export function StudioExportHistorySection({
  exports,
  historyInitialized,
  isLoadingHistory,
  historyError,
  onRetryHistory,
  hasOlderExports,
  isLoadingOlderExports,
  olderExportsError,
  onLoadOlderExports,
}: StudioExportHistorySectionProps) {
  const retryHistoryWithFocusRestoration = useCommandFocusRestoration(isLoadingHistory);
  const loadOlderWithFocusRestoration = useCommandFocusRestoration(isLoadingOlderExports);
  const { t } = useTranslation();
  const historyHeadingRef = useRef<HTMLHeadingElement | null>(null);

  return (
    <section aria-labelledby="export-history-heading" className="export-history">
      <h3 id="export-history-heading" ref={historyHeadingRef} tabIndex={-1}>
        {t("export.history.heading")}
      </h3>
      {isLoadingHistory ? <p role="status">{t("export.history.loading")}</p> : null}
      {historyError ? (
        <div aria-live="assertive" className="studio-inspector__error" role="alert">
          <p>{historyError}</p>
          {onRetryHistory ? (
            <button
              aria-busy={isLoadingHistory || undefined}
              className="ui-command"
              disabled={isLoadingHistory}
              onClick={(event) => {
                void retryHistoryWithFocusRestoration(
                  event.currentTarget,
                  onRetryHistory,
                  () => historyHeadingRef.current,
                );
              }}
              type="button"
            >
              {t("common.action.tryAgain")}
            </button>
          ) : null}
        </div>
      ) : null}
      {historyInitialized && exports.length ? (
        <div className="export-list">
          {exports.map((item) => (
            <a className="studio-inspector__export-row" href={item.download_url} key={item.id}>
              <span>
                <strong>{item.format.toUpperCase()}</strong>
                <small>
                  {t("export.history.rowMeta", {
                    size: Math.ceil(item.size_bytes / 1024),
                    date: new Date(item.created_at).toLocaleString(),
                  })}
                </small>
              </span>
              <ExternalLink aria-hidden="true" />
            </a>
          ))}
        </div>
      ) : historyInitialized ? (
        <p className="studio-inspector__empty">{t("export.history.empty")}</p>
      ) : null}
      {olderExportsError ? (
        <div aria-live="assertive" className="studio-inspector__error" role="alert">
          <p>{olderExportsError}</p>
        </div>
      ) : null}
      {hasOlderExports && onLoadOlderExports ? (
        <button
          aria-busy={isLoadingOlderExports || undefined}
          className="ui-command"
          disabled={isLoadingOlderExports || isLoadingHistory}
          onClick={(event) => {
            // The terminal page unmounts this button, so the section heading
            // is the end-state landing zone.
            void loadOlderWithFocusRestoration(
              event.currentTarget,
              onLoadOlderExports,
              () => historyHeadingRef.current,
            );
          }}
          type="button"
        >
          {isLoadingOlderExports ? t("export.history.loadingOlder") : t("export.history.loadOlder")}
        </button>
      ) : null}
      {historyInitialized && exports.length > 0 && !hasOlderExports ? (
        <p className="studio-inspector__empty" role="status">
          {t("export.history.end")}
        </p>
      ) : null}
    </section>
  );
}
