import type { Dispatch, FormEvent, SetStateAction } from 'react';

import type { SettingsFormState } from '../StudioInspector';

interface StudioSettingsPanelProps {
  settingsForm: SettingsFormState;
  setSettingsForm: Dispatch<SetStateAction<SettingsFormState>>;
  onUpdateSettings: (event: FormEvent) => void;
}

export function StudioSettingsPanel({
  settingsForm,
  setSettingsForm,
  onUpdateSettings,
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
          onChange={(event) =>
            setSettingsForm((current) => ({ ...current, provider: event.target.value }))
          }
          value={settingsForm.provider}
        >
          <option value="mock">mock</option>
          <option value="dashscope">dashscope</option>
          <option value="openai_compatible">openai_compatible</option>
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
