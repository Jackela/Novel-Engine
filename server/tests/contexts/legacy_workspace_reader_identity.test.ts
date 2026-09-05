import {
  appendFileSync,
  mkdirSync,
  renameSync,
  symlinkSync,
  truncateSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";
import { describe, expect, it } from "vitest";
import { FsLegacyWorkspaceReader } from "../../src/contexts/studio/infrastructure/fs_legacy_workspace_reader.js";
import { InvalidOperationError } from "../../src/shared/domain/exceptions.js";
import { makeLegacyWorkspace } from "../legacy_workspace_fixtures.js";

function workspacePath(label: string): string {
  return join(tmpdir(), `novel-engine-legacy-identity-${label}-${Date.now()}-${Math.random()}`);
}

function workspace(label: string): string {
  return makeLegacyWorkspace(workspacePath(label), {
    title: "Pinned",
    chapters: [{ filename: "chapter-001.md", content: "# Inside\n" }],
  });
}

describe("legacy workspace reader identity", () => {
  it.each([
    ["story.yaml", "story"],
    ["chapter-001.md", "chapter"],
  ])("rejects a %s path replaced after its descriptor opens", async (filename, label) => {
    const source = workspace(label);
    const outside = join(workspacePath(`${label}-outside`), "outside.md");
    mkdirSync(join(outside, ".."), { recursive: true });
    writeFileSync(outside, "# Outside bytes\n");
    let replaced = false;
    const reader = new FsLegacyWorkspaceReader({
      afterFileOpen(path) {
        if (replaced || basename(path) !== filename) return;
        replaced = true;
        renameSync(path, `${path}.original`);
        symlinkSync(outside, path);
      },
    });

    await expect(reader.read(source)).rejects.toBeInstanceOf(InvalidOperationError);
  });

  it("normalizes an ancestor replaced by a regular file after opening", async () => {
    const source = workspace("ancestor-file");
    let replaced = false;
    const reader = new FsLegacyWorkspaceReader({
      afterFileOpen(path) {
        if (replaced || basename(path) !== "story.yaml") return;
        replaced = true;
        renameSync(source, `${source}.original`);
        writeFileSync(source, "not a directory");
      },
    });

    await expect(reader.read(source)).rejects.toEqual(
      new InvalidOperationError("Legacy workspace changed during inspection."),
    );
  });

  it.each(["grow", "truncate"])(
    "rejects a file that changes size after fstat: %s",
    async (mode) => {
      const source = workspace(mode);
      let changed = false;
      const reader = new FsLegacyWorkspaceReader({
        afterFileOpen(path) {
          if (changed || basename(path) !== "chapter-001.md") return;
          changed = true;
          if (mode === "grow") appendFileSync(path, "more");
          else truncateSync(path, 1);
        },
      });

      await expect(reader.read(source)).rejects.toBeInstanceOf(InvalidOperationError);
    },
  );

  it.each([
    ["source", (source: string) => source],
    ["manuscript", (source: string) => join(source, "manuscript")],
    ["chapters", (source: string) => join(source, "manuscript", "chapters")],
  ])("rejects final %s directory identity replacement", async (_label, selectPath) => {
    const source = workspace(`directory-${_label}`);
    const reader = new FsLegacyWorkspaceReader({
      beforeFinalDirectoryValidation() {
        const target = selectPath(source);
        renameSync(target, `${target}.original`);
        mkdirSync(target);
      },
    });

    await expect(reader.read(source)).rejects.toBeInstanceOf(InvalidOperationError);
  });
});
