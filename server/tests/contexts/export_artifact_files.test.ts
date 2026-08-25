import { createHash } from "node:crypto";
import { mkdtemp, readdir, symlink, unlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import JSZip from "jszip";
import { describe, expect, it } from "vitest";
import type * as A from "../../src/contexts/studio/application/export_artifact_service.js";
import { SnapshotArtifactService } from "../../src/contexts/studio/application/export_artifact_service.js";
import type * as E from "../../src/contexts/studio/application/ports/export_store.js";
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
const projectTitles: A.ProjectTitleLookup = { findProject: () => ({ title: "Ashfall" }) };
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

  // XML 1.0 sanitation regressions for both zipped formats live in
  // export_artifact_xml.test.ts (file-size split).
});

class FakeExportStore implements E.ExportStore {
  readonly appended: E.ExportArtifactRecord[] = [];

  constructor(
    private readonly documents: readonly E.ExportSnapshotDocument[],
    private readonly appendFailure: Error | undefined = undefined,
  ) {}

  materializeArtifactSnapshot(): E.ExportSnapshotMaterialization {
    return { snapshotId: "snapshot-1", documents: this.documents };
  }

  appendArtifact(
    _scope: ProjectScope,
    projectId: string,
    input: E.AppendArtifactInput,
  ): E.ExportArtifactRecord {
    if (this.appendFailure !== undefined) throw this.appendFailure;
    const record: E.ExportArtifactRecord = { projectId, ...input };
    this.appended.push(record);
    return record;
  }

  listProjectArtifacts(): E.ExportArtifactRecord[] {
    return [...this.appended];
  }

  findProjectArtifact(
    _scope: ProjectScope,
    _projectId: string,
    artifactId: string,
  ): E.ExportArtifactRecord {
    const record = this.appended.find((item) => item.id === artifactId);
    if (record === undefined) throw new NotFoundError();
    return record;
  }
}

class RecordingGateway implements A.ExportArtifactGateway {
  readonly writes: A.ArtifactWriteRequest[] = [];
  readonly reads: A.ArtifactReadRequest[] = [];

  async writeSnapshotArtifact(
    requestValue: A.ArtifactWriteRequest,
  ): Promise<A.ArtifactFileEvidence> {
    this.writes.push(requestValue);
    const extension = requestValue.format === "markdown" ? "md" : requestValue.format;
    return {
      relativePath: `exports/${requestValue.projectId}/${requestValue.artifactId}.${extension}`,
      sizeBytes: 1,
      checksumSha256: "a".repeat(64),
      rollback: async () => undefined,
    };
  }

  async readArtifactBytes(input: A.ArtifactReadRequest): Promise<Buffer> {
    this.reads.push(input);
    return Buffer.from("safe");
  }
}

function snapshotDocument(id: string, kind: string, title: string): E.ExportSnapshotDocument {
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
  it("renders frozen chapters and forwards all authorized evidence for buffer delivery", async () => {
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
    expect(
      gateway.writes.every(
        (write) => write.chapters.map((chapter) => chapter.title).join() === "Second,First",
      ),
    ).toBe(true);
    expect(records.every((record) => record.snapshotId === "snapshot-1")).toBe(true);
    await expect(service.readArtifactBytes(principal, "project-1", "artifact-1")).resolves.toEqual(
      Buffer.from("safe"),
    );
    const [firstRecord] = records;
    if (firstRecord === undefined) throw new Error("Expected the first artifact record.");
    expect(gateway.reads).toEqual([readRequest(firstRecord, "artifact-1", "markdown")]);
  });

  it("refuses cross-project path substitution even when the other file is in root", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-"));
    const gateway = new FilesystemExportArtifactGateway(directory);
    const other = await gateway.writeSnapshotArtifact(request("markdown", "shared", "project-2"));
    const store = new FakeExportStore([]);
    store.appended.push({
      id: "shared",
      projectId: "project-1",
      snapshotId: "snapshot-1",
      format: "markdown",
      ...other,
      createdAt: new Date(),
    });
    await expect(
      new SnapshotArtifactService(store, projectTitles, gateway).readArtifactBytes(
        principal,
        "project-1",
        "shared",
      ),
    ).rejects.toThrow(NotFoundError);
  });

  it("rolls a new publication back when artifact persistence fails", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-"));
    const gateway = new FilesystemExportArtifactGateway(directory);
    const store = new FakeExportStore(
      [snapshotDocument("chapter", "chapter", "Chapter")],
      new Error("append failed"),
    );
    const service = new SnapshotArtifactService(store, projectTitles, gateway, {
      newId: () => "orphan",
    });
    await expect(
      service.materializeSnapshotArtifact(principal, "project-1", "markdown"),
    ).rejects.toThrow("append failed");
    expect(await readdir(join(directory, "exports", "project-1"))).toEqual([]);
  });

  it("rejects snapshots without chapters before a file or record is written", async () => {
    const store = new FakeExportStore([snapshotDocument("outline", "outline", "Outline")]);
    const gateway = new RecordingGateway();
    await expect(
      new SnapshotArtifactService(store, projectTitles, gateway).materializeSnapshotArtifact(
        principal,
        "project-1",
        "markdown",
      ),
    ).rejects.toThrow(InvalidOperationError);
    expect(gateway.writes).toEqual([]);
    expect(store.appended).toEqual([]);
  });
});
