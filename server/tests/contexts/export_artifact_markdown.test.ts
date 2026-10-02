/**
 * DR-015 structural contract for the Markdown artifact: every chapter keeps
 * its title in the exported file as a level-2 heading while the single level-1
 * heading stays reserved for the project title, a leading line that already
 * repeats the chapter title is dropped so the heading never appears twice, and
 * chapter order plus blank-line separators are deterministic so the output
 * stays byte-stable. Rendering goes through the real filesystem gateway, the
 * same surface the DOCX/EPUB structural tests use, and the exact-bytes
 * assertions fail loudly when a heading or separator disappears.
 */

import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import type * as A from "../../src/contexts/studio/application/ports/artifact_gateway.js";
import { FilesystemExportArtifactGateway } from "../../src/contexts/studio/infrastructure/export_artifact_files.js";

async function renderMarkdown(renderedChapters: readonly A.ArtifactChapter[]): Promise<string> {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-markdown-"));
  const gateway = new FilesystemExportArtifactGateway(directory);
  const request: A.ArtifactWriteRequest = {
    projectId: "project-1",
    artifactId: "markdown-structure",
    format: "markdown",
    projectTitle: "Ashfall",
    chapters: renderedChapters,
  };
  const evidence = await gateway.writeSnapshotArtifact(request);
  const bytes = await gateway.readArtifactBytes({
    projectId: "project-1",
    artifactId: "markdown-structure",
    format: "markdown",
    relativePath: evidence.relativePath,
    sizeBytes: evidence.sizeBytes,
    checksumSha256: evidence.checksumSha256,
  });
  await evidence.acknowledge();
  return bytes.toString("utf8");
}

describe("Markdown export structure", () => {
  it("gives every chapter its title as a level-2 heading without repeating it", async () => {
    const markdown = await renderMarkdown([
      {
        title: "第一章 落雪",
        contentMarkdown: "# 第一章 落雪\n\n第一段正文，写的是雪。",
      },
      {
        title: "第二章 归途",
        contentMarkdown: "第二章 归途\n\n归途的正文。",
      },
    ]);

    expect(markdown).toBe(
      "# Ashfall\n\n## 第一章 落雪\n\n第一段正文，写的是雪。\n\n## 第二章 归途\n\n归途的正文。\n",
    );
    const lines = markdown.split("\n");
    expect(lines[0]).toBe("# Ashfall");
    // Each chapter title appears exactly once, as the level-2 heading; the
    // repeated leading H1 (or plain title line) is gone.
    expect(lines.filter((line) => line.includes("第一章 落雪"))).toEqual(["## 第一章 落雪"]);
    expect(lines.filter((line) => line.includes("第二章 归途"))).toEqual(["## 第二章 归途"]);
    expect(lines).not.toContain("# 第一章 落雪");
    expect(lines).not.toContain("第一章 落雪");
    expect(lines).not.toContain("第二章 归途");
  });

  it("keeps an authored subheading that differs from the chapter title", async () => {
    const markdown = await renderMarkdown([
      {
        title: "Chapter One",
        contentMarkdown: "## A *bold* scene\n\n[Linked words](https://example.test)",
      },
    ]);

    expect(markdown).toBe(
      "# Ashfall\n\n## Chapter One\n\n## A *bold* scene\n\n[Linked words](https://example.test)\n",
    );
  });

  it("keeps chapter order and deterministic separators with padded and empty bodies", async () => {
    const markdown = await renderMarkdown([
      { title: "Alpha", contentMarkdown: "  alpha body  \n\n" },
      { title: "Beta", contentMarkdown: "" },
      { title: "Gamma", contentMarkdown: "\n\n# Gamma\n\ngamma body\n" },
    ]);

    expect(markdown).toBe(
      "# Ashfall\n\n## Alpha\n\nalpha body\n\n## Beta\n\n## Gamma\n\ngamma body\n",
    );
    const lines = markdown.split("\n");
    // An empty body still exports its heading, so no chapter silently vanishes.
    expect(lines.filter((line) => line === "## Beta")).toHaveLength(1);
    expect(markdown.indexOf("## Alpha")).toBeLessThan(markdown.indexOf("## Beta"));
    expect(markdown.indexOf("## Beta")).toBeLessThan(markdown.indexOf("## Gamma"));
    // Exactly one blank line between segments and between each heading and its
    // body, no runs of blank lines, and a single trailing newline: the
    // separators are deterministic.
    expect(markdown.match(/\n\n/gu)).toHaveLength(5);
    expect(markdown).not.toMatch(/\n{3,}/u);
    expect(markdown.endsWith("gamma body\n")).toBe(true);
    expect(lines[lines.length - 1]).toBe("");
    expect(lines[lines.length - 2]).toBe("gamma body");
  });
});
