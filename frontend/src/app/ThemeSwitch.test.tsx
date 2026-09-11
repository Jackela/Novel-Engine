import { fireEvent } from "@testing-library/dom";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createMountHarness } from "@/test/harness";
import { ThemeSwitch } from "./ThemeSwitch";
import { THEME_STORAGE_KEY } from "./theme";

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.unstubAllGlobals();
  delete document.documentElement.dataset.theme;
});

function queryOptions(container: HTMLDivElement): HTMLInputElement[] {
  return [...container.querySelectorAll<HTMLInputElement>('.ui-theme-switch input[type="radio"]')];
}

describe("ThemeSwitch", () => {
  it("renders the three states and resolves the system target label", () => {
    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: true,
      media: query,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
    }));

    const container = harness.mount(<ThemeSwitch />).container;
    const options = queryOptions(container);

    expect(options).toHaveLength(3);
    expect(options.map((option) => option.value)).toEqual(["system", "light", "dark"]);
    expect(
      [...container.querySelectorAll(".ui-theme-switch__option span")].map(
        (span) => span.textContent,
      ),
    ).toEqual(["System (dark)", "Light", "Dark"]);
    expect(options.map((option) => option.checked)).toEqual([true, false, false]);
  });

  it("re-resolves the system label when the OS scheme flips while unlocked", () => {
    let darkQueryMatches = true;
    let changeHandler: (() => void) | undefined;
    vi.stubGlobal("matchMedia", (query: string) => ({
      get matches() {
        return darkQueryMatches;
      },
      media: query,
      addEventListener: (_type: string, listener: () => void) => {
        changeHandler = listener;
      },
      removeEventListener: () => undefined,
    }));

    const container = harness.mount(<ThemeSwitch />).container;
    const labels = () =>
      [...container.querySelectorAll(".ui-theme-switch__option span")].map(
        (span) => span.textContent,
      );
    expect(labels(), "initial render resolves the OS target").toEqual([
      "System (dark)",
      "Light",
      "Dark",
    ]);

    act(() => {
      darkQueryMatches = false;
      changeHandler?.();
    });

    expect(labels(), "the system label follows the flip without any interaction").toEqual([
      "System (light)",
      "Light",
      "Dark",
    ]);
    expect(queryOptions(container).map((option) => option.checked)).toEqual([true, false, false]);
  });

  it("writes and applies the dark lock on activation", () => {
    const container = harness.mount(<ThemeSwitch />).container;
    const dark = queryOptions(container)[2];

    act(() => {
      fireEvent.click(dark);
    });

    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(dark.checked).toBe(true);
    expect(dark.closest(".ui-theme-switch__option")?.hasAttribute("data-checked")).toBe(true);
  });

  it("starts from the stored lock and returns to system on request", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "light");

    const container = harness.mount(<ThemeSwitch />).container;
    const options = queryOptions(container);
    expect(options[1].checked).toBe(true);
    expect(document.documentElement.dataset.theme).toBe("light");

    act(() => {
      fireEvent.click(options[0]);
    });
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("system");
    expect(document.documentElement.dataset.theme).toBeUndefined();
    expect(options[0].checked).toBe(true);
  });
});
