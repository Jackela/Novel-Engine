import { getByRole, getByText } from "@testing-library/dom";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LANGUAGE_STORAGE_KEY } from "@/app/i18n/language";
import { createMountHarness } from "@/test/harness";

import { StudioSettingsPanel } from "./StudioSettingsPanel";

const PRIVACY_EN =
  "Diagnostics contains version, environment, configuration status, recent error summaries, and database health — nothing you wrote, no API keys. It is saved as a file on your computer; Novel Engine never sends it anywhere. Share it only if you choose to.";

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

function mountPanel(
  diagnostics: {
    onExportDiagnostics?: () => void | Promise<void>;
    isExportingDiagnostics?: boolean;
    diagnosticsError?: string | null;
  } = {},
) {
  const onExportDiagnostics = diagnostics.onExportDiagnostics ?? vi.fn();
  return harness.mount(
    <StudioSettingsPanel
      {...baseProps}
      diagnosticsError={diagnostics.diagnosticsError ?? null}
      isExportingDiagnostics={diagnostics.isExportingDiagnostics ?? false}
      onExportDiagnostics={onExportDiagnostics}
    />,
  );
}

describe("StudioSettingsPanel diagnostics export (#654)", () => {
  it("renders the privacy statement with the export action and activates it", () => {
    const onExportDiagnostics = vi.fn();
    const mounted = mountPanel({ onExportDiagnostics });
    const container = mounted.container;

    expect(getByText(container, PRIVACY_EN)).toBeVisible();
    const action = getByRole(container, "button", { name: "Export diagnostics" });
    expect(action).toBeEnabled();

    act(() => {
      action.click();
    });
    expect(onExportDiagnostics).toHaveBeenCalledTimes(1);
  });

  it("keeps the statement visible and the action busy while exporting", () => {
    const mounted = mountPanel({ isExportingDiagnostics: true });
    const container = mounted.container;

    expect(getByText(container, PRIVACY_EN)).toBeVisible();
    const action = getByRole(container, "button", { name: "Exporting…" });
    expect(action).toHaveAttribute("aria-busy", "true");
    expect(action).toBeDisabled();
  });

  it("surfaces the failure with a retry command", () => {
    const onExportDiagnostics = vi.fn();
    const mounted = mountPanel({
      diagnosticsError: "Unable to export diagnostics.",
      onExportDiagnostics,
    });
    const container = mounted.container;

    expect(container.querySelector('[role="alert"]')?.textContent).toContain(
      "Unable to export diagnostics.",
    );
    const retry = getByRole(container, "button", { name: "Try again" });
    expect(retry).toBeEnabled();

    act(() => {
      retry.click();
    });
    expect(onExportDiagnostics).toHaveBeenCalledTimes(1);
  });

  it("renders the zh privacy statement when the zh dictionary is active", () => {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, "zh");
    const mounted = mountPanel();
    const container = mounted.container;

    expect(
      getByText(
        container,
        "诊断信息包含版本、运行环境、配置状态、近期错误摘要与数据库健康状态——不含你写的任何内容，也不含 API key。它只会以文件形式保存在你的电脑上；Novel Engine 绝不会将它发送到任何地方。是否分享由你自行决定。",
      ),
    ).toBeVisible();
    expect(getByRole(container, "button", { name: "导出诊断信息" })).toBeEnabled();
  });
});
