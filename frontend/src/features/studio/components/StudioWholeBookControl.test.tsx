import { getByRole, queryByRole } from "@testing-library/dom";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createMountHarness, deferred } from "@/test/harness";
import type { WholeBookPhase } from "../hooks/useWholeBookLoop";

import { StudioWholeBookControl } from "./StudioWholeBookControl";

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
});

function render(phase: WholeBookPhase, remaining = 3): HTMLDivElement {
  return harness.mount(
    <StudioWholeBookControl
      phase={phase}
      remaining={remaining}
      onStart={vi.fn()}
      onStop={vi.fn()}
    />,
  ).container;
}

describe("StudioWholeBookControl (#318)", () => {
  it("offers the start control while idle and reports the pending count", () => {
    const container = render({ kind: "idle" }, 2);
    const start = getByRole(container, "button", {
      name: /Generate whole book/i,
    });
    expect(start).toBeEnabled();
    expect(queryByRole(container, "button", { name: /Stop generating/i })).toBeNull();
  });

  it("disables start when every chapter already has an accepted AI revision", () => {
    const container = render({ kind: "idle" }, 0);
    expect(getByRole(container, "button", { name: /Generate whole book/i })).toBeDisabled();
  });

  it("shows progress and the stop control while running", () => {
    const container = render({ kind: "running", current: 2, total: 5 });
    expect(container.querySelector('[role="status"]')?.textContent).toContain(
      "Generating chapter 2 of 5",
    );
    expect(getByRole(container, "button", { name: /Stop generating/i })).toBeInTheDocument();
    expect(queryByRole(container, "button", { name: /Generate whole book/i })).toBeNull();
  });

  it("reports how much work a stopped run preserved", () => {
    const container = render({
      kind: "done",
      generated: 2,
      stoppedEarly: true,
    });
    expect(container.querySelector(".whole-book__outcome")?.textContent).toContain(
      "Stopped — 2 chapters accepted this run",
    );
  });

  it("surfaces a failed chapter through the alert role", () => {
    const container = render({
      kind: "failed",
      generated: 1,
      failedChapterTitle: "Chapter Two",
      message: "Provider exploded.",
    });
    const failure = getByRole(container, "alert");
    expect(failure.textContent).toContain("Failed on “Chapter Two”");
    expect(failure.textContent).toContain("Provider exploded.");
  });

  it("offers only audit refresh retry while an unknown whole-book outcome stays gated", () => {
    const onRetryProposalAudit = vi.fn();
    const mounted = harness.mount(
      <StudioWholeBookControl
        onRetryProposalAudit={onRetryProposalAudit}
        onStart={vi.fn()}
        onStop={vi.fn()}
        phase={{
          kind: "outcome_unknown",
          generated: 1,
          interruptedChapterTitle: "Chapter Two",
        }}
        proposalAuditStatus="audit_failed"
        proposalOutcomeUnknown
        remaining={2}
      />,
    );

    expect(getByRole(mounted.container, "alert").textContent).toContain(
      "proposal outcome is unknown",
    );
    expect(mounted.container.querySelectorAll("button")).toHaveLength(1);
    act(() => {
      getByRole(mounted.container, "button", { name: "Retry audit refresh" }).click();
    });
    expect(onRetryProposalAudit).toHaveBeenCalledOnce();
  });

  it("requires an explicit Generate another proposal action after audit success", () => {
    const onStart = vi.fn();
    const mounted = harness.mount(
      <StudioWholeBookControl
        onStart={onStart}
        onStop={vi.fn()}
        phase={{
          kind: "outcome_unknown",
          generated: 0,
          interruptedChapterTitle: "Chapter One",
        }}
        proposalAuditStatus="audit_succeeded"
        proposalOutcomeUnknown
        remaining={2}
      />,
    );

    expect(getByRole(mounted.container, "alert").textContent).toContain(
      "may already have been saved",
    );
    const generateAnother = getByRole(mounted.container, "button", {
      name: "Generate another proposal",
    });
    expect(queryByRole(mounted.container, "button", { name: /Generate whole book/i })).toBeNull();
    act(() => generateAnother.click());
    expect(onStart).toHaveBeenCalledOnce();
  });

  it("returns orphaned focus to the start command after a failed run settles", async () => {
    const command = deferred<void>();
    const onStart = vi.fn(() => command.promise);
    let phase: WholeBookPhase = { kind: "idle" };
    const content = () => (
      <StudioWholeBookControl phase={phase} remaining={3} onStart={onStart} onStop={vi.fn()} />
    );
    const mounted = harness.mount(content());
    const start = getByRole(mounted.container, "button", { name: /Generate whole book/i });
    start.focus();

    act(() => start.click());
    phase = { kind: "running", current: 1, total: 3 };
    act(() => mounted.root.render(content()));
    expect(document.activeElement).toBe(document.body);

    phase = {
      kind: "failed",
      generated: 0,
      failedChapterTitle: "Opening",
      message: "Provider unavailable.",
    };
    await act(async () => {
      mounted.root.render(content());
      command.resolve(undefined);
      await command.promise;
    });

    const retry = getByRole(mounted.container, "button", { name: /Generate whole book/i });
    expect(document.activeElement).toBe(retry);
  });

  it("returns orphaned Stop focus to the available start command after stopping", async () => {
    const activeRun = deferred<void>();
    const onStart = vi.fn(() => activeRun.promise);
    const onStop = vi.fn();
    let phase: WholeBookPhase = { kind: "idle" };
    const content = () => (
      <StudioWholeBookControl phase={phase} remaining={2} onStart={onStart} onStop={onStop} />
    );
    const mounted = harness.mount(content());
    act(() => {
      getByRole(mounted.container, "button", { name: /Generate whole book/i }).click();
    });
    phase = { kind: "running", current: 1, total: 2 };
    act(() => mounted.root.render(content()));
    const stop = getByRole(mounted.container, "button", { name: /Stop generating/i });
    stop.focus();
    act(() => stop.click());
    expect(onStop).toHaveBeenCalledOnce();

    phase = { kind: "done", generated: 0, stoppedEarly: true };
    act(() => mounted.root.render(content()));
    expect(document.activeElement).toBe(
      getByRole(mounted.container, "button", { name: /Generate whole book/i }),
    );

    await act(async () => {
      activeRun.resolve(undefined);
      await activeRun.promise;
    });
  });

  it("returns orphaned focus to the whole-book outcome when no start command remains", async () => {
    const command = deferred<void>();
    let phase: WholeBookPhase = { kind: "idle" };
    let remaining = 1;
    const content = () => (
      <StudioWholeBookControl
        phase={phase}
        remaining={remaining}
        onStart={() => command.promise}
        onStop={vi.fn()}
      />
    );
    const mounted = harness.mount(content());
    const start = getByRole(mounted.container, "button", { name: /Generate whole book/i });
    start.focus();

    act(() => start.click());
    phase = { kind: "running", current: 1, total: 1 };
    act(() => mounted.root.render(content()));

    phase = { kind: "done", generated: 1, stoppedEarly: false };
    remaining = 0;
    await act(async () => {
      mounted.root.render(content());
      command.resolve(undefined);
      await command.promise;
    });

    expect(getByRole(mounted.container, "button", { name: /Generate whole book/i })).toBeDisabled();
    expect(document.activeElement).toBe(
      mounted.container.querySelector('[aria-label="Whole book generation"]'),
    );
  });

  it("does not steal focus when the user moved to another control during a failed run", async () => {
    const command = deferred<void>();
    let phase: WholeBookPhase = { kind: "idle" };
    const content = () => (
      <StudioWholeBookControl
        phase={phase}
        remaining={3}
        onStart={() => command.promise}
        onStop={vi.fn()}
      />
    );
    const mounted = harness.mount(content());
    act(() => {
      getByRole(mounted.container, "button", { name: /Generate whole book/i }).click();
    });
    phase = { kind: "running", current: 1, total: 3 };
    act(() => mounted.root.render(content()));

    const otherButton = document.createElement("button");
    document.body.appendChild(otherButton);
    otherButton.focus();
    phase = {
      kind: "failed",
      generated: 0,
      failedChapterTitle: "Opening",
      message: "Provider unavailable.",
    };
    await act(async () => {
      mounted.root.render(content());
      command.resolve(undefined);
      await command.promise;
    });

    expect(document.activeElement).toBe(otherButton);
    otherButton.remove();
  });
});
