import { useId } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";
import type { ProviderInfo } from "@/app/types/studio";

import { providerLabel, providerSetupGuideUrl } from "../studioConstants";

interface StudioProviderFieldProps {
  /** Server-owned catalog facts (`configured`/`model`/`is_default`). */
  providers: ProviderInfo[];
  /** The provider selection owned by the settings form. */
  provider: string;
  disabled?: boolean;
  onSelect: (provider: string) => void;
}

/**
 * DR-022 provider configuration field: the option list honors the server
 * catalog instead of rendering every provider blindly — an unconfigured row
 * is disabled and labeled with its missing credential. The selected
 * provider's resolved model is shown whenever the catalog carries one, and
 * an unconfigured selection points at the provider setup guide.
 */
export function StudioProviderField({
  providers,
  provider,
  disabled = false,
  onSelect,
}: StudioProviderFieldProps) {
  const { t } = useTranslation();
  const noticeId = useId();
  const selected = providers.find((candidate) => candidate.provider === provider);
  return (
    <>
      <label className="studio-inspector__settings-field">
        <span>{t("settings.field.provider")}</span>
        <select
          aria-describedby={selected !== undefined && !selected.configured ? noticeId : undefined}
          aria-label={t("settings.field.provider")}
          disabled={disabled}
          onChange={(event) => onSelect(event.target.value)}
          value={provider}
        >
          {providers.map((candidate) => (
            <option
              disabled={!candidate.configured}
              key={candidate.provider}
              value={candidate.provider}
            >
              {candidate.configured
                ? providerLabel(candidate.provider)
                : `${providerLabel(candidate.provider)} — ${t("settings.provider.notConfigured")}`}
            </option>
          ))}
        </select>
      </label>
      <div className="studio-inspector__settings-field">
        <span>{t("settings.field.model")}</span>
        <span>{selected?.model ?? t("settings.value.modelUnknown")}</span>
      </div>
      {selected !== undefined && !selected.configured ? (
        <p className="studio-inspector__settings-notice" id={noticeId} role="status">
          {t("settings.provider.missingCredential")}{" "}
          <a href={providerSetupGuideUrl()} rel="noreferrer" target="_blank">
            {t("settings.provider.setupGuide")}
          </a>
        </p>
      ) : null}
    </>
  );
}
