/**
 * DR-014 structural contract for the EPUB package: the produced archive is
 * unzipped and its XHTML/OPF is asserted directly because EPUBCheck is not
 * available locally (skipped, recorded in the delivery evidence). Every
 * assertion fails loudly when the package markers disappear: `dc:language`
 * derived from the content instead of the former hardcoded `en`, the EPUB 3
 * required `dcterms:modified`, the shipped reading stylesheet referenced from
 * the OPF and every chapter, and preserved fenced code blocks plus image
 * references instead of silent deletion.
 */

import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import JSZip from "jszip";
import { describe, expect, it } from "vitest";
import type * as A from "../../src/contexts/studio/application/ports/artifact_gateway.js";
import { FilesystemExportArtifactGateway } from "../../src/contexts/studio/infrastructure/export_artifact_files.js";

const capturedAt = new Date("2026-08-25T00:00:00.000Z");

const chineseChapters: readonly A.ArtifactChapter[] = [
  {
    title: "第一章 落雪",
    contentMarkdown: [
      "# 第一章 落雪",
      "",
      "第一段正文，写的是雪。",
      "",
      "![雪夜插图](images/snow.png)",
      "",
      "```ts",
      "const snow = 1 < 2;",
      "```",
      "",
      "结尾段落。",
    ].join("\n"),
  },
];

const englishChapters: readonly A.ArtifactChapter[] = [
  { title: "Chapter One", contentMarkdown: "The snow kept falling." },
];

/** Short Chinese prose whose Latin letters all live inside code and URLs. */
const codeHeavyChineseChapters: readonly A.ArtifactChapter[] = [
  {
    title: "第一章 落雪",
    contentMarkdown:
      "# 第一章 落雪\n\n第一段正文。\n\n```ts\nconst snow = 1 < 2;\n```\n\n![雪夜](images/snow.png)",
  },
];

interface EpubParts {
  readonly packageXml: string;
  readonly chapterXml: string;
  readonly stylesheet: string;
}

async function renderEpub(renderedChapters: readonly A.ArtifactChapter[]): Promise<EpubParts> {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-epub-"));
  const gateway = new FilesystemExportArtifactGateway(directory);
  const request: A.ArtifactWriteRequest = {
    projectId: "project-1",
    artifactId: "epub-package",
    format: "epub",
    projectTitle: "雪国纪事",
    chapters: renderedChapters,
    capturedAt,
  };
  const evidence = await gateway.writeSnapshotArtifact(request);
  const zip = await JSZip.loadAsync(
    await gateway.readArtifactBytes({
      projectId: "project-1",
      artifactId: "epub-package",
      format: "epub",
      relativePath: evidence.relativePath,
      sizeBytes: evidence.sizeBytes,
      checksumSha256: evidence.checksumSha256,
    }),
  );
  const part = async (path: string): Promise<string> => {
    const entry = zip.file(path);
    if (entry === null) throw new Error(`Missing EPUB part ${path}.`);
    return entry.async("string");
  };
  return {
    packageXml: await part("OEBPS/content.opf"),
    chapterXml: await part("OEBPS/chapter-001.xhtml"),
    stylesheet: await part("OEBPS/styles/reading.css"),
  };
}

describe("EPUB package contract (DR-014)", () => {
  it("publishes the content language instead of a hardcoded locale", async () => {
    const chinese = await renderEpub(chineseChapters);
    expect(chinese.packageXml).toContain("<dc:language>zh</dc:language>");
    expect(chinese.chapterXml).toContain('xml:lang="zh"');
    const codeHeavy = await renderEpub(codeHeavyChineseChapters);
    expect(codeHeavy.packageXml).toContain("<dc:language>zh</dc:language>");
    const english = await renderEpub(englishChapters);
    expect(english.packageXml).toContain("<dc:language>en</dc:language>");
  });

  it("declares the EPUB 3 modification timestamp from the export time", async () => {
    const parts = await renderEpub(chineseChapters);
    expect(parts.packageXml).toContain(
      '<meta property="dcterms:modified">2026-08-25T00:00:00Z</meta>',
    );
  });

  it("ships a CJK reading stylesheet referenced from the OPF and every chapter", async () => {
    const parts = await renderEpub(chineseChapters);
    expect(parts.packageXml).toMatch(
      /<item\b[^>]*href="styles\/reading\.css"[^>]*media-type="text\/css"/u,
    );
    expect(parts.chapterXml).toMatch(
      /<link\b[^>]*rel="stylesheet"[^>]*href="styles\/reading\.css"/u,
    );
    expect(parts.stylesheet).toContain("text-indent: 2em");
    expect(parts.stylesheet).toContain("line-height:");
    expect(parts.stylesheet).toMatch(/font-family:[^;]*(Songti|SimSun|Noto Serif CJK)/u);
  });

  it("keeps fenced code blocks and image references in the chapter XHTML", async () => {
    const parts = await renderEpub(chineseChapters);
    expect(parts.chapterXml).toMatch(/<pre><code[^>]*>const snow = 1 &lt; 2;<\/code><\/pre>/u);
    expect(parts.chapterXml).toContain('class="image-placeholder"');
    expect(parts.chapterXml).toContain("雪夜插图");
    expect(parts.chapterXml).toContain("images/snow.png");
    expect(parts.chapterXml).toContain("第一段正文，写的是雪。");
  });
});
