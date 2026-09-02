import { mkdir, mkdtemp, readFile, symlink, truncate, unlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import type { ArtifactReadRequest } from "../../src/contexts/studio/application/export_artifact_service.js";
import {
  EXPORT_CAPACITY_LIMITS,
  ExportCapacityExceededError,
} from "../../src/contexts/studio/domain/exceptions.js";
import { FilesystemExportArtifactGateway } from "../../src/contexts/studio/infrastructure/export_artifact_files.js";

function readRequest(): ArtifactReadRequest {
  return {
    projectId: "project-1",
    artifactId: "artifact",
    format: "markdown",
    relativePath: "exports/project-1/artifact.md",
    sizeBytes: EXPORT_CAPACITY_LIMITS.artifact_bytes + 1,
    checksumSha256: "0".repeat(64),
  };
}

describe("export artifact bounded read", () => {
  it("rejects an oversized descriptor before whole-file allocation", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-read-capacity-"));
    const projectDirectory = join(directory, "exports", "project-1");
    await mkdir(projectDirectory, { recursive: true });
    const target = join(projectDirectory, "artifact.md");
    await writeFile(target, "");
    await truncate(target, EXPORT_CAPACITY_LIMITS.artifact_bytes + 1);

    await expect(
      new FilesystemExportArtifactGateway(directory).readArtifactBytes(readRequest()),
    ).rejects.toBeInstanceOf(ExportCapacityExceededError);
  });

  it("does not relabel unexpected I/O or programming failures as not found", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-read-errors-"));
    const gateway = new FilesystemExportArtifactGateway(directory);
    const ioFailure = Object.assign(new Error("simulated read failure"), { code: "EIO" });
    const ioRequest = readRequest();
    Object.defineProperty(ioRequest, "projectId", {
      get() {
        throw ioFailure;
      },
    });
    await expect(gateway.readArtifactBytes(ioRequest)).rejects.toBe(ioFailure);

    const defect = new TypeError("simulated artifact reader defect");
    const defectRequest = readRequest();
    Object.defineProperty(defectRequest, "format", {
      get() {
        throw defect;
      },
    });
    await expect(gateway.readArtifactBytes(defectRequest)).rejects.toBe(defect);
  });

  it("preserves a symlink replacement encountered after rollback quarantine", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-artifact-rollback-link-"));
    const outside = join(directory, "outside.md");
    await writeFile(outside, "outside bytes");
    const gateway = new FilesystemExportArtifactGateway(directory, {
      afterRollbackQuarantine: async (quarantine) => {
        await unlink(quarantine);
        await symlink(outside, quarantine);
      },
    });
    const evidence = await gateway.writeSnapshotArtifact({
      projectId: "project-1",
      artifactId: "artifact",
      format: "markdown",
      projectTitle: "Rollback",
      chapters: [{ title: "Chapter", contentMarkdown: "Body" }],
    });
    const target = join(directory, evidence.relativePath);

    await expect(evidence.rollback()).rejects.toThrow(/preserved a replacement/i);
    await expect(readFile(target, "utf8")).resolves.toBe("outside bytes");
  });
});
