import { getByRole } from "@testing-library/dom";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { job } from "@/test/factories";
import { createMountHarness, deferred } from "@/test/harness";

import { StudioCopilotPanel } from "./StudioCopilotPanel";

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
});

describe("StudioCopilotPanel", () => {
  it.each([
    ["Rewrite", "rewrite", "Rewriting…", "Continue"],
    ["Continue", "continue", "Generating…", "Rewrite"],
  ] as const)(
    "marks only the initiating %s command busy",
    async (label, operation, pendingLabel, otherLabel) => {
      const completion = deferred<void>();
      const onRunProposal = vi.fn(() => completion.promise);
      const props = {
        instruction: "Continue the scene.",
        setInstruction: vi.fn(),
        proposal: null,
        setProposal: vi.fn(),
        onRunProposal,
        onAcceptProposal: vi.fn(),
      };
      const mounted = harness.mount(<StudioCopilotPanel {...props} />);
      const initiator = getByRole(mounted.container, "button", { name: label });
      const otherCommand = getByRole(mounted.container, "button", { name: otherLabel });

      act(() => {
        initiator.click();
        mounted.root.render(<StudioCopilotPanel {...props} isRunningProposal />);
      });

      expect(onRunProposal).toHaveBeenCalledOnce();
      expect(onRunProposal).toHaveBeenCalledWith(operation);
      expect(initiator).toBeDisabled();
      expect(initiator).toHaveAttribute("aria-busy", "true");
      expect(initiator).toHaveAccessibleName(pendingLabel);
      expect(otherCommand).toBeDisabled();
      expect(otherCommand).not.toHaveAttribute("aria-busy");
      expect(otherCommand).toHaveAccessibleName(otherLabel);

      await act(async () => {
        completion.resolve(undefined);
        await completion.promise;
        mounted.root.render(<StudioCopilotPanel {...props} isRunningProposal={false} />);
      });
    },
  );

  it("does not steal focus after generation when the author moved elsewhere", async () => {
    const completion = deferred<void>();
    const onRunProposal = vi.fn(() => completion.promise);
    const props = {
      instruction: "Continue the scene.",
      setInstruction: vi.fn(),
      proposal: null,
      setProposal: vi.fn(),
      onRunProposal,
      onAcceptProposal: vi.fn(),
    };
    const mounted = harness.mount(<StudioCopilotPanel {...props} />);
    const continueButton = Array.from(
      mounted.container.querySelectorAll<HTMLButtonElement>("button"),
    ).find((button) => button.textContent?.includes("Continue"));
    if (continueButton === undefined) throw new Error("Expected the Continue button.");

    act(() => {
      continueButton.click();
      mounted.root.render(<StudioCopilotPanel {...props} isRunningProposal />);
    });
    const otherButton = document.createElement("button");
    document.body.appendChild(otherButton);
    otherButton.focus();

    await act(async () => {
      completion.resolve(undefined);
      await completion.promise;
    });
    expect(document.activeElement).toBe(otherButton);

    act(() => {
      mounted.root.render(
        <StudioCopilotPanel
          {...props}
          isRunningProposal={false}
          proposal={job({ result: { proposal_markdown: "# Next scene" } })}
        />,
      );
    });
    expect(document.activeElement).toBe(otherButton);
    otherButton.remove();
  });

  it("moves orphaned Accept focus to the proposal instruction after acceptance", async () => {
    const completion = deferred<void>();
    const proposal = job({ result: { proposal_markdown: "# Next scene" } });
    const props = {
      instruction: "Continue the scene.",
      setInstruction: vi.fn(),
      proposal,
      setProposal: vi.fn(),
      onRunProposal: vi.fn(),
      onAcceptProposal: vi.fn(() => completion.promise),
    };
    const mounted = harness.mount(<StudioCopilotPanel {...props} />);
    const acceptButton = Array.from(
      mounted.container.querySelectorAll<HTMLButtonElement>("button"),
    ).find((button) => button.textContent?.includes("Accept"));
    const instruction = mounted.container.querySelector<HTMLTextAreaElement>(
      'textarea[aria-label="Proposal instruction"]',
    );
    if (acceptButton === undefined || instruction === null) {
      throw new Error("Expected the Accept command and proposal instruction.");
    }

    acceptButton.focus();
    act(() => {
      acceptButton.click();
      mounted.root.render(<StudioCopilotPanel {...props} isAcceptingProposal />);
    });
    await act(async () => {
      completion.resolve(undefined);
      await completion.promise;
    });

    act(() => {
      mounted.root.render(
        <StudioCopilotPanel {...props} proposal={null} isAcceptingProposal={false} />,
      );
    });
    expect(document.activeElement).toBe(instruction);
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
