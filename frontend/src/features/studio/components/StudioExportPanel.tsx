import { Download, ExternalLink } from 'lucide-react';

import type { ExportFormat, StudioExport } from '@/app/types/studio';

interface StudioExportPanelProps {
  exports: StudioExport[];
  onExport?: (format: ExportFormat) => void;
  exportingFormat?: ExportFormat | null;
  error?: string | null;
  failedFormat?: ExportFormat | null;
  onRetry?: (format: ExportFormat) => void;
}

const FORMATS: Array<{ format: ExportFormat; label: string; description: string }> = [
  { format: 'markdown', label: 'Markdown', description: 'Portable source text' },
  { format: 'docx', label: 'Word document', description: 'Editable document' },
  { format: 'epub', label: 'EPUB', description: 'E-reader package' },
];

export function StudioExportPanel({
  exports,
  onExport,
  exportingFormat = null,
  error = null,
  failedFormat = null,
  onRetry,
}: StudioExportPanelProps) {
  return (
    <div className="inspector-content export-panel">
      <header className="inspector-heading">
        <div>
          <h2>Export project</h2>
          <p>Generate a file from the current immutable snapshot.</p>
        </div>
        <Download aria-hidden="true" />
      </header>

      <div aria-label="Export formats" className="export-format-list">
        {FORMATS.map(({ format, label, description }) => {
          const isExporting = exportingFormat === format;
          return (
            <button
              aria-busy={isExporting}
              className="export-format"
              disabled={Boolean(exportingFormat) || !onExport}
              key={format}
              onClick={() => onExport?.(format)}
              type="button"
            >
              <span>
                <strong>{label}</strong>
                <small>{description}</small>
              </span>
              <span aria-hidden="true">{isExporting ? 'Working…' : 'Export'}</span>
            </button>
          );
        })}
      </div>

      {error ? (
        <div aria-live="assertive" className="inspector-error" role="alert">
          <p>{error}</p>
          {failedFormat && onRetry ? (
            <button
              aria-label={`Retry ${failedFormat} export`}
              className="command"
              disabled={Boolean(exportingFormat)}
              onClick={() => onRetry(failedFormat)}
              type="button"
            >
              Try again
            </button>
          ) : null}
        </div>
      ) : null}

      <section aria-labelledby="export-history-heading" className="export-history">
        <h3 id="export-history-heading">Export history</h3>
        {exports.length ? (
          <div className="export-list">
            {exports.map((item) => (
              <a className="export-row" href={item.download_url} key={item.id}>
                <span>
                  <strong>{item.format.toUpperCase()}</strong>
                  <small>
                    {Math.ceil(item.size_bytes / 1024)} KB ·{' '}
                    {new Date(item.created_at).toLocaleString()}
                  </small>
                </span>
                <ExternalLink aria-hidden="true" />
              </a>
            ))}
          </div>
        ) : (
          <p className="empty-panel">No exports yet.</p>
        )}
      </section>
    </div>
  );
}
