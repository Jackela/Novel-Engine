import { createHash } from "node:crypto";
import {
  access,
  link,
  mkdir,
  readdir,
  readFile,
  rename,
  rm,
  symlink,
  unlink,
  writeFile,
} from "node:fs/promises";
import { join } from "node:path";

import { afterEach, describe, expect, it } from "vitest";
import { reconcileExportPublications } from "../../src/contexts/studio/infrastructure/export_publication_recovery.js";
import {
  addArtifact,
  cleanupRecoveryHarnesses,
  directEvidence,
  finalPath,
  openRecoveryHarness,
  preparePublication,
  projectDirectory,
} from "./export_publication_recovery_fixture.js";

afterEach(cleanupRecoveryHarnesses);

describe("export publication startup reconciliation", () => {
  it("removes proven uncommitted files plus deleted-project trees idempotently", async () => {
    const value = await openRecoveryHarness();
    await preparePublication(value, "uncommitted", Buffer.from("not committed"));
    const deleted = join(value.directory, "exports", "deleted-project");
    await mkdir(deleted, { recursive: true });
    await writeFile(join(deleted, "old.md"), "deleted project bytes");

    const report = await reconcileExportPublications(value.studio.db, value.directory);

    expect(report).toMatchObject({
      manifestsReconciled: 1,
      orphanFilesRemoved: 1,
      sidecarsRemoved: 2,
      deletedProjectDirectoriesRemoved: 1,
    });
    expect(await readdir(projectDirectory(value))).toEqual([]);
    await expect(access(deleted)).rejects.toThrow();
    expect(await reconcileExportPublications(value.studio.db, value.directory)).toEqual({
      manifestsReconciled: 0,
      committedArtifactsVerified: 0,
      finalsRestored: 0,
      orphanFilesRemoved: 0,
      sidecarsRemoved: 0,
      deletedProjectDirectoriesRemoved: 0,
    });
  });

  it.each([
    { kind: "final", name: "replacement.md", bytes: "replacement bytes" },
    { kind: "legacy temporary", name: ".legacy.publication.tmp", bytes: "temporary bytes" },
  ])("preserves an unproven $kind file independently", async ({ name, bytes }) => {
    const value = await openRecoveryHarness();
    const path = join(projectDirectory(value), name);
    await mkdir(projectDirectory(value), { recursive: true });
    await writeFile(path, bytes);

    await expect(reconcileExportPublications(value.studio.db, value.directory)).rejects.toThrow(
      /unproven export file/i,
    );
    await expect(readFile(path, "utf8")).resolves.toBe(bytes);
  });

  it("preserves a stage-only file without manifest or database proof", async () => {
    const value = await openRecoveryHarness();
    const staging = join(projectDirectory(value), ".staging");
    const stage = join(staging, "orphan.publication.stage");
    await mkdir(staging, { recursive: true });
    await writeFile(stage, "unproven stage bytes");

    await expect(reconcileExportPublications(value.studio.db, value.directory)).rejects.toThrow(
      /unproven export staging file/i,
    );
    await expect(readFile(stage, "utf8")).resolves.toBe("unproven stage bytes");
  });

  it("preserves an unbound legacy staging temporary", async () => {
    const value = await openRecoveryHarness();
    const staging = join(projectDirectory(value), ".staging");
    const temporary = join(staging, ".legacy.publication.tmp");
    await mkdir(staging, { recursive: true });
    await writeFile(temporary, "unproven staging temporary");

    await expect(reconcileExportPublications(value.studio.db, value.directory)).rejects.toThrow(
      /unproven export staging file/i,
    );
    await expect(readFile(temporary, "utf8")).resolves.toBe("unproven staging temporary");
  });

  it("preserves a manifest with no stage, final, or database commit marker", async () => {
    const value = await openRecoveryHarness();
    await preparePublication(
      value,
      "manifest-only",
      Buffer.from("manifest lost its byte evidence"),
      "markdown",
      false,
    );
    const staging = join(projectDirectory(value), ".staging");
    const names = await readdir(staging);
    const manifestName = names.find((name) => name.endsWith(".manifest.json"));
    const stageName = names.find((name) => name.endsWith(".stage"));
    if (manifestName === undefined || stageName === undefined) {
      throw new Error("Expected publication recovery sidecars.");
    }
    const manifest = join(staging, manifestName);
    await unlink(join(staging, stageName));
    await unlink(finalPath(value, "manifest-only"));

    await expect(reconcileExportPublications(value.studio.db, value.directory)).rejects.toThrow(
      /unproven export manifest/i,
    );
    await expect(readFile(manifest, "utf8")).resolves.toContain('"artifact_id":"manifest-only"');
  });

  it("removes a manifest temporary only when it is the parsed manifest hard-link", async () => {
    const value = await openRecoveryHarness();
    await preparePublication(
      value,
      "manifest-temp",
      Buffer.from("uncommitted with manifest temporary"),
    );
    const staging = join(projectDirectory(value), ".staging");
    const manifestName = (await readdir(staging)).find((name) => name.endsWith(".manifest.json"));
    if (manifestName === undefined) throw new Error("Expected a publication manifest.");
    const temporary = join(staging, `.${manifestName}.recovery.tmp`);
    await link(join(staging, manifestName), temporary);

    const report = await reconcileExportPublications(value.studio.db, value.directory);

    expect(report).toMatchObject({
      manifestsReconciled: 1,
      orphanFilesRemoved: 1,
      sidecarsRemoved: 3,
    });
    await expect(readdir(projectDirectory(value))).resolves.toEqual([]);
  });

  it("preserves an independent manifest temporary even for a committed artifact", async () => {
    const value = await openRecoveryHarness();
    const evidence = await preparePublication(
      value,
      "committed-temp",
      Buffer.from("committed artifact with unowned temporary"),
      "markdown",
      false,
    );
    addArtifact(value, "committed-temp", evidence);
    const staging = join(projectDirectory(value), ".staging");
    const manifestName = (await readdir(staging)).find((name) => name.endsWith(".manifest.json"));
    if (manifestName === undefined) throw new Error("Expected a publication manifest.");
    const manifest = join(staging, manifestName);
    const manifestBytes = await readFile(manifest);
    const temporary = join(staging, `.${manifestName}.recovery.tmp`);
    await writeFile(temporary, manifestBytes);
    await unlink(manifest);

    await expect(reconcileExportPublications(value.studio.db, value.directory)).rejects.toThrow(
      /unproven export staging file/i,
    );
    await expect(readFile(temporary)).resolves.toEqual(manifestBytes);
    await expect(readFile(finalPath(value, "committed-temp"))).resolves.toEqual(
      Buffer.from("committed artifact with unowned temporary"),
    );
  });

  it("keeps committed finals, clears sidecars, and verifies rows without manifests", async () => {
    const value = await openRecoveryHarness();
    const committed = await preparePublication(value, "committed", Buffer.from("committed bytes"));
    addArtifact(value, "committed", committed);
    const stableBytes = Buffer.from("stable without sidecars");
    await writeFile(finalPath(value, "stable"), stableBytes);
    addArtifact(value, "stable", directEvidence(value, "stable", stableBytes));

    const report = await reconcileExportPublications(value.studio.db, value.directory);

    expect(report).toMatchObject({
      manifestsReconciled: 1,
      committedArtifactsVerified: 2,
      finalsRestored: 0,
      sidecarsRemoved: 2,
    });
    expect((await readdir(projectDirectory(value))).sort()).toEqual(["committed.md", "stable.md"]);
  });

  it("restores a missing committed final from its verified stage hard-link", async () => {
    const value = await openRecoveryHarness();
    const bytes = Buffer.from("recoverable committed bytes");
    const evidence = await preparePublication(value, "recoverable", bytes);
    addArtifact(value, "recoverable", evidence);
    await unlink(finalPath(value, "recoverable"));

    const report = await reconcileExportPublications(value.studio.db, value.directory);

    expect(report.finalsRestored).toBe(1);
    expect(report.committedArtifactsVerified).toBe(1);
    expect(await readFile(finalPath(value, "recoverable"))).toEqual(bytes);
    expect(await readdir(projectDirectory(value))).toEqual(["recoverable.md"]);
  });

  it("fails closed when committed bytes are missing or disagree with their evidence", async () => {
    const missing = await openRecoveryHarness();
    const missingEvidence = await preparePublication(
      missing,
      "missing",
      Buffer.from("will disappear"),
    );
    addArtifact(missing, "missing", missingEvidence);
    await unlink(finalPath(missing, "missing"));
    await rm(join(projectDirectory(missing), ".staging"), { recursive: true });
    await expect(reconcileExportPublications(missing.studio.db, missing.directory)).rejects.toThrow(
      /missing/i,
    );

    const corrupt = await openRecoveryHarness();
    const corruptEvidence = await preparePublication(corrupt, "corrupt", Buffer.from("expected"));
    addArtifact(corrupt, "corrupt", corruptEvidence);
    await writeFile(finalPath(corrupt, "corrupt"), "replacement");
    await expect(reconcileExportPublications(corrupt.studio.db, corrupt.directory)).rejects.toThrow(
      /evidence|match/i,
    );
    expect(await readdir(join(projectDirectory(corrupt), ".staging"))).toHaveLength(2);
  });

  it("rejects malformed, symlinked, and path-escaping recovery evidence", async () => {
    const value = await openRecoveryHarness();
    const staging = join(projectDirectory(value), ".staging");
    await mkdir(staging, { recursive: true });
    await writeFile(join(staging, "bad.manifest.json"), "{");
    await expect(reconcileExportPublications(value.studio.db, value.directory)).rejects.toThrow();
    await rm(staging, { recursive: true });

    const outside = join(value.directory, "outside.md");
    await writeFile(outside, "outside stays");
    await symlink(outside, finalPath(value, "linked"));
    await expect(reconcileExportPublications(value.studio.db, value.directory)).rejects.toThrow(
      /unsafe/i,
    );
    await unlink(finalPath(value, "linked"));

    await mkdir(staging, { recursive: true });
    const bytes = Buffer.from("escape attempt");
    await writeFile(join(staging, "escape.pub.stage"), bytes);
    await writeFile(
      join(staging, "escape.pub.manifest.json"),
      JSON.stringify({
        version: 1,
        publication_id: "pub",
        artifact_id: "escape",
        project_id: value.projectId,
        format: "markdown",
        relative_path: "../../outside.md",
        stage_file: "escape.pub.stage",
        size_bytes: bytes.length,
        checksum_sha256: createHash("sha256").update(bytes).digest("hex"),
      }),
    );
    await expect(reconcileExportPublications(value.studio.db, value.directory)).rejects.toThrow();
    await expect(readFile(outside, "utf8")).resolves.toBe("outside stays");
  });

  it("preserves an ambiguous rollback quarantine and fails closed", async () => {
    const value = await openRecoveryHarness();
    const quarantine = join(projectDirectory(value), "replaced.md.rollback-recovery");
    await mkdir(projectDirectory(value), { recursive: true });
    await writeFile(quarantine, "possibly replacement bytes");

    await expect(reconcileExportPublications(value.studio.db, value.directory)).rejects.toThrow(
      /rollback quarantine/i,
    );
    await expect(readFile(quarantine, "utf8")).resolves.toBe("possibly replacement bytes");
  });

  it("removes a rollback quarantine only when the durable stage proves ownership", async () => {
    const value = await openRecoveryHarness();
    const evidence = await preparePublication(
      value,
      "owned",
      Buffer.from("owned publication bytes"),
    );
    const target = finalPath(value, "owned");
    const quarantine = `${target}.rollback-recovery`;
    await rename(target, quarantine);

    const report = await reconcileExportPublications(value.studio.db, value.directory);

    expect(report).toMatchObject({
      manifestsReconciled: 1,
      orphanFilesRemoved: 1,
      sidecarsRemoved: 2,
    });
    await expect(access(quarantine)).rejects.toThrow();
    await expect(access(join(value.directory, evidence.relativePath))).rejects.toThrow();
    await expect(readdir(projectDirectory(value))).resolves.toEqual([]);
  });

  it("preserves an identical replacement when its durable stage proof is missing", async () => {
    const value = await openRecoveryHarness();
    const bytes = Buffer.from("byte-identical replacement");
    await preparePublication(value, "identical", bytes);
    const target = finalPath(value, "identical");
    await unlink(target);
    await writeFile(target, bytes);
    const staging = join(projectDirectory(value), ".staging");
    for (const name of await readdir(staging)) {
      if (name.endsWith(".stage")) await unlink(join(staging, name));
    }

    await expect(reconcileExportPublications(value.studio.db, value.directory)).rejects.toThrow(
      /replaced/i,
    );
    await expect(readFile(target)).resolves.toEqual(bytes);
    expect((await readdir(staging)).some((name) => name.endsWith(".manifest.json"))).toBe(true);
  });
});
