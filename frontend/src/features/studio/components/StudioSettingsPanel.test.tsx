import { fireEvent, getByRole, getByText, queryByRole } from "@testing-library/dom";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ProviderInfo } from "@/app/types/studio";
import { createMountHarness, deferred } from "@/test/harness";

import { StudioSettingsPanel } from "./StudioSettingsPanel";

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
});

function render(element: React.ReactElement): HTMLDivElement {
  return harness.mount(element).container;
}

describe("StudioSettingsPanel", () => {
  const baseProps = {
    settingsForm: {
      title: "Clockwork Harbor",
      description: "A story",
      provider: "mock",
    },
    setSettingsForm: vi.fn(),
    onUpdateSettings: vi.fn(),
  };

  it("renders provider options dynamically", () => {
    const providers: ProviderInfo[] = [
      { provider: "mock", configured: true, model: null, is_default: true },
      {
        provider: "openai_compatible",
        configured: true,
        model: "gpt-4o",
        is_default: false,
      },
    ];

    const container = render(<StudioSettingsPanel {...baseProps} providers={providers} />);

    expect(
      getByRole(container, "option", { name: "Mock (trial — no API key)" }),
    ).toBeInTheDocument();
    expect(getByRole(container, "option", { name: "OpenAI-compatible" })).toBeInTheDocument();
    expect(queryByRole(container, "option", { name: "DashScope" })).not.toBeInTheDocument();
  });

  it("falls back to built-in providers when no provider list is supplied", () => {
    const container = render(<StudioSettingsPanel {...baseProps} />);

    expect(
      getByRole(container, "option", { name: "Mock (trial — no API key)" }),
    ).toBeInTheDocument();
    expect(getByRole(container, "option", { name: "DashScope" })).toBeInTheDocument();
    expect(getByRole(container, "option", { name: "OpenAI-compatible" })).toBeInTheDocument();
  });

  it("shows unknown provider IDs under their raw name so they stay selectable", () => {
    const providers: ProviderInfo[] = [
      { provider: "mock", configured: true, model: null, is_default: true },
      { provider: "custom_relay", configured: true, model: null, is_default: false },
    ];

    const container = render(<StudioSettingsPanel {...baseProps} providers={providers} />);

    const option = getByRole(container, "option", { name: "custom_relay" });
    expect(option).toHaveValue("custom_relay");
  });

  it("calls setSettingsForm when provider selection changes", () => {
    const setSettingsForm = vi.fn();

    const container = render(
      <StudioSettingsPanel {...baseProps} setSettingsForm={setSettingsForm} />,
    );

    const select = getByRole(container, "combobox", {
      name: "Provider",
    }) as HTMLSelectElement;
    select.value = "openai_compatible";
    fireEvent.change(select);

    expect(setSettingsForm).toHaveBeenCalledTimes(1);
    expect(setSettingsForm).toHaveBeenCalledWith(expect.any(Function));
  });

  it("submits settings through onUpdateSettings", () => {
    const onUpdateSettings = vi.fn((event: React.FormEvent) => event.preventDefault());

    const container = render(
      <StudioSettingsPanel {...baseProps} onUpdateSettings={onUpdateSettings} />,
    );

    fireEvent.submit(getByRole(container, "button", { name: "Save settings" }));

    expect(onUpdateSettings).toHaveBeenCalledTimes(1);
  });

  it("freezes every editable setting while a save is pending", () => {
    const container = render(<StudioSettingsPanel {...baseProps} isSaving />);

    expect(getByRole(container, "textbox", { name: "Title" })).toBeDisabled();
    expect(getByRole(container, "textbox", { name: "Description" })).toBeDisabled();
    expect(getByRole(container, "combobox", { name: "Provider" })).toBeDisabled();
    expect(getByRole(container, "button", { name: "Saving…" })).toBeDisabled();
  });

  it("disables and labels an unconfigured provider row (DR-022)", () => {
    const providers: ProviderInfo[] = [
      { provider: "mock", configured: true, model: "deterministic-story-v1", is_default: true },
      { provider: "dashscope", configured: false, model: "qwen3.5-flash", is_default: false },
    ];

    const container = render(<StudioSettingsPanel {...baseProps} providers={providers} />);

    const unconfigured = getByRole(container, "option", {
      name: "DashScope — not configured (missing API key)",
    });
    expect(unconfigured).toBeDisabled();
    expect(getByRole(container, "option", { name: "Mock (trial — no API key)" })).toBeEnabled();
  });

  it("shows the resolved model for the selected provider (DR-022)", () => {
    const providers: ProviderInfo[] = [
      { provider: "mock", configured: true, model: "deterministic-story-v1", is_default: false },
      { provider: "dashscope", configured: true, model: "qwen3.5-flash", is_default: true },
    ];
    const container = render(
      <StudioSettingsPanel
        {...baseProps}
        settingsForm={{ ...baseProps.settingsForm, provider: "dashscope" }}
        providers={providers}
      />,
    );

    expect(getByText(container, "qwen3.5-flash")).toBeInTheDocument();
    expect(getByText(container, "Model")).toBeInTheDocument();
  });

  it("warns when the selected provider has no credential and points at the setup guide (DR-022)", () => {
    const providers: ProviderInfo[] = [
      { provider: "mock", configured: true, model: "deterministic-story-v1", is_default: false },
      { provider: "dashscope", configured: false, model: "qwen3.5-flash", is_default: true },
    ];
    const container = render(
      <StudioSettingsPanel
        {...baseProps}
        settingsForm={{ ...baseProps.settingsForm, provider: "dashscope" }}
        providers={providers}
      />,
    );

    const warning = getByRole(container, "status");
    expect(warning).toHaveTextContent("This provider has no API key on the server.");
    const guide = getByRole(container, "link", { name: "Provider setup guide" });
    expect(guide).toHaveAttribute(
      "href",
      "https://github.com/Jackela/Novel-Engine/blob/main/openwiki/guides/provider-setup.md",
    );
  });

  it("keeps a save failure in the form and associates it with the form", () => {
    const container = render(
      <StudioSettingsPanel {...baseProps} error="Persistence unavailable. Try again." />,
    );

    const alert = getByRole(container, "alert");
    const form = container.querySelector("form");
    expect(alert).toHaveTextContent("Persistence unavailable. Try again.");
    expect(form).toHaveAttribute("aria-describedby", alert.id);
    expect(getByRole(container, "button", { name: "Save settings" })).toBeEnabled();
  });

  it("restores focus to the save button after the update completes", async () => {
    const onUpdateSettings = vi.fn(async (event: React.FormEvent) => {
      event.preventDefault();
      await Promise.resolve();
    });

    const container = render(
      <StudioSettingsPanel {...baseProps} onUpdateSettings={onUpdateSettings} />,
    );
    const saveButton = getByRole(container, "button", {
      name: "Save settings",
    });

    await act(async () => {
      fireEvent.submit(saveButton);
    });

    expect(document.activeElement).toBe(saveButton);
  });

  it("does not override focus the author moved during the update", async () => {
    const completion = deferred<void>();
    const onUpdateSettings = vi.fn(async (event: React.FormEvent) => {
      event.preventDefault();
      await completion.promise;
    });
    const container = render(
      <StudioSettingsPanel {...baseProps} onUpdateSettings={onUpdateSettings} />,
    );
    const saveButton = getByRole(container, "button", { name: "Save settings" });
    const provider = getByRole(container, "combobox", { name: "Provider" });
    saveButton.focus();

    void act(() => fireEvent.submit(saveButton));
    provider.focus();
    await act(async () => {
      completion.resolve(undefined);
      await completion.promise;
    });

    expect(document.activeElement).toBe(provider);
  });
});
