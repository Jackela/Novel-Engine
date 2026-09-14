import type { Dispatch, FormEvent, SetStateAction } from "react";
import { useId, useRef } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";
import type { ProviderInfo } from "@/app/types/studio";

import { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";
import { DEFAULT_PROVIDER_OPTIONS, providerLabel } from "../studioConstants";
import type { SettingsFormState } from "../studioInspectorTypes";

interface StudioSettingsPanelProps {
  settingsForm: SettingsFormState;
  setSettingsForm: Dispatch<SetStateAction<SettingsFormState>>;
  onUpdateSettings: (event: FormEvent<HTMLFormElement>) => void | Promise<void>;
  providers?: ProviderInfo[];
  isSaving?: boolean;
  error?: string | null;
  /** #654: activates the opt-in diagnostics export (local download only). */
  onExportDiagnostics?: () => void | Promise<void>;
  isExportingDiagnostics?: boolean;
  diagnosticsError?: string | null;
}

export function StudioSettingsPanel({
  settingsForm,
  setSettingsForm,
  onUpdateSettings,
  providers = DEFAULT_PROVIDER_OPTIONS,
  isSaving = false,
  error = null,
  onExportDiagnostics,
  isExportingDiagnostics = false,
  diagnosticsError = null,
}: StudioSettingsPanelProps) {
  const saveButtonRef = useRef<HTMLButtonElement>(null);
  const diagnosticsButtonRef = useRef<HTMLButtonElement>(null);
  const errorId = useId();
  const runWithFocusRestoration = useCommandFocusRestoration(isSaving);
  const runDiagnosticsWithFocusRestoration = useCommandFocusRestoration(isExportingDiagnostics);
  const { t } = useTranslation();

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    const saveButton = saveButtonRef.current;
    if (saveButton === null) {
      void onUpdateSettings(event);
      return;
    }
    void runWithFocusRestoration(saveButton, () => onUpdateSettings(event));
  };

  return (
    <form
      aria-busy={isSaving}
      aria-describedby={error ? errorId : undefined}
      className="studio-inspector__panel"
      onSubmit={(event) => void handleSubmit(event)}
    >
      <h2>{t("settings.heading")}</h2>
      {error ? (
        <p aria-live="assertive" className="studio-inspector__error" id={errorId} role="alert">
          {error}
        </p>
      ) : null}
      <label className="studio-inspector__settings-field">
        <span>{t("common.field.title")}</span>
        <input
          disabled={isSaving}
          maxLength={240}
          onChange={(event) =>
            setSettingsForm((current) => ({
              ...current,
              title: event.target.value,
            }))
          }
          value={settingsForm.title}
        />
      </label>
      <label className="studio-inspector__settings-field">
        <span>{t("common.field.description")}</span>
        <textarea
          disabled={isSaving}
          maxLength={10000}
          onChange={(event) =>
            setSettingsForm((current) => ({
              ...current,
              description: event.target.value,
            }))
          }
          rows={4}
          value={settingsForm.description}
        />
      </label>
      <label className="studio-inspector__settings-field">
        <span>{t("settings.field.provider")}</span>
        <select
          aria-label={t("settings.field.provider")}
          disabled={isSaving}
          onChange={(event) =>
            setSettingsForm((current) => ({
              ...current,
              provider: event.target.value,
            }))
          }
          value={settingsForm.provider}
        >
          {providers.map((provider) => (
            <option key={provider.provider} value={provider.provider}>
              {providerLabel(provider.provider)}
            </option>
          ))}
        </select>
      </label>
      <div className="studio-inspector__settings-field">
        <span>{t("settings.field.storage")}</span>
        <span>{t("settings.value.sqlite")}</span>
      </div>
      <div className="studio-inspector__settings-field">
        <span>{t("settings.field.documentSyntax")}</span>
        <span>{t("settings.value.markdown")}</span>
      </div>
      <div className="studio-inspector__actions">
        <button
          aria-busy={isSaving}
          className="ui-command ui-command--primary"
          disabled={isSaving}
          ref={saveButtonRef}
          type="submit"
        >
          {isSaving ? t("settings.action.saving") : t("settings.action.save")}
        </button>
      </div>
      <p aria-live="polite" className="sr-only">
        {isSaving ? t("settings.status.saving") : ""}
      </p>
      <p>{t("settings.diagnostics.privacy")}</p>
      <div className="studio-inspector__actions">
        <button
          aria-busy={isExportingDiagnostics}
          className="ui-command"
          disabled={isExportingDiagnostics || !onExportDiagnostics}
          onClick={(event) => {
            if (onExportDiagnostics) {
              void runDiagnosticsWithFocusRestoration(
                event.currentTarget,
                onExportDiagnostics,
                () => diagnosticsButtonRef.current,
              );
            }
          }}
          ref={diagnosticsButtonRef}
          type="button"
        >
          {isExportingDiagnostics
            ? t("settings.diagnostics.action.exporting")
            : t("settings.diagnostics.action.export")}
        </button>
      </div>
      {diagnosticsError ? (
        <div aria-live="assertive" className="studio-inspector__error" role="alert">
          <p>{diagnosticsError}</p>
          {onExportDiagnostics ? (
            <button
              aria-busy={isExportingDiagnostics}
              className="ui-command"
              disabled={isExportingDiagnostics}
              onClick={(event) => {
                void runDiagnosticsWithFocusRestoration(
                  event.currentTarget,
                  onExportDiagnostics,
                  () => diagnosticsButtonRef.current,
                );
              }}
              type="button"
            >
              {t("common.action.tryAgain")}
            </button>
          ) : null}
        </div>
      ) : null}
      <p aria-live="polite" className="sr-only">
        {isExportingDiagnostics ? t("settings.diagnostics.status.exporting") : ""}
      </p>
    </form>
  );
}
