import { useEffect, useRef, useState } from "react";
import { api } from "@/app/api";
import { useTranslation } from "@/app/i18n/useTranslation";
import type { AgentExecution } from "@/app/parseAgentExecution";
import type { StudioJobSummary } from "@/app/types/studio";
import { toErrorMessage } from "../hooks/toErrorMessage";
import { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";

interface StudioAcpJobActionsProps {
  readonly projectId: string;
  readonly job: StudioJobSummary;
  readonly disabled: boolean;
  readonly onRetry: (jobId: string) => void | Promise<void>;
}

/** Read durable tool evidence before allowing a retry with possible file effects. */
export function StudioAcpJobActions({
  projectId,
  job,
  disabled,
  onRetry,
}: StudioAcpJobActionsProps) {
  const { t } = useTranslation();
  const [execution, setExecution] = useState<AgentExecution | undefined>();
  const [visible, setVisible] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const evidenceRef = useRef<HTMLDivElement>(null);
  const retryRef = useRef<HTMLButtonElement>(null);
  const restoreFocus = useCommandFocusRestoration(busy);
  useEffect(() => () => controllerRef.current?.abort(), []);
  const retryable = job.status === "failed" || job.status === "interrupted";

  const read = async (retry: boolean) => {
    if (controllerRef.current || disabled) return;
    const controller = new AbortController();
    controllerRef.current = controller;
    setBusy(true);
    setError(null);
    try {
      const detail = await api.job(projectId, job.id, { signal: controller.signal });
      if (controller.signal.aborted) return;
      const evidence = detail.result.agent_execution;
      setExecution(evidence);
      setVisible(true);
      const needsConfirmation =
        evidence === undefined || evidence.outcome_unknown || evidence.external_effects.length > 0;
      if (retry && needsConfirmation) {
        setConfirming(true);
        queueMicrotask(() => evidenceRef.current?.focus());
      } else if (retry) await onRetry(job.id);
    } catch (reason) {
      if (!controller.signal.aborted) setError(toErrorMessage(reason, t("acp.error.evidence")));
    } finally {
      if (controllerRef.current === controller) controllerRef.current = null;
      setBusy(false);
    }
  };
  const confirm = async () => {
    if (busy || disabled) return;
    setConfirming(false);
    setBusy(true);
    try {
      await onRetry(job.id);
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <button
        className="ui-command"
        type="button"
        disabled={disabled || busy}
        aria-busy={busy || undefined}
        onClick={(event) => {
          void restoreFocus(
            event.currentTarget,
            () => read(false),
            () => evidenceRef.current,
          );
        }}
      >
        {t("acp.action.viewActivity")}
      </button>
      {retryable ? (
        <button
          className="ui-command"
          type="button"
          ref={retryRef}
          disabled={disabled || busy || confirming}
          aria-label={t("jobs.action.retry", { operation: job.operation })}
          onClick={(event) => {
            void restoreFocus(
              event.currentTarget,
              () => read(true),
              () => evidenceRef.current,
            );
          }}
        >
          {t("jobs.action.retry", { operation: job.operation })}
        </button>
      ) : null}
      {visible || error ? (
        <div ref={evidenceRef} tabIndex={-1} className="studio-inspector__proposal">
          {error ? (
            <p role="alert" className="studio-inspector__error">
              {error}
            </p>
          ) : null}
          {execution?.external_effects.map((tool) => (
            <div key={tool.tool_id}>
              <strong>{tool.title}</strong>
              <p>{tool.target ?? tool.kind}</p>
              <small>{tool.status}</small>
            </div>
          ))}
          {execution?.outcome_unknown || execution === undefined ? (
            <p>{t("acp.effects.unknown")}</p>
          ) : execution.external_effects.length > 0 ? (
            <p>{t("acp.effects.completed")}</p>
          ) : (
            <p>{t("acp.effects.none")}</p>
          )}
          {confirming ? (
            <fieldset className="studio-acp__permission">
              <legend>{t("acp.retry.confirmation")}</legend>
              <p>{t("acp.retry.warning")}</p>
              <button
                className="ui-command ui-command--primary"
                type="button"
                disabled={disabled || busy}
                onClick={(event) => {
                  void restoreFocus(event.currentTarget, confirm, () => retryRef.current);
                }}
              >
                {t("acp.retry.confirm")}
              </button>
              <button
                className="ui-command"
                type="button"
                disabled={busy}
                onClick={() => {
                  setConfirming(false);
                  queueMicrotask(() => retryRef.current?.focus());
                }}
              >
                {t("acp.retry.cancel")}
              </button>
            </fieldset>
          ) : null}
        </div>
      ) : null}
    </>
  );
}
