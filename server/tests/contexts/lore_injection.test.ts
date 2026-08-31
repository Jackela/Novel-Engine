import { describe, expect, it } from "vitest";

import {
  DEFAULT_LOREBOOK_BUDGET_CHARACTERS,
  triggeredLoreSections,
} from "../../src/contexts/studio/application/lore_injection.js";
import {
  LOREBOOK_SUMMARY_CHARACTERS,
  type LoreEntrySource,
  loreEntrySummary,
  matchLoreEntriesWithRank,
} from "../../src/contexts/studio/application/lorebook.js";
import { buildProposalUserPrompt } from "../../src/contexts/studio/application/resident_context.js";
import { LOREBOOK_BEGIN } from "../../src/contexts/studio/application/sanitization.js";

function entry(overrides: Partial<LoreEntrySource> & { title: string }): LoreEntrySource {
  return {
    loreAliasesJson: "[]",
    status: "stable",
    contentMarkdown: "Reference prose.",
    ...overrides,
  };
}

describe("entry summary line (#445 summary source: the entry's own opening)", () => {
  it("flattens the first prose paragraph after leading headings", () => {
    const summary = loreEntrySummary(
      entry({
        title: "Mara",
        contentMarkdown:
          "# Mara\n\n**Mara** keeps [the archive](place.md) `locked`.\n\nSecond paragraph.",
      }),
    );
    expect(summary).toBe("Mara keeps the archive locked.");
  });

  it("truncates overlong openings at a word boundary with an ellipsis", () => {
    const long = "word ".repeat(120).trim();
    const summary = loreEntrySummary(entry({ title: "Mara", contentMarkdown: long }));
    expect(summary.startsWith("…")).toBe(false);
    expect(summary.endsWith("…")).toBe(true);
    expect(summary.length).toBeLessThanOrEqual(LOREBOOK_SUMMARY_CHARACTERS + 1);
    expect(summary).not.toContain("  ");
  });

  it("falls back to the flattened body when the text opens with headings only", () => {
    const summary = loreEntrySummary(
      entry({ title: "Mara", contentMarkdown: "## Mara\n### Early life" }),
    );
    expect(summary).toContain("Early life");
  });
});

