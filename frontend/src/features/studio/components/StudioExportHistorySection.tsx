import { ExternalLink } from "lucide-react";
import { useRef } from "react";

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
  const historyHeadingRef = useRef<HTMLHeadingElement | null>(null);

  return (
    <section aria-labelledby="export-history-heading" className="export-history">
      <h3 id="export-history-heading" ref={historyHeadingRef} tabIndex={-1}>
        Export history
      </h3>
      {isLoadingHistory ? <p role="status">Loading export history…</p> : null}
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
              Try again
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
                  {Math.ceil(item.size_bytes / 1024)} KB ·{" "}
                  {new Date(item.created_at).toLocaleString()}
                </small>
              </span>
              <ExternalLink aria-hidden="true" />
            </a>
          ))}
        </div>
      ) : historyInitialized ? (
        <p className="studio-inspector__empty">No exports yet.</p>
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
            void loadOlderWithFocusRestoration(event.currentTarget, onLoadOlderExports);
          }}
          type="button"
        >
          {isLoadingOlderExports ? "Loading older exports" : "Load older exports"}
        </button>
      ) : null}
      {historyInitialized && exports.length > 0 && !hasOlderExports ? (
        <p className="studio-inspector__empty" role="status">
          End of export history.
        </p>
      ) : null}
    </section>
  );
}
