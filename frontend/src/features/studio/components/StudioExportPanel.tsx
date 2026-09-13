import { Download } from "lucide-react";
import { useRef } from "react";

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
  label: string;
  description: string;
}> = [
  {
    format: "markdown",
    label: "Markdown",
    description: "Portable source text",
  },
  { format: "docx", label: "Word document", description: "Editable document" },
  { format: "epub", label: "EPUB", description: "E-reader package" },
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
  const runWithFocusRestoration = useCommandFocusRestoration(isExporting);
  const formatButtonRefs = useRef(new Map<ExportFormat, HTMLButtonElement>());

  return (
    <div
      aria-busy={isExporting || isLoadingHistory}
      className="studio-inspector__panel export-panel"
    >
      <header className="studio-inspector__heading">
        <div>
          <h2>Export project</h2>
          <p>Generate a file from the current immutable snapshot.</p>
        </div>
        <Download aria-hidden="true" />
      </header>

      {/* biome-ignore lint/a11y/useSemanticElements: this button group is not a form control group; <fieldset> would misrepresent semantics and drag in default fieldset styling. */}
      <div aria-label="Export formats" className="export-format-list" role="group">
        {FORMATS.map(({ format, label, description }) => {
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
                <strong>{label}</strong>
                <small>{description}</small>
              </span>
              <span aria-hidden="true">{isCurrentFormat ? "Working…" : "Export"}</span>
            </button>
          );
        })}
      </div>

      {error ? (
        <div aria-live="assertive" className="studio-inspector__error" role="alert">
          <p>{error}</p>
          {failedFormat && onRetry ? (
            <button
              aria-label={`Retry ${failedFormat} export`}
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
              Try again
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
