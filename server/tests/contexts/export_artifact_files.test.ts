import { createHash } from "node:crypto";
import { mkdtemp, readdir, readFile, stat, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import JSZip from "jszip";
import { describe, expect, it } from "vitest";

import {
  type ArtifactWriteRequest,
  type ExportArtifactGateway,
  type ProjectTitleLookup,
  SnapshotArtifactService,
} from "../../src/contexts/studio/application/export_artifact_service.js";
import type {
  AppendArtifactInput,
  ExportArtifactRecord,
  ExportSnapshotDocument,
  ExportSnapshotMaterialization,
  ExportStore,
} from "../../src/contexts/studio/application/ports/export_store.js";
import type { ProjectScope } from "../../src/contexts/studio/application/ports/studio_store.js";
import { NotFoundError } from "../../src/contexts/studio/domain/exceptions.js";
import { FilesystemExportArtifactGateway } from "../../src/contexts/studio/infrastructure/export_artifact_files.js";
import type { Principal } from "../../src/shared/application/ports/auth.js";
import { InvalidOperationError } from "../../src/shared/domain/exceptions.js";

const principal: Principal = {
  sessionId: "session-1",
  kind: "owner",
  ownerId: "owner-1",
  expiresAt: null,
};

const projectTitles: ProjectTitleLookup = { findProject: () => ({ title: "Ashfall" }) };

function request(format: ArtifactWriteRequest["format"], artifactId: string): ArtifactWriteRequest {
  return {
    projectId: "project-1",
    artifactId,
    format,
    projectTitle: "Ashfall",
    chapters: [
      {
        title: "Chapter one",
        contentMarkdown: "## First *bold* scene\n\n[Linked words](https://example.test)",
      },
      { title: "Chapter two", contentMarkdown: "Second paragraph." },
    ],
  };
}

async function zipText(zip: JSZip, path: string): Promise<string> {
  const entry = zip.file(path);
  if (entry === null) {
    throw new Error(`Missing ZIP entry ${path}.`);
  }
  return entry.async("string");
}

describe("FilesystemExportArtifactGateway", () => {
  it("keeps Markdown byte-stable, records final integrity, and leaves no temporary file", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-"));
    const gateway = new FilesystemExportArtifactGateway(directory);
    const evidence = await gateway.writeSnapshotArtifact(request("markdown", "artifact-md"));
    const path = await gateway.resolveArtifactFile(evidence.relativePath);
    const bytes = await readFile(path);

    expect(bytes.toString("utf8")).toBe(
      "# Ashfall\n\n## First *bold* scene\n\n[Linked words](https://example.test)\n\nSecond paragraph.\n",
    );
    expect(evidence.relativePath).toBe("exports/project-1/artifact-md.md");
    expect(evidence.sizeBytes).toBe((await stat(path)).size);
    expect(evidence.checksumSha256).toBe(createHash("sha256").update(bytes).digest("hex"));
    expect(await readdir(join(directory, "exports", "project-1"))).toEqual(["artifact-md.md"]);
  });

  it("writes DOCX and EPUB with plain chapter text and their required structures", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-"));
    const gateway = new FilesystemExportArtifactGateway(directory);
    const docx = await gateway.writeSnapshotArtifact(request("docx", "artifact-docx"));
    const docxZip = await JSZip.loadAsync(
      await readFile(await gateway.resolveArtifactFile(docx.relativePath)),
    );
    const documentXml = await zipText(docxZip, "word/document.xml");

    expect(documentXml).toContain("Ashfall");
    expect(documentXml).toContain("Chapter one");
    expect(documentXml).toContain("First bold scene");
    expect(documentXml).toContain("Linked words");
    expect(documentXml).not.toContain("*");
    expect(documentXml).not.toContain("## First");

    const epub = await gateway.writeSnapshotArtifact(request("epub", "artifact-epub"));
    const epubZip = await JSZip.loadAsync(
      await readFile(await gateway.resolveArtifactFile(epub.relativePath)),
    );
    expect(Object.keys(epubZip.files)).toEqual(
      expect.arrayContaining([
        "OEBPS/chapter-001.xhtml",
        "OEBPS/chapter-002.xhtml",
        "OEBPS/nav.xhtml",
        "OEBPS/toc.ncx",
      ]),
    );
    const chapter = await zipText(epubZip, "OEBPS/chapter-001.xhtml");
    expect(chapter).toContain("<h1>Chapter one</h1>");
    expect(chapter).toContain("<p>First bold scene</p>");
    expect(chapter).toContain("<p>Linked words</p>");
    expect(chapter).not.toContain("*");
    expect(chapter).not.toContain("##");
    expect(await zipText(epubZip, "OEBPS/nav.xhtml")).toContain("chapter-001.xhtml");
    expect(await zipText(epubZip, "OEBPS/toc.ncx")).toContain("chapter-002.xhtml");
  });

  it("refuses traversal and symlinked files outside the export root", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-"));
    const gateway = new FilesystemExportArtifactGateway(directory);
    const evidence = await gateway.writeSnapshotArtifact(request("markdown", "artifact-safe"));
    const outside = join(directory, "outside.md");
    await writeFile(outside, "outside");
    await symlink(outside, join(directory, "exports", "project-1", "outside.md"));

    await expect(gateway.resolveArtifactFile("../../outside.md")).rejects.toThrow(NotFoundError);
    await expect(gateway.resolveArtifactFile("exports/project-1/outside.md")).rejects.toThrow(
      NotFoundError,
    );
    await expect(gateway.resolveArtifactFile(evidence.relativePath)).resolves.toContain(
      "artifact-safe.md",
    );
  });
});

