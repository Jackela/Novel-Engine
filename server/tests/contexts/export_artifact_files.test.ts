import { createHash } from "node:crypto";
import { mkdir, mkdtemp, readdir, readFile, symlink, unlink, writeFile } from "node:fs/promises";
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
  const bytes = await gateway.readArtifactBytes(readRequest(evidence, artifactId, format));
  await evidence.acknowledge();
  return bytes;
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
    const staging = join(directory, "exports", "project-1", ".staging");
    expect((await readdir(staging)).sort()).toEqual([
      expect.stringMatching(/^artifact-md\..+\.manifest\.json$/),
      expect.stringMatching(/^artifact-md\..+\.stage$/),
    ]);
    await evidence.acknowledge();
    expect((await readdir(join(directory, "exports", "project-1"))).sort()).toEqual([
      ".staging",
      "artifact-md.md",
    ]);
    await expect(readdir(staging)).resolves.toEqual([]);
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

  it("rejects a symlinked exports root before creating anything outside", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-"));
    const outside = await mkdtemp(join(tmpdir(), "novel-engine-artifact-outside-"));
    await symlink(outside, join(directory, "exports"), "dir");
    const gateway = new FilesystemExportArtifactGateway(directory);

    await expect(
      gateway.writeSnapshotArtifact(request("markdown", "artifact-link", "project-link")),
    ).rejects.toThrow("Export directory is not a real directory.");
    await expect(readdir(outside)).resolves.toEqual([]);
  });

  it("rejects a symlinked project directory before publishing outside", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-"));
    const outside = await mkdtemp(join(tmpdir(), "novel-engine-artifact-outside-"));
    await mkdir(join(directory, "exports"));
    await symlink(outside, join(directory, "exports", "project-link"), "dir");
    const gateway = new FilesystemExportArtifactGateway(directory);

    await expect(
      gateway.writeSnapshotArtifact(request("markdown", "artifact-link", "project-link")),
    ).rejects.toThrow("Export directory is not a real directory.");
    await expect(readdir(outside)).resolves.toEqual([]);
  });

  it("rejects a symlinked staging directory before writing outside", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-"));
    const outside = await mkdtemp(join(tmpdir(), "novel-engine-artifact-outside-"));
    const projectDirectory = join(directory, "exports", "project-link");
    await mkdir(projectDirectory, { recursive: true });
    await symlink(outside, join(projectDirectory, ".staging"), "dir");
    const gateway = new FilesystemExportArtifactGateway(directory);

    await expect(
      gateway.writeSnapshotArtifact(request("markdown", "artifact-link", "project-link")),
    ).rejects.toThrow("Export staging path is not a real directory.");
    await expect(readdir(outside)).resolves.toEqual([]);
  });

  it("never clobbers an existing artifact id and leaves no temporary file", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-"));
    const gateway = new FilesystemExportArtifactGateway(directory);
    const first = await gateway.writeSnapshotArtifact(request("markdown", "repeat"));
    const original = await gateway.readArtifactBytes(readRequest(first, "repeat", "markdown"));
    await first.acknowledge();
    await expect(gateway.writeSnapshotArtifact(request("markdown", "repeat"))).rejects.toThrow();
    expect(await gateway.readArtifactBytes(readRequest(first, "repeat", "markdown"))).toEqual(
      original,
    );
    expect((await readdir(join(directory, "exports", "project-1"))).sort()).toEqual([
      ".staging",
      "repeat.md",
    ]);
    await expect(readdir(join(directory, "exports", "project-1", ".staging"))).resolves.toEqual([]);
  });

  it("keeps shared staging stable while another format acknowledges", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-"));
    const firstGateway = new FilesystemExportArtifactGateway(directory);
    const first = await firstGateway.writeSnapshotArtifact(request("markdown", "parallel-md"));
    let announceReady: (() => void) | undefined;
    let releaseWrite: (() => void) | undefined;
    const ready = new Promise<void>((resolve) => {
      announceReady = resolve;
    });
    const blocked = new Promise<void>((resolve) => {
      releaseWrite = resolve;
    });
    const secondGateway = new FilesystemExportArtifactGateway(directory, {
      afterStagingReady: async () => {
        announceReady?.();
        await blocked;
      },
    });
    const pending = secondGateway.writeSnapshotArtifact(request("docx", "parallel-docx"));
    await ready;

    await first.acknowledge();
    releaseWrite?.();
    const second = await pending;
    await second.acknowledge();

    expect((await readdir(join(directory, "exports", "project-1"))).sort()).toEqual([
      ".staging",
      "parallel-docx.docx",
      "parallel-md.md",
    ]);
    await expect(readdir(join(directory, "exports", "project-1", ".staging"))).resolves.toEqual([]);
  });

  it("does not delete a replacement that takes the published path before rollback", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-"));
    const gateway = new FilesystemExportArtifactGateway(directory);
    const evidence = await gateway.writeSnapshotArtifact(request("markdown", "replaced"));
    const target = join(directory, evidence.relativePath);
    await unlink(target);
    await writeFile(target, "replacement bytes");

    await expect(evidence.rollback()).rejects.toThrow(/preserved a replacement/i);

    await expect(readFile(target, "utf8")).resolves.toBe("replacement bytes");
    await expect(
      readdir(join(directory, "exports", "project-1", ".staging")),
    ).resolves.toHaveLength(2);
  });

  it("does not delete a replacement created after rollback quarantines its file", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-"));
    const gateway = new FilesystemExportArtifactGateway(directory, {
      afterRollbackQuarantine: async (_quarantine, target) => {
        await writeFile(target, "late replacement bytes");
      },
    });
    const evidence = await gateway.writeSnapshotArtifact(request("markdown", "late-replaced"));
    const target = join(directory, evidence.relativePath);

    await evidence.rollback();

    await expect(readFile(target, "utf8")).resolves.toBe("late replacement bytes");
  });

  it("preserves both replacements when rollback cannot restore its quarantine", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-"));
    const gateway = new FilesystemExportArtifactGateway(directory, {
      afterRollbackQuarantine: async (_quarantine, target) => {
        await writeFile(target, "late replacement bytes");
      },
    });
    const evidence = await gateway.writeSnapshotArtifact(request("markdown", "double-replaced"));
    const target = join(directory, evidence.relativePath);
    await unlink(target);
    await writeFile(target, "early replacement bytes");

    await expect(evidence.rollback()).rejects.toMatchObject({ code: "EEXIST" });

    await expect(readFile(target, "utf8")).resolves.toBe("late replacement bytes");
    const quarantines = (await readdir(join(directory, "exports", "project-1"))).filter((name) =>
      name.includes(".rollback-"),
    );
    expect(quarantines).toHaveLength(1);
    await expect(
      readFile(join(directory, "exports", "project-1", quarantines[0] ?? ""), "utf8"),
    ).resolves.toBe("early replacement bytes");
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

  it.each(["EXDEV", "ENOTSUP", "EOPNOTSUPP", "ENOSYS", "EMLINK"])(
    "classifies unsupported durable-write error %s",
    async (code) => {
      const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-"));
      const gateway = new FilesystemExportArtifactGateway(directory, {
        afterStagingReady: async () => {
          throw Object.assign(new Error("unsupported durable write"), { code });
        },
      });

      await expect(
        gateway.writeSnapshotArtifact(request("markdown", `artifact-${code.toLowerCase()}`)),
      ).rejects.toThrow(ExportArtifactWriteError);
    },
  );

  // XML 1.0 sanitation regressions for both zipped formats live in
  // export_artifact_xml.test.ts (file-size split).
});
