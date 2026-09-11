import { Monitor, Moon, Sun } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import {
  applyTheme,
  onSystemThemeChange,
  readThemePreference,
  resolveSystemScheme,
  setThemePreference,
  type ThemePreference,
} from "./theme";

const OPTIONS: readonly {
  readonly value: ThemePreference;
  readonly label: string;
  readonly Icon: typeof Sun;
}[] = [
  { value: "system", label: "System", Icon: Monitor },
  { value: "light", label: "Light", Icon: Sun },
  { value: "dark", label: "Dark", Icon: Moon },
] as const;

function optionLabel(value: ThemePreference): string {
  return value === "system"
    ? `System (${resolveSystemScheme()})`
    : (OPTIONS.find((option) => option.value === value)?.label ?? value);
}

/**
 * Three-state segmented control for theme selection (ADR-0010). Native
 * radios keep the radiogroup semantics and arrow-key navigation on the
 * platform; the 44px targets, visible focus ring, and checked styling live
 * in the `ui-theme-switch` styles in base.css.
 */
export function ThemeSwitch() {
  const [preference, setPreference] = useState<ThemePreference>(readThemePreference);

  useEffect(() => {
    // Re-assert the stored choice once mounted: the inline head script only
    // covers pre-paint locks, while the theme-color metas need the module.
    applyTheme(readThemePreference());
    return onSystemThemeChange((stored) => {
      setPreference(stored);
    });
  }, []);

  const select = useCallback((next: ThemePreference) => {
    setThemePreference(next);
    setPreference(next);
  }, []);

  return (
    <fieldset className="ui-theme-switch">
      <legend className="ui-theme-switch__legend">Theme</legend>
      {OPTIONS.map(({ value, Icon }) => (
        <label
          key={value}
          className="ui-theme-switch__option"
          data-checked={preference === value || undefined}
        >
          <input
            type="radio"
            name="theme"
            value={value}
            className="ui-theme-switch__input"
            checked={preference === value}
            onChange={() => {
              select(value);
            }}
          />
          <Icon aria-hidden="true" />
          <span>{optionLabel(value)}</span>
        </label>
      ))}
    </fieldset>
  );
}
