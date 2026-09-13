import { createHash } from "node:crypto";
import { access, mkdir, readdir, stat, truncate, writeFile } from "node:fs/promises";
import { join } from "node:path";

import { afterEach, describe, expect, it } from "vitest";

import { EXPORT_CAPACITY_LIMITS } from "../../src/contexts/studio/domain/exceptions.js";
import { reconcileExportPublications } from "../../src/contexts/studio/infrastructure/export_publication_recovery.js";
import {
  addArtifact,
  cleanupRecoveryHarnesses,
  finalPath,
  openRecoveryHarness,
  preparePublication,
  projectDirectory,
} from "./export_publication_recovery_fixture.js";

afterEach(cleanupRecoveryHarnesses);

function sparseZeroChecksum(size: number): string {
  const digest = createHash("sha256");
  const chunk = Buffer.alloc(65_536);
  for (let offset = 0; offset < size; offset += chunk.length) {
    digest.update(chunk.subarray(0, Math.min(chunk.length, size - offset)));
  }
  return digest.digest("hex");
}

describe("bounded export publication recovery", () => {
  it("verifies a committed legacy artifact above 64 MiB without collecting its body", async () => {
    const value = await openRecoveryHarness();
    const artifactId = "legacy-oversized";
    const path = finalPath(value, artifactId);
    const size = EXPORT_CAPACITY_LIMITS.artifact_bytes + 1;
    await mkdir(projectDirectory(value), { recursive: true });
    await writeFile(path, "");
    await truncate(path, size);
    addArtifact(value, artifactId, {
      relativePath: `exports/${value.projectId}/${artifactId}.md`,
      sizeBytes: size,
      checksumSha256: sparseZeroChecksum(size),
    });

    const report = await reconcileExportPublications(value.studio.db, value.directory);

    expect(report.committedArtifactsVerified).toBe(1);
    expect((await stat(path)).size).toBe(size);
  });

  it("preserves oversized uncommitted evidence when manifest identity no longer proves cleanup authority", async () => {
    const value = await openRecoveryHarness();
    const artifactId = "oversized-manifest";
    await preparePublication(value, artifactId, Buffer.from("uncommitted bytes"));
    const staging = join(projectDirectory(value), ".staging");
    const names = await readdir(staging);
    const manifestName = names.find((name) => name.endsWith(".manifest.json"));
    const stageName = names.find((name) => name.endsWith(".stage"));
    if (manifestName === undefined || stageName === undefined) {
      throw new Error("expected recovery sidecars");
    }
    const manifest = join(staging, manifestName);
    await writeFile(manifest, "x".repeat(EXPORT_CAPACITY_LIMITS.manifest_bytes + 1));

    await expect(
      reconcileExportPublications(value.studio.db, value.directory),
    ).rejects.toMatchObject({ resource: "manifest_bytes" });
    await expect(access(manifest)).resolves.toBeUndefined();
    await expect(access(join(staging, stageName))).resolves.toBeUndefined();
    await expect(access(finalPath(value, artifactId))).resolves.toBeUndefined();
  });

  it("preserves oversized uncommitted evidence without cleanup authority", async () => {
    const value = await openRecoveryHarness();
    const artifactId = "unowned-oversized-manifest";
    await preparePublication(
      value,
      artifactId,
      Buffer.from("unowned uncommitted bytes"),
      "markdown",
      false,
    );
    const staging = join(projectDirectory(value), ".staging");
    const names = await readdir(staging);
    const manifestName = names.find((name) => name.endsWith(".manifest.json"));
    const stageName = names.find((name) => name.endsWith(".stage"));
    if (manifestName === undefined || stageName === undefined) {
      throw new Error("expected recovery sidecars");
    }
    const manifest = join(staging, manifestName);
    const stage = join(staging, stageName);
    const final = finalPath(value, artifactId);
    await writeFile(manifest, "x".repeat(EXPORT_CAPACITY_LIMITS.manifest_bytes + 1));

    await expect(
      reconcileExportPublications(value.studio.db, value.directory),
    ).rejects.toMatchObject({ resource: "manifest_bytes" });
    await expect(access(manifest)).resolves.toBeUndefined();
    await expect(access(stage)).resolves.toBeUndefined();
    await expect(access(final)).resolves.toBeUndefined();
  });
});
