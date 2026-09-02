import { describe, expect, it } from "vitest";

import {
  renderLoreSection,
  triggeredLoreSections,
} from "../../src/contexts/studio/application/lore_injection.js";
import {
  asLoreStatus,
  type LoreEntrySource,
  loreEntryKeys,
  matchLoreEntries,
  normalizeLoreAliases,
  parseLoreAliases,
} from "../../src/contexts/studio/application/lorebook.js";
import {
  assembleResidentContext,
  buildProposalUserPrompt,
  type ResidentChapterSource,
  type ResidentContextSource,
  residentMatchCorpus,
} from "../../src/contexts/studio/application/resident_context.js";
import {
  LOREBOOK_BEGIN,
  LOREBOOK_END,
  UNTRUSTED_MANUSCRIPT_BEGIN,
} from "../../src/contexts/studio/application/sanitization.js";

function entry(overrides: Partial<LoreEntrySource> & { title: string }): LoreEntrySource {
  return {
    loreAliasesJson: "[]",
    // Tests below exercise the matching semantics of injectable entries;
    // gating-specific cases override this to draft/deprecated (#444).
    status: "stable",
    contentMarkdown: "Reference prose.",
    ...overrides,
  };
}

describe("alias normalization (#315 write-path contract)", () => {
  it("trims each alias and drops empties", () => {
    expect(normalizeLoreAliases(["  the archivist ", "", "   ", "Mara"])).toEqual([
      "the archivist",
      "Mara",
    ]);
  });

  it("dedupes case-insensitively while keeping the first spelling", () => {
    expect(normalizeLoreAliases(["Mara", "the archivist", "MARA", "The Archivist"])).toEqual([
      "Mara",
      "the archivist",
    ]);
  });

  it("parses stored JSON defensively", () => {
    expect(parseLoreAliases('["a","b"]')).toEqual(["a", "b"]);
    for (const malformed of ["{}", '"text"', "[1,2]", "", "broken"]) {
      expect(parseLoreAliases(malformed)).toEqual([]);
    }
  });
});

describe("lore entry keys (#315: title is always an implicit key)", () => {
  it("extends the title with aliases and never replaces it", () => {
    const keys = loreEntryKeys(
      entry({ title: "Mara", loreAliasesJson: '["the archivist","Keeper of Floods"]' }),
    );
    expect(keys).toContain("Mara");
    expect(keys).toContain("the archivist");
    expect(keys).toContain("Keeper of Floods");
  });

  it("trims keys and drops blank ones, tolerating a whitespace-only title alias set", () => {
    expect(loreEntryKeys(entry({ title: "  Mara  ", loreAliasesJson: '[" ", "  "]' }))).toEqual([
      "Mara",
    ]);
  });
});

describe("keyword matching (#315 layer-2 selection)", () => {
  const corpora = (resident: string, manuscript: string) => ({ resident, manuscript });

  it("injects an entry when its title occurs in the manuscript", () => {
    const matched = matchLoreEntries([entry({ title: "Mara" })], corpora("", "Mara walked home."));
    expect(matched.map((candidate) => candidate.title)).toEqual(["Mara"]);
  });

  it("matches case-insensitively across either corpus", () => {
    const mara = entry({ title: "Mara", loreAliasesJson: '["the archivist"]' });
    const hitByResident = matchLoreEntries(
      [mara],
      corpora("THE ARCHIVIST keeps records.", "plain text"),
    );
    expect(hitByResident.map((candidate) => candidate.title)).toEqual(["Mara"]);

    const sable = entry({ title: "Sable" });
    const hitByManuscript = matchLoreEntries([sable], corpora("nothing here", "sable fur"));
    expect(hitByManuscript.map((candidate) => candidate.title)).toEqual(["Sable"]);
  });

  it("uses substring occurrence — a key inside a larger word still counts", () => {
    // Documented choice (#315): substring semantics; whole-token boundaries
    // are deliberately not required for multi-word fantasy names.
    const matched = matchLoreEntries([entry({ title: "Vant" })], corpora("", "the Vantrice"));
    expect(matched.map((candidate) => candidate.title)).toEqual(["Vant"]);
  });

  it("omits entries without any key occurrence", () => {
    const matched = matchLoreEntries(
      [entry({ title: "Vantris" }), entry({ title: "Mara" })],
      corpora("outline mentions Mara only", "manuscript also mentions Mara"),
    );
    expect(matched.map((candidate) => candidate.title)).toEqual(["Mara"]);
  });

  it("skips entries without injectable content even on a key hit", () => {
    const matched = matchLoreEntries(
      [
        entry({ title: "Empty", contentMarkdown: null }),
        entry({ title: "Blank", contentMarkdown: "   \n\t " }),
        entry({ title: "Real", contentMarkdown: "Body." }),
      ],
      corpora("Empty Blank Real", ""),
    );
    expect(matched.map((candidate) => candidate.title)).toEqual(["Real"]);
  });

  it("keeps matches in reading order of their documents", () => {
    const matched = matchLoreEntries(
      [entry({ title: "First" }), entry({ title: "Second" }), entry({ title: "Third" })],
      corpora("Third then First", "Second"),
    );
    expect(matched.map((candidate) => candidate.title)).toEqual(["First", "Second", "Third"]);
  });
});

