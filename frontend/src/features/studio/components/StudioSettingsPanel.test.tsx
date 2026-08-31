import { fireEvent, getByRole, queryByRole } from "@testing-library/dom";
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

    expect(getByRole(container, "option", { name: "mock" })).toBeInTheDocument();
    expect(getByRole(container, "option", { name: "openai_compatible" })).toBeInTheDocument();
    expect(queryByRole(container, "option", { name: "dashscope" })).not.toBeInTheDocument();
  });

  it("falls back to built-in providers when no provider list is supplied", () => {
    const container = render(<StudioSettingsPanel {...baseProps} />);

    expect(getByRole(container, "option", { name: "mock" })).toBeInTheDocument();
    expect(getByRole(container, "option", { name: "dashscope" })).toBeInTheDocument();
    expect(getByRole(container, "option", { name: "openai_compatible" })).toBeInTheDocument();
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

    act(() => fireEvent.submit(saveButton));
    provider.focus();
    await act(async () => {
      completion.resolve(undefined);
      await completion.promise;
    });

    expect(document.activeElement).toBe(provider);
  });
});
