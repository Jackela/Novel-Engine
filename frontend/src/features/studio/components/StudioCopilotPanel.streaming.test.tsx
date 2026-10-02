import { getByRole } from "@testing-library/dom";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createMountHarness } from "@/test/harness";

import { StudioCopilotPanel } from "./StudioCopilotPanel";

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.unstubAllGlobals();
});

describe("StudioCopilotPanel streaming recovery", () => {
  it("keeps an interrupted preview readable with a copy action instead of Stop", async () => {
    const writeText = vi.fn<(text: string) => Promise<void>>().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    const props = {
      instruction: "Continue the scene.",
      setInstruction: vi.fn(),
      proposal: null,
      setProposal: vi.fn(),
      onRunProposal: vi.fn(),
      onAcceptProposal: vi.fn(),
      onStopProposal: vi.fn(),
    };
    const mounted = harness.mount(
      <StudioCopilotPanel
        {...props}
        isRunningProposal={false}
        streamingText="A quiet beginning"
        streamingInterrupted
      />,
    );

    expect(mounted.container.textContent).toContain("A quiet beginning");
    expect(mounted.container.textContent).toContain("Interrupted — text preserved");
    expect(mounted.container.textContent).not.toContain("Stop");

    const copy = getByRole(mounted.container, "button", { name: "Copy" });
    await act(async () => {
      copy.click();
      await Promise.resolve();
    });
    expect(writeText).toHaveBeenCalledWith("A quiet beginning");
  });

  it("moves orphaned Stop focus to Continue after streaming stops", async () => {
    const onStopProposal = vi.fn();
    const props = {
      instruction: "Continue the scene.",
      setInstruction: vi.fn(),
      proposal: null,
      setProposal: vi.fn(),
      onRunProposal: vi.fn(),
      onAcceptProposal: vi.fn(),
      onStopProposal,
    };
    const mounted = harness.mount(
      <StudioCopilotPanel {...props} isRunningProposal streamingText="Partial draft" />,
    );
    const stop = Array.from(mounted.container.querySelectorAll<HTMLButtonElement>("button")).find(
      (button) => button.textContent?.includes("Stop"),
    );
    if (stop === undefined) throw new Error("Expected the Stop command.");

    stop.focus();
    act(() => stop.click());
    await act(async () => Promise.resolve());
    act(() => {
      mounted.root.render(
        <StudioCopilotPanel {...props} isRunningProposal={false} streamingText={null} />,
      );
    });

    const continueButton = Array.from(
      mounted.container.querySelectorAll<HTMLButtonElement>("button"),
    ).find((button) => button.textContent?.includes("Continue"));
    expect(onStopProposal).toHaveBeenCalledOnce();
    expect(document.activeElement).toBe(continueButton);
  });
});
