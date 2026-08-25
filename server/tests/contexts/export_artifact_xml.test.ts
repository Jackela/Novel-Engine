import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import JSZip from "jszip";
import { describe, expect, it } from "vitest";
import type * as A from "../../src/contexts/studio/application/export_artifact_service.js";
import type { ExportArtifactFormat } from "../../src/contexts/studio/application/ports/export_store.js";
import { FilesystemExportArtifactGateway } from "../../src/contexts/studio/infrastructure/export_artifact_files.js";

const dirtyChapters = [
  {
    title: "Scene\u000B\uDC00",
    contentMarkdown: "Normal\u0001 prose\uD800 and a second paragraph.\n\nPlain tail.",
  },
];

function dirtyRequest(format: ExportArtifactFormat): A.ArtifactWriteRequest {
  return {
    projectId: "project-1",
    artifactId: "xml",
    format,
    projectTitle: "Clear\u0001\uD800 title",
    chapters: dirtyChapters,
  };
}

function readRequest(
  evidence: A.ArtifactFileEvidence,
  format: ExportArtifactFormat,
): A.ArtifactReadRequest {
  const { relativePath, sizeBytes, checksumSha256 } = evidence;
  return {
    projectId: "project-1",
    artifactId: "xml",
    format,
    relativePath,
    sizeBytes,
    checksumSha256,
  };
}

async function zipText(zip: JSZip, path: string): Promise<string> {
  const entry = zip.file(path);
  if (entry === null) throw new Error(`Missing ZIP entry ${path}.`);
  return entry.async("string");
}

function assertCleanXml(xml: string): void {
  expect(xml).toContain("Clear title");
  expect(xml).toContain("Normal prose");
  expect(xml).not.toContain("\u0001");
  expect(xml).not.toContain("\u000B");
  expect(xml).not.toContain("\uD800");
  expect(xml).not.toContain("\uFFFD");
}

/** XML 1.0 sanitation regressions for both zipped export formats. */
describe("export artifact XML sanitation", () => {
  it("removes invalid XML 1.0 characters while preserving normal DOCX text", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-"));
    const gateway = new FilesystemExportArtifactGateway(directory);
    const evidence = await gateway.writeSnapshotArtifact(dirtyRequest("docx"));
    const zip = await JSZip.loadAsync(
      await gateway.readArtifactBytes(readRequest(evidence, "docx")),
    );
    assertCleanXml(await zipText(zip, "word/document.xml"));
  });

  it("removes invalid XML 1.0 characters while preserving normal EPUB text", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-"));
    const gateway = new FilesystemExportArtifactGateway(directory);
    const evidence = await gateway.writeSnapshotArtifact(dirtyRequest("epub"));
    const zip = await JSZip.loadAsync(
      await gateway.readArtifactBytes(readRequest(evidence, "epub")),
    );
    const xml = (
      await Promise.all(
        ["OEBPS/chapter-001.xhtml", "OEBPS/nav.xhtml", "OEBPS/toc.ncx", "OEBPS/content.opf"].map(
          (path) => zipText(zip, path),
        ),
      )
    ).join("");
    assertCleanXml(xml);
  });
});