describe("progressive disclosure under the injection budget (#445, ADR-0006)", () => {
  const matched = (entries: readonly LoreEntrySource[], resident: string, manuscript: string) =>
    triggeredLoreSections({ entries, resident, manuscript, budgetCharacters: 10_000 });

  it("expands every hit to full text while the section fits the budget", () => {
    const entries = [
      entry({ title: "Mara", contentMarkdown: "Mara keeps the flooded archive." }),
      entry({ title: "Sable", contentMarkdown: "Sable pilots the breakwater lights." }),
    ];
    const rendered = matched(entries, "Mara and Sable", "").join("\n");
    expect(rendered).toContain("### Mara\n\nMara keeps the flooded archive.");
    expect(rendered).toContain("### Sable\n\nSable pilots the breakwater lights.");
    expect(rendered).not.toContain("(summary only)");
  });

  it("keeps over-budget hits as summary lines instead of dropping them", () => {
    // The unique tail sentence sits past the summary cap, so its presence
    // would prove the full body leaked into the prompt.
    const body = `${"Long lore body padding. ".repeat(40)}TAIL-SENTENCE-BEYOND-THE-CAP`;
    const mara = entry({ title: "Mara", contentMarkdown: body });
    const entries = [mara, entry({ title: "Sable", contentMarkdown: "Tiny body." })];
    const rendered = triggeredLoreSections({
      entries,
      resident: "Mara Sable",
      manuscript: "",
      budgetCharacters: 1,
    }).join("\n");
    expect(rendered).toContain(LOREBOOK_BEGIN);
    expect(rendered).toContain("### Mara (summary only)");
    expect(rendered).toContain("### Sable (summary only)");
    expect(rendered).toContain(loreEntrySummary(mara));
    expect(rendered).not.toContain("TAIL-SENTENCE-BEYOND-THE-CAP");
  });

  it("upgrades a title hit before an alias hit when only one fits", () => {
    // Identical bodies make each promotion worth exactly the same delta, so
    // the budget admits exactly one full body: the title hit must win.
    const body = "Shared length body for both entries. ".repeat(10);
    const mara = entry({ title: "Mara", contentMarkdown: body });
    const sable = entry({
      title: "Sable",
      loreAliasesJson: '["gull pilot"]',
      contentMarkdown: body,
    });
    const render = (budgetCharacters: number) =>
      triggeredLoreSections({
        entries: [mara, sable],
        resident: "gull pilot and Mara",
        manuscript: "",
        budgetCharacters,
      }).join("\n");
    const floor = render(0);
    const full = render(10_000);
    const onePromotionBudget = floor.length + (full.length - floor.length) / 2;
    const promoted = render(onePromotionBudget);
    expect(promoted).toContain("### Mara\n\n");
    expect(promoted).toContain("### Sable (summary only)");
  });

  it("breaks promotion ties by reading order, keeping render order stable", () => {
    const body = "Equal length prose for both entries. ".repeat(10);
    const first = entry({ title: "First", contentMarkdown: body });
    const second = entry({
      title: "Second",
      loreAliasesJson: '["second key"]',
      contentMarkdown: body,
    });
    const render = (budgetCharacters: number) =>
      triggeredLoreSections({
        entries: [first, second],
        resident: "Second key and First",
        manuscript: "",
        budgetCharacters,
      }).join("\n");
    const floor = render(0);
    const full = render(10_000);
    const onePromotionBudget = floor.length + (full.length - floor.length) / 2;
    const promoted = render(onePromotionBudget);
    expect(promoted).toContain("### First\n\n");
    expect(promoted).toContain("### Second (summary only)");
    expect(promoted.indexOf("### First")).toBeLessThan(promoted.indexOf("### Second"));
  });

  it("renders no section at all when nothing matches, at any budget", () => {
    const entries = [entry({ title: "Mara", contentMarkdown: "Body." })];
    for (const budgetCharacters of [0, 1, DEFAULT_LOREBOOK_BUDGET_CHARACTERS]) {
      expect(
        triggeredLoreSections({ entries, resident: "", manuscript: "", budgetCharacters }),
      ).toEqual([]);
    }
  });

  it("is deterministic: repeated planning renders byte-identically", () => {
    const entries = [
      entry({
        title: "Mara",
        loreAliasesJson: '["the archivist"]',
        contentMarkdown: "One. ".repeat(30),
      }),
      entry({ title: "Sable", contentMarkdown: "Two. ".repeat(30) }),
      entry({ title: "Rho", contentMarkdown: "Three. ".repeat(30) }),
    ];
    const runs = [
      triggeredLoreSections({
        entries,
        resident: "the archivist, Sable and Rho",
        manuscript: "",
        budgetCharacters: 400,
      }),
      triggeredLoreSections({
        entries,
        resident: "the archivist, Sable and Rho",
        manuscript: "",
        budgetCharacters: 400,
      }),
      triggeredLoreSections({
        entries,
        resident: "the archivist, Sable and Rho",
        manuscript: "",
        budgetCharacters: 400,
      }),
    ];
    const [firstRun, secondRun, thirdRun] = runs;
    if (firstRun === undefined || secondRun === undefined || thirdRun === undefined) {
      throw new Error("Expected three deterministic rendering runs.");
    }
    expect(firstRun.length).toBeGreaterThan(0);
    expect(firstRun).toEqual(secondRun);
    expect(secondRun).toEqual(thirdRun);
  });

  it("keeps the un-budgeted call on the adjudicated default budget", () => {
    const body = "Promotion body shared by the pair. ".repeat(10);
    const mara = entry({ title: "Mara", contentMarkdown: body });
    const sable = entry({ title: "Sable", contentMarkdown: body });
    const corpora = { resident: "Mara and Sable", manuscript: "" };
    const ranks = matchLoreEntriesWithRank([mara, sable], corpora);
    expect(ranks.map((match) => match.rank)).toEqual(["title", "title"]);
    const render = (budgetCharacters: number | undefined) =>
      triggeredLoreSections({ entries: [mara, sable], ...corpora, budgetCharacters }).join("\n");
    // The default budget holds both full bodies at this fixture size.
    expect(render(undefined)).not.toContain("(summary only)");
    // Shrinking to one promotion below the default demotes exactly one entry.
    const floor = render(0);
    const full = render(DEFAULT_LOREBOOK_BUDGET_CHARACTERS);
    const onePromotionBudget = floor.length + (full.length - floor.length) / 2;
    const demoted = render(onePromotionBudget);
    expect(demoted).toContain("### Mara\n\n");
    expect(demoted).toContain("### Sable (summary only)");
  });

  it("surfaces every matched entry through buildProposalUserPrompt's single assembly", () => {
    const source = {
      outlineMarkdown: null,
      linkedBeat: null,
      volumes: [],
      chapters: [],
      targetDocumentId: "target",
    };
    const entries = [
      entry({
        title: "Mara",
        contentMarkdown: `${"Opening summary padding. ".repeat(40)}FULL-BODY-SENTENCE-NEVER-SHOWN`,
      }),
    ];
    const viaPrompt = buildProposalUserPrompt({
      operation: "generate",
      instruction: "",
      source,
      manuscriptMarkdown: "Mara appears.",
      loreEntries: entries,
      loreBudgetCharacters: 1,
    });
    expect(viaPrompt).toContain("### Mara (summary only)");
    expect(viaPrompt).not.toContain("FULL-BODY-SENTENCE-NEVER-SHOWN");
    // The prompt embeds the direct sections API's lore block byte-for-byte at
    // the same budget: every pipeline shares one assembly point.
    const directSections = triggeredLoreSections({
      entries,
      resident: "",
      manuscript: "Mara appears.",
      budgetCharacters: 1,
    }).join("\n");
    expect(viaPrompt).toContain(directSections);
  });
});