describe("lifecycle gating (#444: only stable entries inject)", () => {
  const corpora = { resident: "Mara and Vex", manuscript: "" };

  it("injects a stable entry on a key hit", () => {
    const matched = matchLoreEntries([entry({ title: "Mara", status: "stable" })], corpora);
    expect(matched.map((candidate) => candidate.title)).toEqual(["Mara"]);
  });

  it("skips a draft entry even when its key occurs", () => {
    const matched = matchLoreEntries([entry({ title: "Mara", status: "draft" })], corpora);
    expect(matched).toEqual([]);
  });

  it("skips a deprecated entry even when its key occurs", () => {
    const matched = matchLoreEntries([entry({ title: "Mara", status: "deprecated" })], corpora);
    expect(matched).toEqual([]);
  });

  it("gates per entry: stable matches survive alongside gated-out neighbors", () => {
    const matched = matchLoreEntries(
      [
        entry({ title: "Mara", status: "draft" }),
        entry({ title: "Vex", status: "stable" }),
        entry({ title: "Rho", status: "deprecated" }),
      ],
      corpora,
    );
    expect(matched.map((candidate) => candidate.title)).toEqual(["Vex"]);
  });

  it("reads an unknown stored status as draft — fail-closed, never injectable", () => {
    expect(asLoreStatus("stable")).toBe("stable");
    expect(asLoreStatus("draft")).toBe("draft");
    expect(asLoreStatus("deprecated")).toBe("deprecated");
    for (const corrupted of ["", "STABLE", "archived", "null"]) {
      expect(asLoreStatus(corrupted)).toBe("draft");
    }
  });
});

describe("resident match corpus (#315 corpus equals the assembled resident view)", () => {
  function chapter(input: Partial<ResidentChapterSource> & { id: string }): ResidentChapterSource {
    return {
      kind: "chapter",
      title: input.id,
      position: 1,
      volumeId: null,
      contentMarkdown: "",
      ...input,
    };
  }

  it("joins outline, beat, prior story, and recent tail into one searchable text", () => {
    const source: ResidentContextSource = {
      outlineMarkdown: "## The Storm\nSable watches the harbour.",
      linkedBeat: { title: "The Storm", content: "Rain floods the harbour." },
      chapters: [chapter({ id: "one", position: 1, contentMarkdown: "Ends beside Cadera." })],
      targetDocumentId: "target",
    };
    const view = assembleResidentContext(source);
    const corpus = residentMatchCorpus(view);
    expect(corpus).toContain("Sable watches the harbour.");
    expect(corpus).toContain("Rain floods the harbour.");
    expect(corpus).toContain("Ends beside Cadera.");
    const corpusMatch = matchLoreEntries(
      [entry({ title: "Cadera" }), entry({ title: "Absentia" })],
      { resident: corpus, manuscript: "" },
    );
    expect(corpusMatch.map((candidate) => candidate.title)).toEqual(["Cadera"]);
  });
});

