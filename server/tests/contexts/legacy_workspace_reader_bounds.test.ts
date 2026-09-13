import { mkdirSync, unlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";
import { describe, expect, it } from "vitest";
import { LEGACY_IMPORT_LIMITS } from "../../src/contexts/studio/application/ports/legacy_workspace_reader.js";
import type { ImportCapacityExceededError } from "../../src/contexts/studio/domain/exceptions.js";
import { FsLegacyWorkspaceReader } from "../../src/contexts/studio/infrastructure/fs_legacy_workspace_reader.js";
import { makeLegacyWorkspace } from "../legacy_workspace_fixtures.js";

const reader = new FsLegacyWorkspaceReader();

function workspacePath(label: string): string {
  return join(tmpdir(), `novel-engine-legacy-bounds-${label}-${Date.now()}-${Math.random()}`);
}

function expectCapacity(
  operation: Promise<unknown>,
  resource: ImportCapacityExceededError["resource"],
  limit: number,
  observed: number,
) {
  return expect(operation).rejects.toMatchObject({ resource, limit, observed });
}

describe("legacy workspace reader budgets", () => {
  it("accepts the exact multi-byte story limit and rejects the next byte", async () => {
    const source = makeLegacyWorkspace(workspacePath("story"), { chapters: [] });
    const story = join(source, "story.yaml");
    const exactBytes = `${"星".repeat(87_381)}a`;
    writeFileSync(story, exactBytes);
    expect(Buffer.byteLength(exactBytes)).toBe(LEGACY_IMPORT_LIMITS.storyBytes);

    await expect(reader.read(source)).resolves.toMatchObject({ chapters: [] });
    writeFileSync(story, Buffer.alloc(LEGACY_IMPORT_LIMITS.storyBytes + 1));
    await expectCapacity(
      reader.read(source),
      "story_bytes",
      LEGACY_IMPORT_LIMITS.storyBytes,
      LEGACY_IMPORT_LIMITS.storyBytes + 1,
    );
  });

  it("accepts the exact chapter limit and rejects the next byte", async () => {
    const source = makeLegacyWorkspace(workspacePath("chapter"), {
      chapters: [{ filename: "chapter-001.md", content: "" }],
    });
    const chapter = join(source, "manuscript", "chapters", "chapter-001.md");
    writeFileSync(chapter, Buffer.alloc(LEGACY_IMPORT_LIMITS.chapterBytes));
    await expect(reader.read(source)).resolves.toMatchObject({
      chapters: [{ bytes: LEGACY_IMPORT_LIMITS.chapterBytes }],
    });

    writeFileSync(chapter, Buffer.alloc(LEGACY_IMPORT_LIMITS.chapterBytes + 1));
    await expectCapacity(
      reader.read(source),
      "chapter_bytes",
      LEGACY_IMPORT_LIMITS.chapterBytes,
      LEGACY_IMPORT_LIMITS.chapterBytes + 1,
    );
  });

  it("accepts the exact workspace byte limit and rejects the next byte", async () => {
    const source = makeLegacyWorkspace(workspacePath("total"), { chapters: [] });
    writeFileSync(join(source, "story.yaml"), "");
    const chapters = join(source, "manuscript", "chapters");
    for (let index = 0; index < 16; index += 1) {
      writeFileSync(
        join(chapters, `chapter-${String(index).padStart(3, "0")}.md`),
        Buffer.alloc(LEGACY_IMPORT_LIMITS.chapterBytes),
      );
    }
    await expect(reader.read(source)).resolves.toMatchObject({ chapters: expect.any(Array) });

    writeFileSync(join(source, "story.yaml"), "x");
    await expectCapacity(
      reader.read(source),
      "workspace_bytes",
      LEGACY_IMPORT_LIMITS.workspaceBytes,
      LEGACY_IMPORT_LIMITS.workspaceBytes + 1,
    );
  }, 60_000);

  it("bounds matching chapters and every observed directory entry", async () => {
    const source = makeLegacyWorkspace(workspacePath("counts"), { chapters: [] });
    const chapters = join(source, "manuscript", "chapters");
    for (let index = 0; index < LEGACY_IMPORT_LIMITS.chapterCount; index += 1) {
      writeFileSync(join(chapters, `chapter-${String(index).padStart(4, "0")}.md`), "");
    }
    for (let index = 0; index < 2_096; index += 1) {
      writeFileSync(join(chapters, `ignored-${String(index).padStart(4, "0")}.txt`), "");
    }
    await expect(reader.read(source)).resolves.toMatchObject({
      chapters: { length: LEGACY_IMPORT_LIMITS.chapterCount },
    });

    writeFileSync(join(chapters, "ignored-over-limit.txt"), "");
    await expectCapacity(
      reader.read(source),
      "directory_entries",
      LEGACY_IMPORT_LIMITS.directoryEntries,
      LEGACY_IMPORT_LIMITS.directoryEntries + 1,
    );
    unlinkSync(join(chapters, "ignored-over-limit.txt"));
    unlinkSync(join(chapters, "ignored-0000.txt"));
    writeFileSync(join(chapters, "chapter-over-limit.md"), "");
    await expectCapacity(
      reader.read(source),
      "chapter_count",
      LEGACY_IMPORT_LIMITS.chapterCount,
      LEGACY_IMPORT_LIMITS.chapterCount + 1,
    );
  }, 60_000);

  it("counts non-matching entries without reading them", async () => {
    const source = makeLegacyWorkspace(workspacePath("nonmatching"), { chapters: [] });
    const chapters = join(source, "manuscript", "chapters");
    for (let index = 0; index <= LEGACY_IMPORT_LIMITS.directoryEntries; index += 1) {
      mkdirSync(join(chapters, `ignored-${String(index).padStart(4, "0")}`));
    }
    await expectCapacity(
      reader.read(source),
      "directory_entries",
      LEGACY_IMPORT_LIMITS.directoryEntries,
      LEGACY_IMPORT_LIMITS.directoryEntries + 1,
    );
  }, 60_000);

  it("yields to the event loop while reading a large accepted workspace", async () => {
    const source = makeLegacyWorkspace(workspacePath("responsive"), {
      chapters: [{ filename: "chapter-001.md", content: "" }],
    });
    const chapter = join(source, "manuscript", "chapters", "chapter-001.md");
    writeFileSync(chapter, Buffer.alloc(LEGACY_IMPORT_LIMITS.chapterBytes));
    let chapterOpened = false;
    let scheduledImmediateRan = false;
    let readingSettled = false;
    let resolveImmediate: (() => void) | undefined;
    const immediateRan = new Promise<void>((resolve) => {
      resolveImmediate = resolve;
    });
    const responsiveReader = new FsLegacyWorkspaceReader({
      afterFileOpen(path) {
        if (basename(path) !== "chapter-001.md") return;
        chapterOpened = true;
        setImmediate(() => {
          scheduledImmediateRan = true;
          resolveImmediate?.();
        });
      },
    });

    const reading = responsiveReader.read(source).finally(() => {
      readingSettled = true;
    });
    await immediateRan;

    expect(chapterOpened).toBe(true);
    expect(scheduledImmediateRan).toBe(true);
    expect(readingSettled).toBe(false);
    await expect(reading).resolves.toMatchObject({
      chapters: [{ bytes: LEGACY_IMPORT_LIMITS.chapterBytes }],
    });
  }, 60_000);
});
