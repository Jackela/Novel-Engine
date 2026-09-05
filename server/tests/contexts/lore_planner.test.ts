import { describe, expect, it } from "vitest";

import {
  iterateTriggeredLoreSections,
  type LorePlanningInstrumentation,
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
  it("constructs each summary/full representation once and renders one final pass for M and 2M", () => {
    for (const count of [12, 24]) {
      const observed = matchedEntriesWithObservedSources(count);
      const calls = { summary: 0, full: 0, finalPass: 0, lines: 0 };
      const instrumentation: LorePlanningInstrumentation = {
        onRepresentationPrepared: (mode) => {
          calls[mode] += 1;
        },
        onFinalRenderPass: () => {
          calls.finalPass += 1;
        },
        onLineRendered: () => {
          calls.lines += 1;
        },
      };
      const lines = [
        ...iterateTriggeredLoreSections({
          entries: observed.matches.map((match) => match.entry),
          resident: observed.matches.map((match) => match.entry.title).join(" "),
          manuscript: "",
          budgetCharacters: 20_000,
          instrumentation,
        }),
      ];

      expect(lines.length).toBeGreaterThan(count);
      expect(calls).toEqual({
        summary: count,
        full: count,
        finalPass: 1,
        lines: lines.length,
      });
    }
  });

  it("does not render later final-section lines after a consumer stops", () => {
    const rendered: string[] = [];
    const instrumentation: LorePlanningInstrumentation = {
      onRepresentationPrepared: () => undefined,
      onFinalRenderPass: () => undefined,
      onLineRendered: (line) => rendered.push(line),
    };
    const iterator = iterateTriggeredLoreSections({
      entries: [
        {
          title: "Mara",
          loreAliasesJson: "[]",
          status: "stable",
          contentMarkdown: "Mara keeps the archive.",
        },
      ],
      resident: "Mara",
      manuscript: "",
      budgetCharacters: 10_000,
      instrumentation,
    });

    expect(iterator.next().value).toBe("");
    expect(iterator.next().value).toContain("LOREBOOK");
    iterator.return(undefined);

    expect(rendered).toHaveLength(2);
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
