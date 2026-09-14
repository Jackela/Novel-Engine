import { getByRole } from "@testing-library/dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LANGUAGE_STORAGE_KEY } from "@/app/i18n/language";
import { createMountHarness } from "@/test/harness";

import { StudioSettingsPanel } from "./StudioSettingsPanel";

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  window.localStorage.clear();
});

const baseProps = {
  settingsForm: { title: "Clockwork Harbor", description: "A story", provider: "mock" },
  setSettingsForm: vi.fn(),
  onUpdateSettings: vi.fn(),
};

describe("StudioSettingsPanel bilingual rendering", () => {
  it("renders the English surface with provider labels by default", () => {
    const container = harness.mount(<StudioSettingsPanel {...baseProps} />).container;

    expect(getByRole(container, "heading", { name: "Project settings" })).toBeVisible();
    expect(getByRole(container, "option", { name: "Mock (trial — no API key)" })).toBeVisible();
    expect(getByRole(container, "option", { name: "OpenAI-compatible" })).toBeVisible();
    expect(getByRole(container, "button", { name: "Save settings" })).toBeEnabled();
  });

  it("renders the zh surface with localized provider labels when stored", () => {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, "zh");

    const container = harness.mount(<StudioSettingsPanel {...baseProps} />).container;

    expect(getByRole(container, "heading", { name: "项目设置" })).toBeVisible();
    expect(getByRole(container, "option", { name: "Mock（试用 — 无需 API key）" })).toBeVisible();
    expect(getByRole(container, "option", { name: "OpenAI 兼容" })).toBeVisible();
    expect(getByRole(container, "button", { name: "保存设置" })).toBeEnabled();
  });
});