class FakeExportStore implements ExportStore {
  readonly appended: ExportArtifactRecord[] = [];

  constructor(private readonly documents: readonly ExportSnapshotDocument[]) {}

  materializeArtifactSnapshot(): ExportSnapshotMaterialization {
    return { snapshotId: "snapshot-1", documents: this.documents };
  }

  appendArtifact(
    _scope: ProjectScope,
    projectId: string,
    input: AppendArtifactInput,
  ): ExportArtifactRecord {
    const record: ExportArtifactRecord = { projectId, ...input };
    this.appended.push(record);
    return record;
  }

  listProjectArtifacts(): ExportArtifactRecord[] {
    return [...this.appended];
  }

  findProjectArtifact(
    _scope: ProjectScope,
    _projectId: string,
    artifactId: string,
  ): ExportArtifactRecord {
    const record = this.appended.find((item) => item.id === artifactId);
    if (record === undefined) {
      throw new NotFoundError();
    }
    return record;
  }
}

class RecordingGateway implements ExportArtifactGateway {
  readonly writes: ArtifactWriteRequest[] = [];

  async writeSnapshotArtifact(requestValue: ArtifactWriteRequest) {
    this.writes.push(requestValue);
    return {
      relativePath: `exports/${requestValue.projectId}/${requestValue.artifactId}.${requestValue.format}`,
      sizeBytes: 1,
      checksumSha256: "a".repeat(64),
    };
  }

  async resolveArtifactFile(relativePath: string): Promise<string> {
    return `/safe/${relativePath}`;
  }
}

function snapshotDocument(id: string, kind: string, title: string): ExportSnapshotDocument {
  return {
    snapshotDocumentId: `snap-${id}`,
    documentId: id,
    revisionId: `revision-${id}`,
    kind,
    title,
    contentMarkdown: `${title} content`,
    metadataJson: "{}",
    position: 1,
  };
}

describe("SnapshotArtifactService", () => {
  it("renders all formats from the ordered frozen chapters and records each artifact", async () => {
    const store = new FakeExportStore([
      snapshotDocument("outline", "outline", "Outline"),
      snapshotDocument("second", "chapter", "Second"),
      snapshotDocument("first", "chapter", "First"),
    ]);
    const gateway = new RecordingGateway();
    let sequence = 0;
    const service = new SnapshotArtifactService(store, projectTitles, gateway, {
      now: () => new Date("2026-08-25T00:00:00.000Z"),
      newId: () => `artifact-${++sequence}`,
    });

    const records = await Promise.all(
      (["markdown", "docx", "epub"] as const).map((format) =>
        service.materializeSnapshotArtifact(principal, "project-1", format),
      ),
    );
    expect(gateway.writes.map((write) => write.chapters.map((chapter) => chapter.title))).toEqual([
      ["Second", "First"],
      ["Second", "First"],
      ["Second", "First"],
    ]);
    expect(records.map((record) => record.snapshotId)).toEqual([
      "snapshot-1",
      "snapshot-1",
      "snapshot-1",
    ]);
    expect(service.catalogProjectArtifacts(principal, "project-1")).toHaveLength(3);
    await expect(service.locateArtifactFile(principal, "project-1", "artifact-1")).resolves.toBe(
      "/safe/exports/project-1/artifact-1.markdown",
    );
  });

  it("rejects a snapshot without chapters before a file or record is written", async () => {
    const store = new FakeExportStore([snapshotDocument("outline", "outline", "Outline")]);
    const gateway = new RecordingGateway();
    const service = new SnapshotArtifactService(store, projectTitles, gateway);

    await expect(
      service.materializeSnapshotArtifact(principal, "project-1", "markdown"),
    ).rejects.toThrow(InvalidOperationError);
    expect(gateway.writes).toEqual([]);
    expect(store.appended).toEqual([]);
  });
});
