import { afterEach, describe, expect, it, vi } from "vitest";

import { revision } from "@/test/factories";
import { createMountHarness } from "@/test/harness";

import { StudioHistoryPanel } from "./StudioHistoryPanel";

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
});

const revisions = [
  revision("revision-old", { content_markdown: "Old draft", word_count: 2 }),
  revision("revision-other", {
    parent_revision_id: "revision-old",
    revision_number: 2,
    content_markdown: "Other draft",
    word_count: 2,
  }),
  revision("revision-current", {
    parent_revision_id: "revision-other",
    revision_number: 3,
    content_markdown: "Current draft",
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
});
