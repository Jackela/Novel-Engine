import type { Dispatch, FormEvent, SetStateAction } from 'react';

import type { ProviderInfo } from '@/app/types/studio';

import { DEFAULT_PROVIDER_OPTIONS } from '../studioConstants';
import type { SettingsFormState } from '../StudioInspector';

interface StudioSettingsPanelProps {
  settingsForm: SettingsFormState;
  setSettingsForm: Dispatch<SetStateAction<SettingsFormState>>;
  onUpdateSettings: (event: FormEvent) => void;
  providers?: ProviderInfo[];
}

export function StudioSettingsPanel({
  settingsForm,
  setSettingsForm,
  onUpdateSettings,
  providers = DEFAULT_PROVIDER_OPTIONS,
}: StudioSettingsPanelProps) {
  return (
    <form className="inspector-content" onSubmit={onUpdateSettings}>
      <h2>Project settings</h2>
      <label className="settings-field">
        <span>Title</span>
        <input
          maxLength={240}
          onChange={(event) =>
            setSettingsForm((current) => ({ ...current, title: event.target.value }))
          }
          value={settingsForm.title}
        />
      </label>
      <label className="settings-field">
        <span>Description</span>
        <textarea
          maxLength={10000}
          onChange={(event) =>
            setSettingsForm((current) => ({ ...current, description: event.target.value }))
          }
          rows={4}
          value={settingsForm.description}
        />
      </label>
      <label className="settings-field">
        <span>Provider</span>
        <select
          aria-label="Provider"
          onChange={(event) =>
            setSettingsForm((current) => ({ ...current, provider: event.target.value }))
          }
          value={settingsForm.provider}
        >
          {providers.map((provider) => (
            <option key={provider.provider} value={provider.provider}>
              {provider.provider}
            </option>
          ))}
        </select>
      </label>
      <div className="settings-field">
        <span>Storage</span>
        <span>SQLite</span>
      </div>
      <div className="settings-field">
        <span>Document syntax</span>
        <span>Markdown</span>
      </div>
      <div className="inspector-actions">
        <button className="command command--primary" type="submit">
          Save settings
        </button>
      </div>
    </form>
  );
}
