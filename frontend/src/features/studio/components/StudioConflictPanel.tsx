import { useTranslation } from "@/app/i18n/useTranslation";

import type { ServerVersionPreviewController } from "../hooks/useConflictServerPreview";

/** The two destructive conflict commands the panel can run. */
export type ConflictCommand = "loadLatest" | "retryOverwrite";

interface StudioConflictPanelProps {
  readonly error: string | null;
  readonly disabled: boolean;
  /** The command whose promise is still pending; drives its aria-busy state. */
  readonly pendingCommand: string | null;
  readonly onLoadLatest?: () => void | Promise<void>;
  readonly onRetryOverwrite?: () => void | Promise<void>;
  readonly onRunCommand: (
    command: ConflictCommand,
    target: HTMLButtonElement,
    run: (() => void | Promise<void>) | undefined,
  ) => void;
  /** DR-012: read-only server-version view; absent in isolated fixtures. */
  readonly serverVersion?: ServerVersionPreviewController | null;
}

/**
 * The save-conflict surface: the guard message, the three-way choice — load
 * latest, keep local, or decide after the read-only server-version preview —
 * and, with DR-012, the preview that names the revision the local overwrite
 * would supersede while leaving the local draft untouched.
 */
export function StudioConflictPanel({
  error,
  disabled,
  pendingCommand,
  onLoadLatest,
  onRetryOverwrite,
  onRunCommand,
  serverVersion = null,
}: StudioConflictPanelProps) {
  const { t } = useTranslation();
  return (
    <div aria-live="assertive" className="editor-conflict" role="alert">
      <strong>{t("editor.conflict.heading")}</strong>
      {error ? <span>{error}</span> : null}
      <div className="editor-conflict__actions">
        <button
          aria-busy={pendingCommand === "loadLatest" || undefined}
          disabled={disabled || onLoadLatest === undefined}
          onClick={(event) => onRunCommand("loadLatest", event.currentTarget, onLoadLatest)}
          type="button"
        >
          {t("editor.conflict.action.loadLatest")}
        </button>
        <button
          aria-busy={pendingCommand === "retryOverwrite" || undefined}
          disabled={disabled || onRetryOverwrite === undefined}
          onClick={(event) => onRunCommand("retryOverwrite", event.currentTarget, onRetryOverwrite)}
          type="button"
        >
          {t("editor.conflict.action.keepLocal")}
        </button>
        {serverVersion ? (
          <button
            aria-busy={serverVersion.isLoading || undefined}
            disabled={disabled || serverVersion.isLoading}
            onClick={() => {
              if (serverVersion.isOpen) serverVersion.hide();
              else void serverVersion.view();
            }}
            type="button"
          >
            {serverVersion.isOpen
              ? t("editor.conflict.action.hideServer")
              : t("editor.conflict.action.viewServer")}
          </button>
        ) : null}
      </div>
      {serverVersion?.isOpen ? (
        <section
          aria-label={t("editor.conflict.server.heading")}
          className="editor-conflict__server"
        >
          <strong>{t("editor.conflict.server.heading")}</strong>
          {serverVersion.isLoading ? (
            <p role="status">{t("editor.conflict.server.loading")}</p>
          ) : null}
          {serverVersion.error !== null ? <p role="alert">{serverVersion.error}</p> : null}
          {serverVersion.revision !== null && serverVersion.currentRevisionId !== null ? (
            <>
              <p>
                {t("editor.conflict.server.overwritten", {
                  number: serverVersion.revision.revision_number,
                  id: serverVersion.currentRevisionId.slice(0, 8),
                })}
              </p>
              <pre className="editor-conflict__server-body">
                {serverVersion.revision.content_markdown}
              </pre>
            </>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
