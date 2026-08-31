import { createHash } from "node:crypto";
import { mkdtemp, readdir, readFile, symlink, unlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import JSZip from "jszip";
import { describe, expect, it } from "vitest";
import type * as A from "../../src/contexts/studio/application/export_artifact_service.js";
import {
  ExportArtifactWriteError,
  NotFoundError,
} from "../../src/contexts/studio/domain/exceptions.js";
import { FilesystemExportArtifactGateway } from "../../src/contexts/studio/infrastructure/export_artifact_files.js";

type ReadEvidence = Pick<A.ArtifactFileEvidence, "relativePath" | "sizeBytes" | "checksumSha256">;

const defaultChapters = [
  {
    title: "Chapter one",
    contentMarkdown: "## First *bold* scene\n\n[Linked words](https://example.test)",
  },
  { title: "Chapter two", contentMarkdown: "Second paragraph." },
];

function request(
  format: A.ArtifactWriteRequest["format"],
  artifactId: string,
  projectId = "project-1",
): A.ArtifactWriteRequest {
  return {
    projectId,
    artifactId,
    format,
    projectTitle: "Ashfall",
    chapters: defaultChapters,
  };
}

function readRequest(
  evidence: ReadEvidence,
  artifactId: string,
  format: A.ArtifactWriteRequest["format"],
  projectId = "project-1",
): A.ArtifactReadRequest {
  const { relativePath, sizeBytes, checksumSha256 } = evidence;
  return { projectId, artifactId, format, relativePath, sizeBytes, checksumSha256 };
}

async function zipText(zip: JSZip, path: string): Promise<string> {
  const entry = zip.file(path);
  if (entry === null) throw new Error(`Missing ZIP entry ${path}.`);
  return entry.async("string");
}

async function artifactBytes(
  gateway: FilesystemExportArtifactGateway,
  format: A.ArtifactWriteRequest["format"],
  artifactId: string,
): Promise<Buffer> {
  const evidence = await gateway.writeSnapshotArtifact(request(format, artifactId));
  return gateway.readArtifactBytes(readRequest(evidence, artifactId, format));
}

describe("FilesystemExportArtifactGateway", () => {
  it("keeps Markdown byte-stable, evidence-backed, and temporary-free", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-"));
    const gateway = new FilesystemExportArtifactGateway(directory);
    const evidence = await gateway.writeSnapshotArtifact(request("markdown", "artifact-md"));
    const bytes = await gateway.readArtifactBytes(readRequest(evidence, "artifact-md", "markdown"));

    expect(bytes.toString("utf8")).toBe(
      "# Ashfall\n\n## First *bold* scene\n\n[Linked words](https://example.test)\n\nSecond paragraph.\n",
    );
    expect(evidence.relativePath).toBe("exports/project-1/artifact-md.md");
    expect(evidence.sizeBytes).toBe(bytes.length);
    expect(evidence.checksumSha256).toBe(createHash("sha256").update(bytes).digest("hex"));
    expect(await readdir(join(directory, "exports", "project-1"))).toEqual(["artifact-md.md"]);
  });

  it("writes DOCX and EPUB with plain text and required structures", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-"));
    const gateway = new FilesystemExportArtifactGateway(directory);
    const docx = await JSZip.loadAsync(await artifactBytes(gateway, "docx", "artifact-docx"));
    const documentXml = await zipText(docx, "word/document.xml");
    expect(documentXml).toContain("Ashfall");
    expect(documentXml).toContain("First bold scene");
    expect(documentXml).toContain("Linked words");
    expect(documentXml).not.toContain("*");

    const epub = await JSZip.loadAsync(await artifactBytes(gateway, "epub", "artifact-epub"));
    for (const path of [
      "OEBPS/chapter-001.xhtml",
      "OEBPS/chapter-002.xhtml",
      "OEBPS/nav.xhtml",
      "OEBPS/toc.ncx",
    ]) {
      expect(Object.keys(epub.files)).toContain(path);
    }
    expect(await zipText(epub, "OEBPS/chapter-001.xhtml")).toContain("<p>First bold scene</p>");
    expect(await zipText(epub, "OEBPS/nav.xhtml")).toContain("chapter-001.xhtml");
    expect(await zipText(epub, "OEBPS/toc.ncx")).toContain("chapter-002.xhtml");
  });

  it("rejects tampered bytes, symlink leaves, and noncanonical paths", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-"));
    const gateway = new FilesystemExportArtifactGateway(directory);
    const evidence = await gateway.writeSnapshotArtifact(request("markdown", "artifact-safe"));
    const input = readRequest(evidence, "artifact-safe", "markdown");
    const target = join(directory, "exports", "project-1", "artifact-safe.md");
    await writeFile(target, "tampered");
    await expect(gateway.readArtifactBytes(input)).rejects.toThrow(NotFoundError);
    await unlink(target);
    const outside = join(directory, "outside.md");
    await writeFile(outside, "outside");
    await symlink(outside, target);
    await expect(gateway.readArtifactBytes(input)).rejects.toThrow(NotFoundError);
    await expect(
      gateway.readArtifactBytes({ ...input, relativePath: "../../outside.md" }),
    ).rejects.toThrow(NotFoundError);
  });

  it("never clobbers an existing artifact id and leaves no temporary file", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-"));
    const gateway = new FilesystemExportArtifactGateway(directory);
    const first = await gateway.writeSnapshotArtifact(request("markdown", "repeat"));
    const original = await gateway.readArtifactBytes(readRequest(first, "repeat", "markdown"));
    await expect(gateway.writeSnapshotArtifact(request("markdown", "repeat"))).rejects.toThrow();
    expect(await gateway.readArtifactBytes(readRequest(first, "repeat", "markdown"))).toEqual(
      original,
    );
    expect(await readdir(join(directory, "exports", "project-1"))).toEqual(["repeat.md"]);
  });

  it("does not delete a replacement that takes the published path before rollback", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-"));
    const gateway = new FilesystemExportArtifactGateway(directory);
    const evidence = await gateway.writeSnapshotArtifact(request("markdown", "replaced"));
    const target = join(directory, evidence.relativePath);
    await unlink(target);
    await writeFile(target, "replacement bytes");

    await evidence.rollback();

    await expect(readFile(target, "utf8")).resolves.toBe("replacement bytes");
  });

  it("classifies known OS write failures without swallowing renderer defects", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-"));
    const gateway = new FilesystemExportArtifactGateway(directory);
    await expect(
      gateway.writeSnapshotArtifact(request("markdown", "artifact-long", "p".repeat(300))),
    ).rejects.toThrow(ExportArtifactWriteError);

    const rendererDefect = request("markdown", "artifact-bug");
    Object.defineProperty(rendererDefect, "chapters", {
      get() {
        throw new TypeError("simulated renderer defect");
      },
    });
    await expect(gateway.writeSnapshotArtifact(rendererDefect)).rejects.toThrow(
      "simulated renderer defect",
    );
  });

  // XML 1.0 sanitation regressions for both zipped formats live in
  // export_artifact_xml.test.ts (file-size split).
});
