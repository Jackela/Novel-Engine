import { describe, expect, it } from "vitest";

import {
  planLoreInjections,
  triggeredLoreSections,
} from "../../src/contexts/studio/application/lore_injection.js";
import type { LoreEntrySource, LoreMatch } from "../../src/contexts/studio/application/lorebook.js";

function matchedEntriesWithObservedSources(count: number): {
  matches: LoreMatch[];
  reads: { content: number; title: number };
} {
  const reads = { content: 0, title: 0 };
  const matches = Array.from({ length: count }, (_, index): LoreMatch => {
    const source: LoreEntrySource = {
      loreAliasesJson: "[]",
      status: "stable",
      get title() {
        reads.title += 1;
        return `Entry ${index}`;
      },
      get contentMarkdown() {
        reads.content += 1;
        return `Opening ${index}. ${"Detailed lore. ".repeat(30)}`;
      },
    };
    return { entry: source, rank: index % 2 === 0 ? "title" : "alias" };
  });
  return { matches, reads };
}

describe("linear lore injection planning", () => {
  it("snapshots every matched source once while planning M and 2M entries", () => {
    for (const count of [12, 24]) {
      const observed = matchedEntriesWithObservedSources(count);
      const plan = planLoreInjections(observed.matches, 20_000);

      expect(plan).toHaveLength(count);
      expect(observed.reads).toEqual({ content: count, title: count });
    }
  });

  it("promotes at the exact rendered budget and keeps the summary one character below it", () => {
    const contentMarkdown = "x".repeat(300);
    const input = {
      entries: [
        {
          title: "Mara",
          loreAliasesJson: "[]",
          status: "stable" as const,
          contentMarkdown,
        },
      ],
      resident: "Mara",
      manuscript: "",
    };
    const fullyRendered = triggeredLoreSections({
      ...input,
      budgetCharacters: 10_000,
    }).join("\n");

    expect(
      triggeredLoreSections({
        ...input,
        budgetCharacters: fullyRendered.length,
      }).join("\n"),
    ).toBe(fullyRendered);
    expect(
      triggeredLoreSections({
        ...input,
        budgetCharacters: fullyRendered.length - 1,
      }).join("\n"),
    ).toContain("### Mara (summary only)");
  });
});
