/**
 * DR-013 structural contract for the DOCX manuscript: the produced package is
 * unzipped in the test and its OOXML is asserted directly, because no Word/WPS
 * renderer is available in CI. Every assertion fails loudly when the layout
 * markers disappear: explicit East-Asian fonts (`w:rFonts w:eastAsia`), an
 * exact two-character first-line indent (`w:firstLineChars="200"` with a
 * twip fallback), a page break before every chapter (`w:pageBreakBefore`), a
 * refreshed table-of-contents field (`w:instrText` + `w:updateFields`), and a
 * chapter body that never repeats the chapter title. Image and code-fence
 * handling stays out of the DOCX contract; DR-014 owns the EPUB side.
 */

import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import JSZip from "jszip";
import { describe, expect, it } from "vitest";
import type * as A from "../../src/contexts/studio/application/ports/artifact_gateway.js";
import { FilesystemExportArtifactGateway } from "../../src/contexts/studio/infrastructure/export_artifact_files.js";

const chapters: readonly A.ArtifactChapter[] = [
  {
    title: "第一章 落雪",
    contentMarkdown: "# 第一章 落雪\n\n第一段正文，写的是雪。\n\n第二段正文，仍是雪。",
  },
  {
    title: "第二章 归途",
    contentMarkdown: "第二章 归途\n\n归途的正文。",
  },
];

interface DocxParts {
  readonly documentXml: string;
  readonly stylesXml: string;
  readonly settingsXml: string;
}

async function renderDocx(renderedChapters: readonly A.ArtifactChapter[]): Promise<DocxParts> {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-docx-"));
  const gateway = new FilesystemExportArtifactGateway(directory);
  const request: A.ArtifactWriteRequest = {
    projectId: "project-1",
    artifactId: "docx-layout",
    format: "docx",
    projectTitle: "雪国纪事",
    chapters: renderedChapters,
  };
  const evidence = await gateway.writeSnapshotArtifact(request);
  const zip = await JSZip.loadAsync(
    await gateway.readArtifactBytes({
      projectId: "project-1",
      artifactId: "docx-layout",
      format: "docx",
      relativePath: evidence.relativePath,
      sizeBytes: evidence.sizeBytes,
      checksumSha256: evidence.checksumSha256,
    }),
  );
  const part = async (path: string): Promise<string> => {
    const entry = zip.file(path);
    if (entry === null) throw new Error(`Missing DOCX part ${path}.`);
    return entry.async("string");
  };
  return {
    documentXml: await part("word/document.xml"),
    stylesXml: await part("word/styles.xml"),
    settingsXml: await part("word/settings.xml"),
  };
}

/** Every literal text node of the document body, in document order. */
function textNodes(xml: string): string[] {
  return [...xml.matchAll(/<w:t(?:\s[^>]*)?>([^<]*)<\/w:t>/gu)].map((match) => match[1] ?? "");
}

/** Every `w:ind` element as a raw tag so each indent can be inspected alone. */
function indentTags(xml: string): string[] {
  return [...xml.matchAll(/<w:ind\b[^>]*\/>/gu)].map((match) => match[0]);
}

describe("DOCX manuscript layout (DR-013)", () => {
  it("declares an East-Asian font with a Latin counterpart in defaults and runs", async () => {
    const parts = await renderDocx(chapters);
    expect(parts.stylesXml).toContain('w:eastAsia="SimSun"');
    expect(parts.stylesXml).toContain('w:ascii="Times New Roman"');
    expect(parts.documentXml).toContain('w:eastAsia="SimSun"');
  });

  it("indents every body paragraph by exactly two CJK characters", async () => {
    const parts = await renderDocx(chapters);
    const bodyIndents = indentTags(parts.documentXml);
    expect(bodyIndents).toHaveLength(3);
    for (const indent of bodyIndents) {
      expect(indent).toContain('w:firstLineChars="200"');
      expect(indent).toContain('w:firstLine="480"');
    }
    const [defaultIndent] = indentTags(parts.stylesXml);
    expect(defaultIndent).toContain('w:firstLineChars="200"');
    expect(defaultIndent).toContain('w:firstLine="480"');
  });

  it("breaks the page before every chapter", async () => {
    const parts = await renderDocx(chapters);
    expect([...parts.documentXml.matchAll(/<w:pageBreakBefore\b[^>]*\/>/gu)]).toHaveLength(
      chapters.length,
    );
  });

  it("embeds a table-of-contents field and refreshes fields on open", async () => {
    const parts = await renderDocx(chapters);
    const instructions = [
      ...parts.documentXml.matchAll(/<w:instrText(?:\s[^>]*)?>([^<]*)<\/w:instrText>/gu),
    ].map((match) => match[1] ?? "");
    expect(
      instructions.some(
        (instruction) => instruction.includes("TOC") && instruction.includes("&quot;1-1&quot;"),
      ),
    ).toBe(true);
    expect([...parts.documentXml.matchAll(/w:fldCharType="begin"/gu)].length).toBeGreaterThan(0);
    expect(parts.documentXml).toMatch(/w:fldCharType="end"/u);
    expect(parts.settingsXml).toContain("<w:updateFields");
  });

  it("renders each chapter title once instead of repeating it in the body", async () => {
    const parts = await renderDocx(chapters);
    const nodes = textNodes(parts.documentXml);
    expect(nodes.filter((node) => node === "第一章 落雪")).toHaveLength(1);
    expect(nodes.filter((node) => node === "第二章 归途")).toHaveLength(1);
    expect(nodes).toContain("第一段正文，写的是雪。");
    expect(nodes).toContain("归途的正文。");
  });

  it("keeps a first body line that is not the chapter title", async () => {
    const parts = await renderDocx([
      { title: "第三章 破晓", contentMarkdown: "破晓之前，最冷。\n\n第二段正文。" },
    ]);
    const nodes = textNodes(parts.documentXml);
    expect(nodes.filter((node) => node === "第三章 破晓")).toHaveLength(1);
    expect(nodes).toContain("破晓之前，最冷。");
    expect(nodes).toContain("第二段正文。");
  });
});
