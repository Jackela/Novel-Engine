import { useRef } from "react";
import { useTranslation } from "@/app/i18n/useTranslation";
import type { AcpOperationView } from "../hooks/useAcpOperation";
import { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";

interface StudioAcpOperationsProps {
  readonly operations: readonly AcpOperationView[];
  readonly onRespond: (
    operationId: string,
    permissionId: string,
    optionId: string,
  ) => void | Promise<void>;
  readonly onCancel: (operationId: string) => void;
}

/** Redacted tool progress and CLI-defined choices stay inside the Inspector. */
export function StudioAcpOperations({ operations, onRespond, onCancel }: StudioAcpOperationsProps) {
  const { t } = useTranslation();
  const headingRef = useRef<HTMLHeadingElement>(null);
  const restoreFocus = useCommandFocusRestoration(false);
  if (operations.length === 0) return null;
  return (
    <section className="studio-inspector__panel studio-acp" aria-label={t("acp.heading")}>
      <h2 ref={headingRef} tabIndex={-1}>
        {t("acp.heading")}
      </h2>
      {operations.map((operation) => {
        const running = ["connecting", "running", "waiting"].includes(operation.phase);
        return (
          <div key={operation.id} aria-busy={running && operation.permissions.length === 0}>
            <p aria-live="polite" role="status">
              {t(`acp.status.${operation.phase}`)}
            </p>
            {operation.tools.map((tool) => (
              <p key={tool.tool_id}>
                {tool.title}
                {tool.target ? ` — ${tool.target}` : ""} ({tool.status})
              </p>
            ))}
            {operation.permissions.map((permission) => {
              const deciding = operation.decidingPermissionIds.includes(permission.permission_id);
              return (
                <fieldset
                  className="studio-acp__permission"
                  key={permission.permission_id}
                  disabled={deciding}
                >
                  <legend>{permission.tool.title}</legend>
                  <p>{permission.tool.kind}</p>
                  {permission.tool.target ? <p>{permission.tool.target}</p> : null}
                  <div className="studio-inspector__actions">
                    {permission.options.map((option) => (
                      <button
                        key={option.option_id}
                        type="button"
                        className="ui-command"
                        disabled={deciding}
                        aria-busy={deciding || undefined}
                        onClick={(event) => {
                          void restoreFocus(
                            event.currentTarget,
                            () =>
                              onRespond(operation.id, permission.permission_id, option.option_id),
                            () => headingRef.current,
                          );
                        }}
                      >
                        {option.name}
                      </button>
                    ))}
                  </div>
                </fieldset>
              );
            })}
            {operation.error ? (
              <p className="studio-inspector__error" role="alert">
                {operation.error}
              </p>
            ) : null}
            {operation.effects !== "none" ? <p>{t(`acp.effects.${operation.effects}`)}</p> : null}
            {running ? (
              <button
                type="button"
                className="ui-command"
                onClick={() => {
                  onCancel(operation.id);
                  headingRef.current?.focus();
                }}
              >
                {t("acp.action.stop")}
              </button>
            ) : null}
          </div>
        );
      })}
    </section>
  );
}