describe("lorebook section rendering (#315 reference-data layout)", () => {
  it("renders nothing when no entry matched", () => {
    expect(renderLoreSection([])).toEqual([]);
    expect(
      triggeredLoreSections({
        entries: [entry({ title: "Mara" })],
        resident: "",
        manuscript: "",
      }),
    ).toEqual([]);
  });

  it("renders one heading per matched entry over its writer-trusted content", () => {
    const sections = renderLoreSection([
      entry({
        title: "Mara",
        loreAliasesJson: '["the archivist"]',
        contentMarkdown: "Mara keeps\n\nthe flooded archive.",
      }),
      entry({ title: "Sable", contentMarkdown: "Gull-winged pilot of the breakwater." }),
    ]);
    const rendered = sections.join("\n");
    expect(rendered).toContain("### Mara");
    expect(rendered).toContain("Mara keeps");
    expect(rendered.indexOf("### Mara")).toBeLessThan(rendered.indexOf("### Sable"));
    expect(rendered).toContain("### Sable");
    // The section carries its own reference-data markers.
    expect(sections[0]).toBe("");
    expect(sections.some((line) => line === LOREBOOK_BEGIN)).toBe(true);
    expect(sections.at(-1)).toBe(LOREBOOK_END);
  });

  it("flattens a multi-line title onto one heading line while keeping content raw", () => {
    const rendered = renderLoreSection([
      entry({ title: "Weird\nTitle", contentMarkdown: "Body stays untouched." }),
    ]).join("\n");
    expect(rendered).toContain("### Weird Title");
    expect(rendered).toContain("Body stays untouched.");
  });
});

describe("proposal prompt composition (#315 lore between resident context and manuscript)", () => {
  function sourceWith(overrides: Partial<ResidentContextSource>): ResidentContextSource {
    return {
      outlineMarkdown: null,
      linkedBeat: null,
      chapters: [],
      targetDocumentId: "target",
      ...overrides,
    };
  }

  it("places the lorebook after the resident sections and before the untrusted block", () => {
    const userPrompt = buildProposalUserPrompt({
      operation: "generate",
      instruction: "Continue.",
      source: sourceWith({
        outlineMarkdown: "# Outline",
        chapters: [
          {
            id: "one",
            kind: "chapter",
            title: "One",
            position: 1,
            volumeId: null,
            contentMarkdown: "",
          },
        ],
      }),
      manuscriptMarkdown: "Mara appears in this draft.",
      loreEntries: [
        entry({ title: "Mara", contentMarkdown: "Mara keeps the flooded archive." }),
        entry({ title: "Vantris", contentMarkdown: "Never mentioned anywhere." }),
      ],
    });

    const order = [
      "LOREBOOK (reference entries triggered by their keys occurring above):",
      LOREBOOK_BEGIN,
      "### Mara",
      "Mara keeps the flooded archive.",
      UNTRUSTED_MANUSCRIPT_BEGIN,
    ].map((marker) => userPrompt.indexOf(marker));
    expect(order.every((index) => index >= 0)).toBe(true);
    expect([...order].sort((a, b) => a - b)).toEqual(order);
    expect(userPrompt).not.toContain("### Vantris");
    expect(userPrompt).not.toContain("Never mentioned anywhere.");
  });

  it("keeps the prompt byte-identical to the #314 shape when nothing matches", () => {
    const base = buildProposalUserPrompt({
      operation: "continue",
      instruction: "",
      source: sourceWith({ chapters: [] }),
      manuscriptMarkdown: "Solo draft.",
    });
    const withEmptyEntries = buildProposalUserPrompt({
      operation: "continue",
      instruction: "",
      source: sourceWith({ chapters: [] }),
      manuscriptMarkdown: "Solo draft.",
      loreEntries: [entry({ title: "Unmentioned", contentMarkdown: "Quiet pages." })],
    });
    expect(withEmptyEntries).toBe(base);
    expect(base.endsWith("[BEGIN UNTRUSTED MANUSCRIPT JSON]")).toBe(false);
  });
});
