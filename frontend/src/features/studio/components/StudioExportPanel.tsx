import { Download } from "lucide-react";
import { useRef } from "react";

import type { MessageKey } from "@/app/i18n/dictionaries/en";
import { useTranslation } from "@/app/i18n/useTranslation";
import type { ExportFormat, StudioExport } from "@/app/types/studio";
import { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";
import { StudioExportHistorySection } from "./StudioExportHistorySection";

interface StudioExportPanelProps {
  exports: StudioExport[];
  historyInitialized?: boolean;
  isLoadingHistory?: boolean;
  historyError?: string | null;
  onRetryHistory?: () => void | Promise<void>;
  hasOlderExports?: boolean;
  isLoadingOlderExports?: boolean;
  olderExportsError?: string | null;
  onLoadOlderExports?: () => void | Promise<void>;
  onExport?: (format: ExportFormat) => void | Promise<void>;
  exportingFormat?: ExportFormat | null;
  retryingFormat?: ExportFormat | null;
  error?: string | null;
  failedFormat?: ExportFormat | null;
  onRetry?: (format: ExportFormat) => void | Promise<void>;
}

const FORMATS: Array<{
  format: ExportFormat;
  labelKey: MessageKey;
  hintKey: MessageKey;
}> = [
  {
    format: "markdown",
    labelKey: "export.format.markdown",
    hintKey: "export.format.markdownHint",
  },
  { format: "docx", labelKey: "export.format.docx", hintKey: "export.format.docxHint" },
  { format: "epub", labelKey: "export.format.epub", hintKey: "export.format.epubHint" },
];

export function StudioExportPanel({
  exports,
  historyInitialized = true,
  isLoadingHistory = false,
  historyError = null,
  onRetryHistory,
  hasOlderExports = false,
  isLoadingOlderExports = false,
  olderExportsError = null,
  onLoadOlderExports,
  onExport,
  exportingFormat = null,
  retryingFormat = null,
  error = null,
  failedFormat = null,
  onRetry,
}: StudioExportPanelProps) {
  const isExporting = exportingFormat !== null;
  const { t } = useTranslation();
  const runWithFocusRestoration = useCommandFocusRestoration(isExporting);
  const formatButtonRefs = useRef(new Map<ExportFormat, HTMLButtonElement>());

  return (
    <div
      aria-busy={isExporting || isLoadingHistory}
      className="studio-inspector__panel export-panel"
    >
      <header className="studio-inspector__heading">
        <div>
          <h2>{t("export.heading")}</h2>
          <p>{t("export.hint")}</p>
        </div>
        <Download aria-hidden="true" />
      </header>

      {/* biome-ignore lint/a11y/useSemanticElements: this button group is not a form control group; <fieldset> would misrepresent semantics and drag in default fieldset styling. */}
      <div aria-label={t("export.formats.legend")} className="export-format-list" role="group">
        {FORMATS.map(({ format, labelKey, hintKey }) => {
          const isCurrentFormat = exportingFormat === format && retryingFormat !== format;
          return (
            <button
              aria-busy={isCurrentFormat}
              className="export-format"
              disabled={isExporting || !onExport}
              key={format}
              onClick={(event) => {
                if (onExport) {
                  void runWithFocusRestoration(event.currentTarget, () => onExport(format));
                }
              }}
              ref={(node) => {
                if (node) formatButtonRefs.current.set(format, node);
                else formatButtonRefs.current.delete(format);
              }}
              type="button"
            >
              <span>
                <strong>{t(labelKey)}</strong>
                <small>{t(hintKey)}</small>
              </span>
              <span aria-hidden="true">
                {isCurrentFormat ? t("export.action.working") : t("export.action.run")}
              </span>
            </button>
          );
        })}
      </div>

      {error ? (
        <div aria-live="assertive" className="studio-inspector__error" role="alert">
          <p>{error}</p>
          {failedFormat && onRetry ? (
            <button
              aria-label={t("export.action.retry", { format: failedFormat })}
              aria-busy={retryingFormat === failedFormat}
              className="ui-command"
              disabled={isExporting}
              onClick={(event) => {
                void runWithFocusRestoration(
                  event.currentTarget,
                  () => onRetry(failedFormat),
                  () => formatButtonRefs.current.get(failedFormat) ?? null,
                );
              }}
              type="button"
            >
              {t("common.action.tryAgain")}
            </button>
          ) : null}
        </div>
      ) : null}

      <StudioExportHistorySection
        exports={exports}
        historyInitialized={historyInitialized}
        isLoadingHistory={isLoadingHistory}
        historyError={historyError}
        onRetryHistory={onRetryHistory}
        hasOlderExports={hasOlderExports}
        isLoadingOlderExports={isLoadingOlderExports}
        olderExportsError={olderExportsError}
        onLoadOlderExports={onLoadOlderExports}
      />
    </div>
  );
}
