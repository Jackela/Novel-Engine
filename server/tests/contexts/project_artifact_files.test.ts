import { mkdir, mkdtemp, readFile, rename, rm, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";

import { FilesystemProjectArtifactCleaner } from "../../src/contexts/studio/infrastructure/project_artifact_files.js";

const roots: string[] = [];

afterEach(async () => {
  await Promise.all(roots.splice(0).map((root) => rm(root, { recursive: true, force: true })));
});

async function temporaryRoot(prefix: string): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), prefix));
  roots.push(root);
  return root;
}

async function expectMissing(path: string): Promise<void> {
  await expect(readFile(path)).rejects.toMatchObject({ code: "ENOENT" });
}

describe("FilesystemProjectArtifactCleaner", () => {
  it("removes a real project export tree and leaves the exports root", async () => {
    const dataDirectory = await temporaryRoot("novel-engine-project-artifacts-");
    const exportsRoot = join(dataDirectory, "exports");
    const projectDirectory = join(exportsRoot, "project-1");
    await mkdir(join(projectDirectory, "nested"), { recursive: true });
    await writeFile(join(projectDirectory, "novel.md"), "# Novel\n");
    await writeFile(join(projectDirectory, "nested", "evidence"), "safe");

    await new FilesystemProjectArtifactCleaner(dataDirectory).removeProjectArtifacts("project-1");

    await expectMissing(join(projectDirectory, "novel.md"));
    await expect(mkdir(exportsRoot)).rejects.toMatchObject({ code: "EEXIST" });
  });

  it("succeeds repeatedly when the exports root or project leaf is missing", async () => {
    const dataDirectory = await temporaryRoot("novel-engine-project-artifacts-missing-");
    const cleaner = new FilesystemProjectArtifactCleaner(dataDirectory);
    await cleaner.removeProjectArtifacts("already-deleted");
    await mkdir(join(dataDirectory, "exports"));
    await cleaner.removeProjectArtifacts("already-deleted");
    await cleaner.removeProjectArtifacts("already-deleted");
  });

  it("unlinks a project-leaf symlink without touching its external target", async () => {
    const dataDirectory = await temporaryRoot("novel-engine-project-artifacts-link-");
    const outside = await temporaryRoot("novel-engine-project-artifacts-outside-");
    const exportsRoot = join(dataDirectory, "exports");
    const projectLink = join(exportsRoot, "project-link");
    const sentinel = join(outside, "sentinel.txt");
    await mkdir(exportsRoot);
    await writeFile(sentinel, "must survive");
    await symlink(outside, projectLink, "dir");

    await new FilesystemProjectArtifactCleaner(dataDirectory).removeProjectArtifacts(
      "project-link",
    );

    await expectMissing(projectLink);
    await expect(readFile(sentinel, "utf8")).resolves.toBe("must survive");
  });

  it("fails closed when the exports root itself is a symlink", async () => {
    const dataDirectory = await temporaryRoot("novel-engine-project-artifacts-root-link-");
    const outside = await temporaryRoot("novel-engine-project-artifacts-root-outside-");
    const sentinel = join(outside, "project-1", "sentinel.txt");
    await mkdir(join(outside, "project-1"));
    await writeFile(sentinel, "must survive");
    await symlink(outside, join(dataDirectory, "exports"), "dir");

    await expect(
      new FilesystemProjectArtifactCleaner(dataDirectory).removeProjectArtifacts("project-1"),
    ).rejects.toThrow("Exports root is not a real directory.");
    await expect(readFile(sentinel, "utf8")).resolves.toBe("must survive");
  });

  it("fails closed when the exports root is replaced after confinement", async () => {
    const dataDirectory = await temporaryRoot("novel-engine-project-artifacts-root-race-");
    const outside = await temporaryRoot("novel-engine-project-artifacts-race-outside-");
    const exportsRoot = join(dataDirectory, "exports");
    const movedExportsRoot = join(dataDirectory, "exports-validated");
    const originalArtifact = join(movedExportsRoot, "project-1", "novel.md");
    const externalSentinel = join(outside, "project-1", "sentinel.txt");
    await mkdir(join(exportsRoot, "project-1"), { recursive: true });
    await writeFile(join(exportsRoot, "project-1", "novel.md"), "# Novel\n");
    await mkdir(join(outside, "project-1"));
    await writeFile(externalSentinel, "must survive");
    const cleaner = new FilesystemProjectArtifactCleaner(dataDirectory, {
      beforeRemove: async () => {
        await rename(exportsRoot, movedExportsRoot);
        await symlink(outside, exportsRoot, "dir");
      },
    });

    await expect(cleaner.removeProjectArtifacts("project-1")).rejects.toThrow(
      "Exports root is not a real directory.",
    );
    await expect(readFile(externalSentinel, "utf8")).resolves.toBe("must survive");
    await expect(readFile(originalArtifact, "utf8")).resolves.toBe("# Novel\n");
  });

  it("fails closed when the project leaf is replaced after confinement", async () => {
    const dataDirectory = await temporaryRoot("novel-engine-project-artifacts-leaf-race-");
    const exportsRoot = join(dataDirectory, "exports");
    const projectDirectory = join(exportsRoot, "project-1");
    const validatedDirectory = join(exportsRoot, "project-1-validated");
    const originalArtifact = join(validatedDirectory, "novel.md");
    const replacementSentinel = join(projectDirectory, "replacement.txt");
    await mkdir(projectDirectory, { recursive: true });
    await writeFile(join(projectDirectory, "novel.md"), "# Novel\n");
    const cleaner = new FilesystemProjectArtifactCleaner(dataDirectory, {
      beforeRemove: async () => {
        await rename(projectDirectory, validatedDirectory);
        await mkdir(projectDirectory);
        await writeFile(replacementSentinel, "must survive");
      },
    });

    await expect(cleaner.removeProjectArtifacts("project-1")).rejects.toThrow(
      "Project export directory changed during artifact cleanup.",
    );
    await expect(readFile(replacementSentinel, "utf8")).resolves.toBe("must survive");
    await expect(readFile(originalArtifact, "utf8")).resolves.toBe("# Novel\n");
  });

  it.each(["", ".", "..", "../outside", "nested/project", "nested\\project", "bad\0id", "项目"])(
    "rejects unsafe project id %j without touching an external sentinel",
    async (projectId) => {
      const dataDirectory = await temporaryRoot("novel-engine-project-artifacts-id-");
      const sentinel = join(dataDirectory, "sentinel.txt");
      await writeFile(sentinel, "must survive");
      await expect(
        new FilesystemProjectArtifactCleaner(dataDirectory).removeProjectArtifacts(projectId),
      ).rejects.toThrow("Project id is invalid.");
      await expect(readFile(sentinel, "utf8")).resolves.toBe("must survive");
    },
  );

  it("propagates an injected failure without deleting the validated directory", async () => {
    const dataDirectory = await temporaryRoot("novel-engine-project-artifacts-failure-");
    const projectDirectory = join(dataDirectory, "exports", "project-1");
    const artifact = join(projectDirectory, "novel.md");
    await mkdir(projectDirectory, { recursive: true });
    await writeFile(artifact, "# Novel\n");
    const cleaner = new FilesystemProjectArtifactCleaner(dataDirectory, {
      beforeRemove: () => {
        throw new Error("simulated project artifact cleanup failure");
      },
    });

    await expect(cleaner.removeProjectArtifacts("project-1")).rejects.toThrow(
      "simulated project artifact cleanup failure",
    );
    await expect(readFile(artifact, "utf8")).resolves.toBe("# Novel\n");
  });
});
