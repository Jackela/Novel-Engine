import { getByRole } from "@testing-library/dom";
import { afterEach, describe, expect, it } from "vitest";

import { createMountHarness } from "@/test/harness";

import { BODY_BUDGET_LIMIT_BYTES } from "../bodyBudget";
import { StudioBodyBudget } from "./StudioBodyBudget";

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
});

function render(draft: string): HTMLDivElement {
  return harness.mount(<StudioBodyBudget draft={draft} />).container;
}

describe("StudioBodyBudget (DR-048)", () => {
  it("shows the draft's word count and byte size against the documented 1 MiB limit", () => {
    const container = render("The harbor bell rang twice.");

    expect(container.querySelector(".editor-body-budget")?.getAttribute("data-level")).toBe("ok");
    expect(container).toHaveTextContent("Draft 27 B of 1.0 MB · 5 words");
    expect(container.querySelector('[role="alert"]')).toBeNull();
  });

  it("counts Han characters individually, like the server word count", () => {
    const container = render("港口的钟响了两下");
    const summary = container.querySelector(".editor-body-budget")?.textContent ?? "";

    // Eight Han characters, 24 UTF-8 bytes — no collapsing into one word.
    expect(summary).toContain("Draft 24 B of 1.0 MB");
    expect(summary).toContain("· 8 words");
  });

  it("warns (politely) once the draft nears the save limit", () => {
    const container = render("a".repeat(950_000));

    expect(container.querySelector(".editor-body-budget")?.getAttribute("data-level")).toBe("near");
    expect(getByRole(container, "status")).toHaveTextContent(
      "Approaching the 1.0 MB save limit — consider splitting this chapter.",
    );
  });

  it("names the split remedy assertively once the draft exceeds the limit", () => {
    const container = render("a".repeat(BODY_BUDGET_LIMIT_BYTES + 1));

    expect(container.querySelector(".editor-body-budget")?.getAttribute("data-level")).toBe("over");
    expect(getByRole(container, "alert")).toHaveTextContent(
      "Over the 1.0 MB save limit. Split this chapter before saving; the draft stays in the editor.",
    );
  });
});
