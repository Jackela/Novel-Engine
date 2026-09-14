import { useCallback, useEffect } from "react";

import { applyLanguage, getActiveLanguage, LANGUAGES, type Language } from "./i18n/language";
import { useTranslation } from "./i18n/useTranslation";

/**
 * Two-state segmented control for UI language (EN/zh), the language twin
 * of `ThemeSwitch`: native radios keep radiogroup semantics and arrow-key
 * navigation on the platform; the 44px targets, visible focus ring, and
 * checked styling live in the `ui-language-switch` styles in base.css.
 * Option labels are native names on purpose — they must stay findable in
 * the language the reader is switching *to*.
 */
export function LanguageSwitch() {
  const { t, language, setLanguage } = useTranslation();

  useEffect(() => {
    // Keep <html lang> truthful even when the stored choice was applied in
    // a previous session whose document is long gone.
    applyLanguage(getActiveLanguage());
  }, []);

  const select = useCallback(
    (next: Language) => {
      setLanguage(next);
    },
    [setLanguage],
  );

  return (
    <fieldset className="ui-language-switch">
      <legend className="ui-language-switch__legend">{t("language.legend")}</legend>
      {LANGUAGES.map((value) => (
        <label
          key={value}
          className="ui-language-switch__option"
          data-checked={language === value || undefined}
        >
          <input
            type="radio"
            name="language"
            value={value}
            className="ui-language-switch__input"
            checked={language === value}
            onChange={() => {
              select(value);
            }}
          />
          <span>{t(`language.option.${value}`)}</span>
        </label>
      ))}
    </fieldset>
  );
}
