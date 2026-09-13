import { access, link, readdir, readFile, rename, stat, unlink, writeFile } from "node:fs/promises";
import { basename, join } from "node:path";

import { afterEach, describe, expect, it } from "vitest";
import { exportPublicationCleanupIntents } from "../../src/contexts/studio/infrastructure/db/schema.js";
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

describe("export publication cleanup journal recovery", () => {
  it("cleans a write-ahead stage and manifest when final publication never became visible", async () => {
    const value = await openRecoveryHarness();
    await preparePublication(value, "before-final", Buffer.from("write ahead cleanup"));
    await unlink(finalPath(value, "before-final"));

    const report = await reconcileExportPublications(value.studio.db, value.directory);

    expect(report).toMatchObject({ manifestsReconciled: 1, sidecarsRemoved: 2 });
    await expect(readdir(projectDirectory(value))).resolves.toEqual([]);
    expect(value.studio.db.select().from(exportPublicationCleanupIntents).all()).toEqual([]);
  });

  it("replays a matching manifest-only cleanup intent and clears its authority", async () => {
    const value = await openRecoveryHarness();
    await preparePublication(value, "manifest-intent", Buffer.from("owned cleanup bytes"));
    const staging = join(projectDirectory(value), ".staging");
    const manifest = await stagingFile(staging, ".manifest.json");
    await unlink(await stagingFile(staging, ".stage"));
    await unlink(finalPath(value, "manifest-intent"));

    const report = await reconcileExportPublications(value.studio.db, value.directory);

    expect(report).toMatchObject({ manifestsReconciled: 1, sidecarsRemoved: 1 });
    await expect(access(manifest)).rejects.toThrow();
    expect(value.studio.db.select().from(exportPublicationCleanupIntents).all()).toEqual([]);
    expect(await reconcileExportPublications(value.studio.db, value.directory)).toEqual(
      emptyReport(),
    );
  });

  it("preserves a cleanup-suffixed manifest without database authority", async () => {
    const value = await openRecoveryHarness();
    await preparePublication(
      value,
      "unowned-manifest",
      Buffer.from("unowned manifest bytes"),
      "markdown",
      false,
    );
    const staging = join(projectDirectory(value), ".staging");
    const manifest = await stagingFile(staging, ".manifest.json");
    const quarantine = `${manifest}.cleanup-restart`;
    await rename(manifest, quarantine);
    await unlink(await stagingFile(staging, ".stage"));
    await unlink(finalPath(value, "unowned-manifest"));

    await expect(reconcileExportPublications(value.studio.db, value.directory)).rejects.toThrow(
      /unproven export manifest/i,
    );
    await expect(readFile(quarantine, "utf8")).resolves.toContain(
      '"artifact_id":"unowned-manifest"',
    );
    expect(value.studio.db.select().from(exportPublicationCleanupIntents).all()).toEqual([]);
  });

  it("preserves a cleanup-suffixed manifest temporary without authority", async () => {
    const value = await openRecoveryHarness();
    await preparePublication(
      value,
      "unowned-temp",
      Buffer.from("unowned temporary bytes"),
      "markdown",
      false,
    );
    const staging = join(projectDirectory(value), ".staging");
    const manifest = await stagingFile(staging, ".manifest.json");
    const temporary = join(staging, `.${basename(manifest)}.recovery.tmp`);
    await link(manifest, temporary);
    const quarantine = `${temporary}.cleanup-restart`;
    await rename(temporary, quarantine);
    await unlink(manifest);
    await unlink(await stagingFile(staging, ".stage"));
    await unlink(finalPath(value, "unowned-temp"));

    await expect(reconcileExportPublications(value.studio.db, value.directory)).rejects.toThrow(
      /unproven export staging file/i,
    );
    await expect(readFile(quarantine, "utf8")).resolves.toContain('"artifact_id":"unowned-temp"');
  });

  it("preserves a byte-identical manifest replacement that disagrees with the journal inode", async () => {
    const value = await openRecoveryHarness();
    await preparePublication(value, "manifest-replaced", Buffer.from("stable publication"));
    const staging = join(projectDirectory(value), ".staging");
    const manifest = await stagingFile(staging, ".manifest.json");
    const bytes = await readFile(manifest);
    const replacement = join(value.directory, "replacement-manifest");
    await writeFile(replacement, bytes, { flag: "wx" });
    const originalIdentity = await stat(manifest, { bigint: true });
    const replacementIdentity = await stat(replacement, { bigint: true });
    expect(replacementIdentity.dev).toBe(originalIdentity.dev);
    expect(replacementIdentity.ino).not.toBe(originalIdentity.ino);
    await rename(replacement, manifest);
    await unlink(await stagingFile(staging, ".stage"));
    await unlink(finalPath(value, "manifest-replaced"));

    await expect(reconcileExportPublications(value.studio.db, value.directory)).rejects.toThrow(
      /manifest identity was replaced/i,
    );
    await expect(readFile(manifest)).resolves.toEqual(bytes);
    expect(value.studio.db.select().from(exportPublicationCleanupIntents).all()).toHaveLength(1);
  });

  it("preserves a byte-identical stage replacement that disagrees with the journal inode", async () => {
    const value = await openRecoveryHarness();
    const bytes = Buffer.from("stable staged publication");
    await preparePublication(value, "stage-replaced", bytes);
    const staging = join(projectDirectory(value), ".staging");
    const stage = await stagingFile(staging, ".stage");
    await unlink(stage);
    await writeFile(stage, bytes);

    await expect(reconcileExportPublications(value.studio.db, value.directory)).rejects.toThrow(
      /stage identity was replaced/i,
    );
    await expect(readFile(stage)).resolves.toEqual(bytes);
    expect(value.studio.db.select().from(exportPublicationCleanupIntents).all()).toHaveLength(1);
  });

  it.each(["stage", "manifest"] as const)(
    "replays a committed partial acknowledgement with only the %s sidecar",
    async (remaining) => {
      const value = await openRecoveryHarness();
      const evidence = await preparePublication(
        value,
        `committed-${remaining}`,
        Buffer.from(`committed ${remaining} bytes`),
      );
      addArtifact(value, `committed-${remaining}`, evidence);
      const staging = join(projectDirectory(value), ".staging");
      const removeSuffix = remaining === "stage" ? ".manifest.json" : ".stage";
      await unlink(await stagingFile(staging, removeSuffix));

      const report = await reconcileExportPublications(value.studio.db, value.directory);

      expect(report).toMatchObject({ manifestsReconciled: 1, sidecarsRemoved: 1 });
      expect(await readdir(projectDirectory(value))).toEqual([`committed-${remaining}.md`]);
      expect(value.studio.db.select().from(exportPublicationCleanupIntents).all()).toEqual([]);
    },
  );

  it("replays a nested top-level final cleanup quarantine with matching authority", async () => {
    const value = await openRecoveryHarness();
    await preparePublication(value, "nested-final", Buffer.from("nested cleanup bytes"));
    const quarantine = `${finalPath(value, "nested-final")}.cleanup-first.cleanup-second`;
    await rename(finalPath(value, "nested-final"), quarantine);

    const report = await reconcileExportPublications(value.studio.db, value.directory);

    expect(report).toMatchObject({ orphanFilesRemoved: 1, manifestsReconciled: 1 });
    await expect(access(quarantine)).rejects.toThrow();
    expect(value.studio.db.select().from(exportPublicationCleanupIntents).all()).toEqual([]);
    expect(await reconcileExportPublications(value.studio.db, value.directory)).toEqual(
      emptyReport(),
    );
  });

  it("preserves an unowned final cleanup quarantine and a later canonical replacement", async () => {
    const value = await openRecoveryHarness();
    await preparePublication(
      value,
      "unowned-final",
      Buffer.from("possibly owned bytes"),
      "markdown",
      false,
    );
    const target = finalPath(value, "unowned-final");
    const quarantine = `${target}.cleanup-restart`;
    await rename(target, quarantine);
    await writeFile(target, "later replacement");

    await expect(reconcileExportPublications(value.studio.db, value.directory)).rejects.toThrow(
      /ambiguous export cleanup quarantine/i,
    );
    await expect(readFile(quarantine, "utf8")).resolves.toBe("possibly owned bytes");
    await expect(readFile(target, "utf8")).resolves.toBe("later replacement");
  });
});

async function stagingFile(staging: string, suffix: string): Promise<string> {
  const name = (await readdir(staging)).find((entry) => entry.endsWith(suffix));
  if (name === undefined) throw new Error(`Expected staging file ending in ${suffix}.`);
  return join(staging, name);
}

function emptyReport() {
  return {
    manifestsReconciled: 0,
    committedArtifactsVerified: 0,
    finalsRestored: 0,
    orphanFilesRemoved: 0,
    sidecarsRemoved: 0,
    deletedProjectDirectoriesRemoved: 0,
  };
}
