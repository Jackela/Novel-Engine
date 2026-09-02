import { mkdir, mkdtemp, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { afterEach, describe, expect, it, vi } from "vitest";

import {
  EXPORT_CAPACITY_LIMITS,
  ExportCapacityExceededError,
} from "../../src/contexts/studio/domain/exceptions.js";
import type { ExportPublicationManifest } from "../../src/contexts/studio/infrastructure/export_artifact_publication.js";
import { publishArtifact } from "../../src/contexts/studio/infrastructure/export_artifact_publication.js";
import { readManifestEvidence } from "../../src/contexts/studio/infrastructure/export_publication_manifest_evidence.js";

const directories: string[] = [];

afterEach(async () => {
  vi.restoreAllMocks();
  await Promise.all(directories.splice(0).map((directory) => rm(directory, { recursive: true })));
});

const record: ExportPublicationManifest = {
  version: 1,
  publication_id: "publication",
  artifact_id: "artifact",
  project_id: "project",
  format: "markdown",
  relative_path: "exports/project/artifact.md",
  stage_file: "artifact.publication.stage",
  size_bytes: 7,
  checksum_sha256: "a".repeat(64),
};

async function manifestPath(bytes: number): Promise<string> {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-manifest-capacity-"));
  directories.push(directory);
  const path = join(directory, "artifact.publication.manifest.json");
  const json = JSON.stringify(record);
  if (json.length > bytes) throw new Error("manifest fixture exceeds its target size");
  await writeFile(path, `${json}${" ".repeat(bytes - json.length)}`);
  return path;
}

describe("publication manifest byte capacity", () => {
  it("accepts and parses exactly 16,384 raw bytes", async () => {
    const path = await manifestPath(EXPORT_CAPACITY_LIMITS.manifest_bytes);

    const evidence = await readManifestEvidence(
      path,
      "artifact.publication.manifest.json",
      "project",
    );

    expect(evidence.record).toEqual(record);
  });

  it("rejects byte 16,385 before UTF-8 decode or JSON parse", async () => {
    const path = await manifestPath(EXPORT_CAPACITY_LIMITS.manifest_bytes + 1);
    const parse = vi.spyOn(JSON, "parse");

    await expect(
      readManifestEvidence(path, "artifact.publication.manifest.json", "project"),
    ).rejects.toBeInstanceOf(ExportCapacityExceededError);
    expect(parse).not.toHaveBeenCalled();
  });

  it("rejects an oversized generated manifest before creating publication files", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-generated-manifest-capacity-"));
    directories.push(directory);
    const projectDirectory = join(directory, "exports", "project");
    await mkdir(projectDirectory, { recursive: true });

    await expect(
      publishArtifact({
        projectDirectory,
        target: join(projectDirectory, "artifact.md"),
        relativePath: `exports/project/${"x".repeat(EXPORT_CAPACITY_LIMITS.manifest_bytes)}.md`,
        projectId: "project",
        artifactId: "artifact",
        format: "markdown",
        contents: Buffer.from("bounded artifact"),
        newId: () => "publication",
      }),
    ).rejects.toMatchObject({ resource: "manifest_bytes" });
    await expect(readdir(projectDirectory)).resolves.toEqual([]);
  });
});
