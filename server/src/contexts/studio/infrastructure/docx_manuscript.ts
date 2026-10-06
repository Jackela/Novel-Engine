/**
 * DOCX manuscript assembly for Chinese-first exports. Word and WPS used to
 * open the artifact with an empty `<w:rPrDefault/>`, so the East-Asian glyphs
 * fell back to the reader's default face and the body lost its two-character
 * first-line indent, chapter page breaks, and table of contents. The body is
 * rendered as running text: markdown markers are stripped, the leading title
 * line that repeats the chapter heading is skipped, and every layout marker is
 * emitted through the `docx` package's own API (no hand-written OOXML).
 */

import type { EventEmitter } from "node:events";

import {
  AlignmentType,
  Document,
  HeadingLevel,
  type IStylesOptions,
  LineRuleType,
  Packer,
  Paragraph,
  TableOfContents,
} from "docx";

import type { ArtifactWriteRequest } from "../application/ports/artifact_gateway.js";
import { xmlSafeText } from "./epub_xml.js";
import { plainText, stripRepeatedTitleLine } from "./export_markdown_body.js";

/** Songti/SimSun carries Han glyphs; Times New Roman covers Latin and digits. */
const MANUSCRIPT_FONT = {
  ascii: "Times New Roman",
  cs: "Times New Roman",
  eastAsia: "SimSun",
  hAnsi: "Times New Roman",
  hint: "eastAsia",
} as const;

// 12pt body text makes two Han characters measure 24pt = 480 twips. The
// character-based indent is repeated so Word keeps "2 characters" even after a
// reader changes the font size.
const BODY_SIZE_HALF_POINTS = 24;
const BODY_LINE_SPACING_TWIPS = 360;
const FIRST_LINE_INDENT_TWIPS = 480;
const FIRST_LINE_INDENT_HUNDREDTHS = 200;
const TITLE_SIZE_HALF_POINTS = 36;
const CHAPTER_SIZE_HALF_POINTS = 32;

const BODY_INDENT = {
  firstLine: FIRST_LINE_INDENT_TWIPS,
  firstLineChars: FIRST_LINE_INDENT_HUNDREDTHS,
} as const;

const NO_INDENT = { firstLine: 0, firstLineChars: 0 } as const;

const BODY_SPACING = {
  after: 0,
  line: BODY_LINE_SPACING_TWIPS,
  lineRule: LineRuleType.AUTO,
} as const;

/**
 * Renders the frozen snapshot chapters into one DOCX stream: a centered title,
 * a table-of-contents field that Word refreshes on open, then one page-broken
 * heading plus indented body paragraphs per chapter. The stream is not
 * buffered here; the caller enforces the artifact byte budget.
 */
export function docxManuscriptStream(request: ArtifactWriteRequest): EventEmitter {
  const children: (Paragraph | TableOfContents)[] = [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      heading: HeadingLevel.TITLE,
      run: { font: MANUSCRIPT_FONT, size: TITLE_SIZE_HALF_POINTS },
      text: xmlSafeText(request.projectTitle),
    }),
    new TableOfContents("Contents", { headingStyleRange: "1-1", hyperlink: true }),
  ];
  for (const chapter of request.chapters) {
    children.push(
      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        pageBreakBefore: true,
        run: { font: MANUSCRIPT_FONT, size: CHAPTER_SIZE_HALF_POINTS },
        text: xmlSafeText(chapter.title),
      }),
      ...bodyParagraphs(chapter.title, chapter.contentMarkdown),
    );
  }
  return Packer.toStream(
    new Document({
      // Word/WPS must rebuild the TOC field on open instead of showing an
      // empty content control until the reader presses F9.
      features: { updateFields: true },
      styles: manuscriptStyles(),
      sections: [{ children }],
    }),
  );
}

function bodyParagraphs(title: string, contentMarkdown: string): Paragraph[] {
  const prose = plainText(stripRepeatedTitleLine(title, contentMarkdown));
  const paragraphs: Paragraph[] = [];
  for (const paragraph of prose.split(/\n\s*\n/)) {
    const text = xmlSafeText(paragraph.trim());
    if (text === "") continue;
    paragraphs.push(
      new Paragraph({
        indent: BODY_INDENT,
        run: { font: MANUSCRIPT_FONT, size: BODY_SIZE_HALF_POINTS },
        spacing: BODY_SPACING,
        text,
      }),
    );
  }
  return paragraphs;
}

/** Default typography applied to body text, titles, and chapter headings. */
function manuscriptStyles(): IStylesOptions {
  return {
    default: {
      document: {
        paragraph: { indent: BODY_INDENT, spacing: BODY_SPACING },
        run: { font: MANUSCRIPT_FONT, size: BODY_SIZE_HALF_POINTS },
      },
      heading1: {
        paragraph: { indent: NO_INDENT },
        run: { font: MANUSCRIPT_FONT, size: CHAPTER_SIZE_HALF_POINTS },
      },
      title: {
        paragraph: { indent: NO_INDENT },
        run: { font: MANUSCRIPT_FONT, size: TITLE_SIZE_HALF_POINTS },
      },
    },
  };
}
