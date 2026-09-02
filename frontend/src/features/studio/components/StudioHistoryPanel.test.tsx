import { getByRole } from "@testing-library/dom";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { revision } from "@/test/factories";
import { createMountHarness, deferred } from "@/test/harness";

import { StudioHistoryPanel } from "./StudioHistoryPanel";

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
});

const revisions = [
  revision("revision-old", { word_count: 2 }),
  revision("revision-other", {
    parent_revision_id: "revision-old",
    revision_number: 2,
    word_count: 2,
  }),
  revision("revision-current", {
    parent_revision_id: "revision-other",
    revision_number: 3,
    word_count: 2,
  }),
];

function renderHistory(restoringRevisionId: string | null): HTMLDivElement {
  return harness.mount(
    <StudioHistoryPanel
      revisions={revisions}
      loadedRevisionId="revision-current"
      onRestoreRevision={vi.fn()}
      restoringRevisionId={restoringRevisionId}
    />,
  ).container;
}

describe("StudioHistoryPanel", () => {
  it("loads older revisions with native semantics and moves focus at the terminal page", async () => {
    const load = deferred<void>();
    let hasOlderRevisions = true;
    let isLoadingOlder = false;
    const content = () => (
      <StudioHistoryPanel
        revisions={revisions}
        loadedRevisionId="revision-current"
        onRestoreRevision={vi.fn()}
        hasOlderRevisions={hasOlderRevisions}
        isLoadingOlder={isLoadingOlder}
        isLoadingHistory={isLoadingOlder}
        historyInitialized
        onLoadOlderRevisions={() => load.promise}
      />
    );
    const { container, root } = harness.mount(content());
    const button = getByRole(container, "button", { name: "Load older revisions" });
    const heading = getByRole(container, "heading", { name: "Revision history" });
    button.focus();
    act(() => {
      button.click();
      isLoadingOlder = true;
      root.render(content());
    });
    expect(button).toHaveAttribute("aria-busy", "true");

    await act(async () => {
      hasOlderRevisions = false;
      isLoadingOlder = false;
      load.resolve(undefined);
      await load.promise;
      root.render(content());
    });

    expect(document.activeElement).toBe(heading);
    expect(container).toHaveTextContent("All revisions loaded");
  });

  it("restores keyboard focus after a disabled load-more command loses focus on failure", async () => {
    const onLoadOlderRevisions = vi.fn().mockResolvedValue(undefined);
    let hasOlderRevisions = true;
    let isLoadingOlder = false;
    const content = () => (
      <StudioHistoryPanel
        revisions={revisions}
        loadedRevisionId="revision-current"
        onRestoreRevision={vi.fn()}
        hasOlderRevisions={hasOlderRevisions}
        isLoadingOlder={isLoadingOlder}
        historyInitialized
        onLoadOlderRevisions={onLoadOlderRevisions}
      />
    );
    const { container, root } = harness.mount(content());
    const button = getByRole(container, "button", { name: "Load older revisions" });
    button.focus();
    act(() => {
      button.click();
      isLoadingOlder = true;
      root.render(content());
    });
    const focusSink = document.createElement("button");
    document.body.append(focusSink);
    focusSink.focus();
    focusSink.remove();
    expect(document.activeElement).toBe(document.body);
    act(() => {
      isLoadingOlder = false;
      root.render(content());
    });

    expect(document.activeElement).toBe(button);
    const elsewhere = document.createElement("button");
    document.body.append(elsewhere);
    elsewhere.focus();
    act(() => {
      hasOlderRevisions = false;
      root.render(content());
    });
    expect(document.activeElement).toBe(elsewhere);
    elsewhere.remove();
  });

  it("preserves a different connected disabled control when keyboard loading fails", () => {
    let isLoadingOlder = false;
    const content = () => (
      <>
        <button type="button">Elsewhere</button>
        <StudioHistoryPanel
          revisions={revisions}
          loadedRevisionId="revision-current"
          onRestoreRevision={vi.fn()}
          hasOlderRevisions
          isLoadingOlder={isLoadingOlder}
          historyInitialized
          onLoadOlderRevisions={vi.fn()}
        />
      </>
    );
    const { container, root } = harness.mount(content());
    const loadButton = getByRole(container, "button", { name: "Load older revisions" });
    const elsewhere = getByRole(container, "button", { name: "Elsewhere" });
    if (!(elsewhere instanceof HTMLButtonElement)) throw new Error("Expected a button.");
    loadButton.focus();
    act(() => {
      loadButton.click();
      isLoadingOlder = true;
      root.render(content());
    });
    elsewhere.focus();
    elsewhere.disabled = true;
    expect(document.activeElement).toBe(elsewhere);
    act(() => {
      isLoadingOlder = false;
      root.render(content());
    });

    expect(document.activeElement).toBe(elsewhere);
  });

  it("preserves a different connected disabled control at the terminal page", () => {
    let hasOlderRevisions = true;
    let isLoadingOlder = false;
    const content = () => (
      <>
        <button type="button">Elsewhere</button>
        <StudioHistoryPanel
          revisions={revisions}
          loadedRevisionId="revision-current"
          onRestoreRevision={vi.fn()}
          hasOlderRevisions={hasOlderRevisions}
          isLoadingOlder={isLoadingOlder}
          historyInitialized
          onLoadOlderRevisions={vi.fn()}
        />
      </>
    );
    const { container, root } = harness.mount(content());
    const loadButton = getByRole(container, "button", { name: "Load older revisions" });
    const elsewhere = getByRole(container, "button", { name: "Elsewhere" });
    if (!(elsewhere instanceof HTMLButtonElement)) throw new Error("Expected a button.");
    loadButton.focus();
    act(() => {
      loadButton.click();
      isLoadingOlder = true;
      root.render(content());
    });
    elsewhere.focus();
    elsewhere.disabled = true;
    expect(document.activeElement).toBe(elsewhere);
    act(() => {
      hasOlderRevisions = false;
      isLoadingOlder = false;
      root.render(content());
    });

    expect(document.activeElement).toBe(elsewhere);
  });

  it("does not steal focus after a pointer loads the terminal page", async () => {
    const onLoadOlderRevisions = vi.fn().mockResolvedValue(undefined);
    let hasOlderRevisions = true;
    const content = () => (
      <>
        <button type="button">Elsewhere</button>
        <StudioHistoryPanel
          revisions={revisions}
          loadedRevisionId="revision-current"
          onRestoreRevision={vi.fn()}
          hasOlderRevisions={hasOlderRevisions}
          historyInitialized
          onLoadOlderRevisions={onLoadOlderRevisions}
        />
      </>
    );
    const { container, root } = harness.mount(content());
    const loadButton = getByRole(container, "button", { name: "Load older revisions" });
    const elsewhere = getByRole(container, "button", { name: "Elsewhere" });
    act(() => {
      loadButton.dispatchEvent(new MouseEvent("click", { bubbles: true, detail: 1 }));
      elsewhere.focus();
      hasOlderRevisions = false;
      root.render(content());
    });

    expect(document.activeElement).toBe(elsewhere);
  });

  it("visibly disables older traversal while a first-page refresh owns History", () => {
    const container = harness.mount(
      <StudioHistoryPanel
        revisions={revisions}
        loadedRevisionId="revision-current"
        onRestoreRevision={vi.fn()}
        hasOlderRevisions
        historyInitialized
        isLoadingHistory
        onLoadOlderRevisions={vi.fn()}
      />,
    ).container;

    const button = getByRole(container, "button", { name: "Refreshing revision history…" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
  });

  it("locks every restore action while one revision is restoring", () => {
    const container = renderHistory("revision-old");
    const restoreButtons = Array.from(
      container.querySelectorAll<HTMLButtonElement>(".ui-command--icon"),
    );

    expect(container.querySelector(".studio-inspector__panel")?.getAttribute("aria-busy")).toBe(
      "true",
    );
    expect(restoreButtons).toHaveLength(2);
    expect(restoreButtons.every((button) => button.disabled)).toBe(true);
    expect(restoreButtons[0]?.getAttribute("aria-busy")).toBe("true");
    expect(restoreButtons[0]?.getAttribute("aria-label")).toBe("Restoring revision revision");
    expect(restoreButtons[1]?.getAttribute("aria-label")).toBe("Restore revision revision");
  });

  it("keeps restore actions available when no revision is restoring", () => {
    const container = renderHistory(null);
    const restoreButtons = Array.from(
      container.querySelectorAll<HTMLButtonElement>(".ui-command--icon"),
    );

    expect(restoreButtons.every((button) => !button.disabled)).toBe(true);
    expect(container.querySelector(".studio-inspector__panel")?.getAttribute("aria-busy")).toBe(
      "false",
    );
  });

  it("does not steal focus after restore when the author moved elsewhere", async () => {
    const command = deferred<void>();
    const onRestore = vi.fn(() => command.promise);
    let restoringRevisionId: string | null = null;
    const content = () => (
      <>
        <button type="button">Fallback</button>
        <StudioHistoryPanel
          revisions={revisions}
          loadedRevisionId="revision-current"
          onRestoreRevision={onRestore}
          restoringRevisionId={restoringRevisionId}
        />
      </>
    );
    const { container, root } = harness.mount(content());
    const trigger = container.querySelector<HTMLButtonElement>(
      'button[aria-label="Restore revision revision"]',
    );
    const fallback = container.querySelector<HTMLButtonElement>("button");
    if (trigger === null || fallback === null) throw new Error("Expected focus targets.");

    trigger.focus();
    act(() => trigger.click());
    restoringRevisionId = "revision-old";
    act(() => root.render(content()));
    fallback.focus();
    await act(async () => {
      command.resolve(undefined);
      await command.promise;
    });
    expect(document.activeElement).toBe(fallback);

    restoringRevisionId = null;
    act(() => root.render(content()));
    expect(onRestore).toHaveBeenCalledWith("revision-old");
    expect(document.activeElement).toBe(fallback);
  });

  it("moves orphaned restore focus to another available revision command", async () => {
    const command = deferred<void>();
    const onRestore = vi.fn(() => command.promise);
    let restoringRevisionId: string | null = null;
    let loadedRevisionId = "revision-current";
    const content = () => (
      <StudioHistoryPanel
        revisions={revisions}
        loadedRevisionId={loadedRevisionId}
        onRestoreRevision={onRestore}
        restoringRevisionId={restoringRevisionId}
      />
    );
    const { container, root } = harness.mount(content());
    const trigger = container.querySelector<HTMLButtonElement>(".ui-command--icon");
    if (trigger === null) throw new Error("Expected a restore command.");

    trigger.focus();
    act(() => {
      trigger.click();
      restoringRevisionId = "revision-old";
      root.render(content());
    });
    await act(async () => {
      command.resolve(undefined);
      await command.promise;
    });
    restoringRevisionId = null;
    loadedRevisionId = "revision-old";
    act(() => root.render(content()));

    const available = container.querySelector<HTMLButtonElement>(".ui-command--icon");
    expect(available).not.toBeNull();
    expect(document.activeElement).toBe(available);
  });

  it("moves orphaned restore focus to the History heading when no command remains", async () => {
    const command = deferred<void>();
    const onlyRevision = revision("revision-only");
    let restoringRevisionId: string | null = null;
    let loadedRevisionId = "new-current";
    const content = () => (
      <StudioHistoryPanel
        revisions={[onlyRevision]}
        loadedRevisionId={loadedRevisionId}
        onRestoreRevision={() => command.promise}
        restoringRevisionId={restoringRevisionId}
      />
    );
    const { container, root } = harness.mount(content());
    const trigger = container.querySelector<HTMLButtonElement>(".ui-command--icon");
    const heading = container.querySelector<HTMLHeadingElement>("h2");
    if (trigger === null || heading === null) throw new Error("Expected History focus targets.");

    trigger.focus();
    act(() => {
      trigger.click();
      restoringRevisionId = onlyRevision.id;
      root.render(content());
    });
    await act(async () => {
      command.resolve(undefined);
      await command.promise;
    });
    restoringRevisionId = null;
    loadedRevisionId = onlyRevision.id;
    act(() => root.render(content()));

    expect(container.querySelector(".ui-command--icon")).toBeNull();
    expect(document.activeElement).toBe(heading);
  });
});
