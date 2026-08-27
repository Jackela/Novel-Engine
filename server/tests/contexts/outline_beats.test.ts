import { describe, expect, it } from "vitest";

import { splitOutlineBeats } from "../../src/contexts/studio/application/outline_beats.js";

/**
 * The beat contract (#313): a beat is one `##`/`###` section of the project's
 * outline document. A heading line is the beat title; the body until the next
 * heading is the beat content; text before the first heading is preamble and
 * never becomes a beat.
 */
describe("splitOutlineBeats", () => {
  it("returns no beats when the outline has no headings", () => {
    expect(
      splitOutlineBeats("Just some prose without any structure at all.\n\nSecond line.\n"),
    ).toEqual([]);
  });

  it("returns no beats for empty or blank outlines", () => {
    expect(splitOutlineBeats("")).toEqual([]);
    expect(splitOutlineBeats("\n\n   \n")).toEqual([]);
  });

  it("keeps text before the first heading out of the beats", () => {
    const outline = [
      "# Story Outline",
      "",
      "Working notes nobody should generate against.",
      "",
      "## The Storm",
      "",
      "Rain floods the harbour.",
    ].join("\n");
    expect(splitOutlineBeats(outline)).toEqual([
      { title: "The Storm", content: "Rain floods the harbour." },
    ]);
  });

  it("splits every heading into its own beat with trimmed bodies", () => {
    const outline = [
      "## Opening",
      "",
      "Mara arrives.",
      "",
      "### The archive",
      "She finds the map.",
      "",
      "## Closing",
      "The ferry leaves.",
    ].join("\n");
    expect(splitOutlineBeats(outline)).toEqual([
      { title: "Opening", content: "Mara arrives." },
      { title: "The archive", content: "She finds the map." },
      { title: "Closing", content: "The ferry leaves." },
    ]);
  });

  it("allows empty beats between headings and trims them to an empty body", () => {
    const outline = ["## One", "", "", "## Two", "Body.", "## Three"].join("\n");
    expect(splitOutlineBeats(outline)).toEqual([
      { title: "One", content: "" },
      { title: "Two", content: "Body." },
      { title: "Three", content: "" },
    ]);
  });

  it("keeps trailing text after the last heading in that beat", () => {
    const outline = ["## Final", "First line.", "Second line."].join("\n\n");
    expect(splitOutlineBeats(outline)).toEqual([
      { title: "Final", content: "First line.\n\nSecond line." },
    ]);
  });

  it("treats only ATX headings of level two and three as delimiters", () => {
    const outline = [
      "## Real",
      "Content.",
      "#### Not a beat boundary",
      "More content.",
      "# Neither is this",
      "Still more.",
      "##NotAHeading",
      "Ordinary paragraph text.",
    ].join("\n");
    expect(splitOutlineBeats(outline)).toEqual([
      {
        title: "Real",
        content:
          "Content.\n#### Not a beat boundary\nMore content.\n# Neither is this\nStill more.\n##NotAHeading\nOrdinary paragraph text.",
      },
    ]);
  });

  it("trims surrounding whitespace from heading titles", () => {
    expect(splitOutlineBeats("##   Spaced out   \n\nBody.")[0]?.title).toBe("Spaced out");
  });
});
