import { fireEvent } from "@testing-library/dom";
import { act } from "react";
import { afterEach, describe, expect, it } from "vitest";

import { createMountHarness } from "@/test/harness";

import { LANGUAGE_STORAGE_KEY } from "./i18n/language";
import { LanguageSwitch } from "./LanguageSwitch";

const harness = createMountHarness();
const INITIAL_LANG = document.documentElement.lang;

afterEach(() => {
  harness.cleanup();
  window.localStorage.clear();
  document.documentElement.lang = INITIAL_LANG;
});

function queryOptions(container: HTMLDivElement): HTMLInputElement[] {
  return [
    ...container.querySelectorAll<HTMLInputElement>('.ui-language-switch input[type="radio"]'),
  ];
}

describe("LanguageSwitch", () => {
  it("renders both native-name options and resolves the browser default", () => {
    const container = harness.mount(<LanguageSwitch />).container;
    const options = queryOptions(container);

    expect(options.map((option) => option.value)).toEqual(["en", "zh"]);
    expect(options.map((option) => option.checked)).toEqual([true, false]);
    // Option labels are native names on purpose: identical in both
    // dictionaries so the target language stays findable.
    expect(
      [...container.querySelectorAll(".ui-language-switch__option span")].map(
        (span) => span.textContent,
      ),
    ).toEqual(["English", "中文"]);
  });

  it("starts from the stored choice and follows it onto <html lang>", () => {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, "zh");

    const container = harness.mount(<LanguageSwitch />).container;
    const options = queryOptions(container);

    expect(options[1].checked).toBe(true);
    expect(document.documentElement.lang).toBe("zh");
    expect(options[1].closest(".ui-language-switch__option")?.hasAttribute("data-checked")).toBe(
      true,
    );
  });

  it("persists a switch, re-renders the checked state, and updates <html lang>", () => {
    const container = harness.mount(<LanguageSwitch />).container;
    const zh = queryOptions(container)[1];

    act(() => {
      fireEvent.click(zh);
    });

    expect(window.localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe("zh");
    expect(document.documentElement.lang).toBe("zh");
    expect(zh.checked).toBe(true);
  });
});
