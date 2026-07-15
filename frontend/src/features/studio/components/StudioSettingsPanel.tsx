import { useRef } from 'react';
import type { Dispatch, FormEvent, SetStateAction } from 'react';

import type { ProviderInfo } from '@/app/types/studio';

import { DEFAULT_PROVIDER_OPTIONS } from '../studioConstants';
import type { SettingsFormState } from '../StudioInspector';

interface StudioSettingsPanelProps {
  settingsForm: SettingsFormState;
  setSettingsForm: Dispatch<SetStateAction<SettingsFormState>>;
  onUpdateSettings: (event: FormEvent<HTMLFormElement>) => void | Promise<void>;
  providers?: ProviderInfo[];
  isSaving?: boolean;
}

export function StudioSettingsPanel({
  settingsForm,
  setSettingsForm,
  onUpdateSettings,
  providers = DEFAULT_PROVIDER_OPTIONS,
  isSaving = false,
}: StudioSettingsPanelProps) {
  const saveButtonRef = useRef<HTMLButtonElement>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    try {
      await onUpdateSettings(event);
    } finally {
      saveButtonRef.current?.focus();
    }
  };

  return (
    <form
      aria-busy={isSaving}
      className="inspector-content"
      onSubmit={(event) => void handleSubmit(event)}
    >
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
        <button
          aria-busy={isSaving}
          className="command command--primary"
          disabled={isSaving}
          ref={saveButtonRef}
          type="submit"
        >
          {isSaving ? 'Saving…' : 'Save settings'}
        </button>
      </div>
      <p aria-live="polite" className="sr-only">
        {isSaving ? 'Saving project settings.' : ''}
      </p>
    </form>
  );
}
