import { existsSync } from "node:fs";
import {
  access,
  mkdir,
  mkdtemp,
  readdir,
  readFile,
  rename,
  rm,
  stat,
  writeFile,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";

import { describe, expect, it } from "vitest";
import {
  cleanupOwnedFile,
  quarantineOwnedFile,
} from "../../src/contexts/studio/infrastructure/export_artifact_fs_support.js";
import { publishArtifact } from "../../src/contexts/studio/infrastructure/export_artifact_publication.js";

async function publicationHarness(prefix: string) {
  const directory = await mkdtemp(join(tmpdir(), prefix));
  const projectDirectory = join(directory, "exports", "project-1");
  const staging = join(projectDirectory, ".staging");
  await mkdir(staging, { recursive: true });
  return { directory, projectDirectory, staging };
}

function publish(projectDirectory: string, artifactId: string, newId: () => string) {
  return publishArtifact({
    projectDirectory,
    target: join(projectDirectory, `${artifactId}.md`),
    relativePath: `exports/project-1/${artifactId}.md`,
    projectId: "project-1",
    artifactId,
    format: "markdown",
    contents: Buffer.from("# Owned publication\n"),
    newId,
  });
}

describe("export publication sidecar ownership", () => {
  it("records cleanup authority before the final path can become visible", async () => {
    const value = await publicationHarness("novel-engine-artifact-write-ahead-");
    const target = join(value.projectDirectory, "write-ahead.md");
    let finalWasVisibleAtBegin = false;
    let beginCalls = 0;
    try {
      await expect(
        publishArtifact({
          projectDirectory: value.projectDirectory,
          target,
          relativePath: "exports/project-1/write-ahead.md",
          projectId: "project-1",
          artifactId: "write-ahead",
          format: "markdown",
          contents: Buffer.from("# Write ahead\n"),
          newId: () => "publication-id",
          cleanupJournal: {
            async begin() {
              beginCalls += 1;
              finalWasVisibleAtBegin ||= existsSync(target);
              throw new Error("simulated cleanup-intent write failure");
            },
            async complete() {
              throw new Error("Unexpected cleanup-intent completion.");
            },
          },
        }),
      ).rejects.toThrow("simulated cleanup-intent write failure");

      expect(beginCalls).toBeGreaterThan(0);
      expect(finalWasVisibleAtBegin).toBe(false);
      await expect(access(target)).rejects.toMatchObject({ code: "ENOENT" });
    } finally {
      await rm(value.directory, { recursive: true });
    }
  });

  it.each(["stage", "manifest", "temporary"] as const)(
    "preserves a pre-existing %s path when publication identity collides",
    async (collision) => {
      const value = await publicationHarness("novel-engine-artifact-collision-");
      try {
        const artifactId = `collision-${collision}`;
        const publicationId = "publication-id";
        const temporaryId = "temporary-id";
        const stage = join(value.staging, `${artifactId}.${publicationId}.stage`);
        const manifest = join(value.staging, `${artifactId}.${publicationId}.manifest.json`);
        const temporary = join(value.staging, `.${basename(manifest)}.${temporaryId}.tmp`);
        const target =
          collision === "stage" ? stage : collision === "manifest" ? manifest : temporary;
        const replacement = `pre-existing ${collision} bytes`;
        await writeFile(target, replacement);
        const ids = [publicationId, temporaryId];

        await expect(
          publish(value.projectDirectory, artifactId, () => ids.shift() ?? "unexpected-id"),
        ).rejects.toMatchObject({ code: "EEXIST" });

        await expect(readFile(target, "utf8")).resolves.toBe(replacement);
        await expect(readdir(value.staging)).resolves.toEqual([basename(target)]);
      } finally {
        await rm(value.directory, { recursive: true });
      }
    },
  );

  it.each(["stage", "manifest"] as const)(
    "preserves a replaced %s sidecar during acknowledgement",
    async (sidecar) => {
      const value = await publicationHarness("novel-engine-artifact-sidecar-");
      try {
        const ids = ["publication-id", "temporary-id"];
        const evidence = await publish(
          value.projectDirectory,
          `replaced-${sidecar}`,
          () => ids.shift() ?? "unexpected-id",
        );
        const suffix = sidecar === "stage" ? ".stage" : ".manifest.json";
        const name = (await readdir(value.staging)).find((entry) => entry.endsWith(suffix));
        if (name === undefined) throw new Error(`Expected a ${sidecar} sidecar.`);
        const path = join(value.staging, name);
        const replacement = join(value.directory, "replacement");
        await writeFile(replacement, `replacement ${sidecar} bytes`, { flag: "wx" });
        const originalIdentity = await stat(path, { bigint: true });
        const replacementIdentity = await stat(replacement, { bigint: true });
        expect(replacementIdentity.dev).toBe(originalIdentity.dev);
        expect(replacementIdentity.ino).not.toBe(originalIdentity.ino);
        await rename(replacement, path);

        await expect(evidence.acknowledge()).rejects.toThrow(/preserved a replacement/i);
        await expect(readFile(path, "utf8")).resolves.toBe(`replacement ${sidecar} bytes`);
      } finally {
        await rm(value.directory, { recursive: true });
      }
    },
  );

  it("keeps repeated cleanup quarantine names bounded across replayed crashes", async () => {
    const value = await publicationHarness("novel-engine-artifact-cleanup-replay-");
    try {
      const original = join(value.staging, "bounded.publication.stage");
      await writeFile(original, "bounded cleanup bytes", { flag: "wx" });
      const details = await stat(original, { bigint: true });
      const identity = { dev: details.dev, ino: details.ino };
      let current = original;

      for (let attempt = 0; attempt < 12; attempt += 1) {
        const quarantined = await quarantineOwnedFile(current, identity);
        if (quarantined === undefined) throw new Error("Expected a cleanup quarantine.");
        current = quarantined.path;
        expect(basename(current).length).toBeLessThan(100);
        expect(basename(current).match(/\.cleanup-/g) ?? []).toHaveLength(1);
      }

      await cleanupOwnedFile(current, identity);
      await expect(access(current)).rejects.toThrow();
      await expect(readdir(value.staging)).resolves.toEqual([]);
    } finally {
      await rm(value.directory, { recursive: true });
    }
  });
});
