import { Loader2 } from "lucide-react";

import { useTranslation } from "@/app/i18n/useTranslation";

interface StudioEditorEmptyStateProps {
  readonly documentLoadError: string | null;
  readonly isLoadingDocument: boolean;
  readonly onRetryDocument: (() => void) | undefined;
}

/**
 * The no-Document surfaces: the loading indicator (polite), the
 * retryable load failure (assertive, with the explicit retry
 * command), and the quiet empty state.
 */
export function StudioEditorEmptyState({
  documentLoadError,
  isLoadingDocument,
  onRetryDocument,
}: StudioEditorEmptyStateProps) {
  const { t } = useTranslation();
  if (isLoadingDocument) {
    return (
      <div aria-live="polite" className="editor__empty" role="status">
        <Loader2 aria-hidden="true" className="ui-spin" /> {t("editor.loadingDocument")}
      </div>
    );
  }
  if (documentLoadError) {
    return (
      <div aria-live="assertive" className="editor__empty" role="alert">
        <strong>{t("editor.error.heading")}</strong>
        <span>{documentLoadError}</span>
        {onRetryDocument ? (
          <button
            className="ui-command ui-command--primary"
            onClick={onRetryDocument}
            type="button"
          >
            {t("editor.action.retryDocument")}
          </button>
        ) : null}
      </div>
    );
  }
  return <div className="editor__empty">{t("editor.empty")}</div>;
}
