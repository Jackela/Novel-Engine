import { mkdirSync, realpathSync, symlinkSync, unlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";
import { describe, expect, it } from "vitest";
import { NotFoundError } from "../../src/contexts/studio/domain/exceptions.js";
import { FsLegacyWorkspaceReader } from "../../src/contexts/studio/infrastructure/fs_legacy_workspace_reader.js";
import { InvalidOperationError } from "../../src/shared/domain/exceptions.js";
import {
  directoryFingerprint,
  type LegacyWorkspaceInput,
  makeLegacyWorkspace,
} from "../legacy_workspace_fixtures.js";

const reader = new FsLegacyWorkspaceReader();
const WEB_SOURCE_ERROR = "Web imports must name a workspace directory under data/imports.";
const IMPORT_NOT_FOUND_ERROR = "Import workspace not found under data/imports.";

function workspacePath(label: string): string {
  return join(tmpdir(), `novel-engine-legacy-reader-${label}-${Date.now()}-${Math.random()}`);
}

function makeWorkspace(label: string, input: LegacyWorkspaceInput): string {
  return makeLegacyWorkspace(workspacePath(label), input);
}

describe("legacy workspace reader", () => {
  it("reads canonical metadata and raw chapters in lexical filename order without mutation", () => {
    const first = "# Second\r\n\r\nA lantern stayed lit.\r\n";
    const second = "# Tenth\n\n星光 remained.\n";
    const source = makeWorkspace("ordered", {
      title: "Legacy Stars",
      premise: "A read-only recovery.",
      chapters: [
        { filename: "chapter-010.md", content: second },
        { filename: "chapter-002.md", content: first },
      ],
    });
    const before = directoryFingerprint(source);

    const workspace = reader.read(source);

    expect(workspace.source).toBe(realpathSync(source));
    expect(workspace.title).toBe("Legacy Stars");
    expect(workspace.description).toBe("A read-only recovery.");
    expect(workspace.chapters).toEqual([
      {
        filename: "chapter-002.md",
        contentMarkdown: first,
        bytes: Buffer.byteLength(first, "utf8"),
      },
      {
        filename: "chapter-010.md",
        contentMarkdown: second,
        bytes: Buffer.byteLength(second, "utf8"),
      },
    ]);
    expect(workspace.sourceHash).toMatch(/^[0-9a-f]{64}$/);
    expect(reader.read(source).sourceHash).toBe(workspace.sourceHash);
    expect(directoryFingerprint(source)).toBe(before);
  });

  it("binds the hash to the canonical source and eligible raw bytes", () => {
    const input: LegacyWorkspaceInput = {
      title: "Shared Story",
      chapters: [{ filename: "chapter-001.md", content: "# Before\n" }],
    };
    const first = makeWorkspace("first", input);
    const second = makeWorkspace("second", input);
    const firstHash = reader.read(first).sourceHash;

    expect(reader.read(second).sourceHash).not.toBe(firstHash);

    writeFileSync(join(first, "manuscript", "chapters", "chapter-001.md"), "# After\n", "utf8");
    expect(reader.read(first).sourceHash).not.toBe(firstHash);

    const fallback = makeWorkspace("fallback", { chapters: [] });
    const fallbackWorkspace = reader.read(fallback);
    expect(fallbackWorkspace.title).toBe(basename(realpathSync(fallback)));
    expect(fallbackWorkspace.description).toBe("");
  });

  it("uses the legacy structure error when story.yaml is absent", () => {
    const source = makeWorkspace("missing-story", {
      chapters: [{ filename: "chapter-001.md", content: "# One\n" }],
    });
    unlinkSync(join(source, "story.yaml"));

    expect(() => reader.read(source)).toThrowError(
      new InvalidOperationError("Legacy workspace must contain story.yaml."),
    );
  });

  it("rejects a symbolic-link source root before it resolves the target", () => {
    const target = makeWorkspace("root-target", {
      chapters: [{ filename: "chapter-001.md", content: "# One\n" }],
    });
    const source = workspacePath("root-link");
    symlinkSync(target, source, "dir");

    expect(() => reader.read(source)).toThrowError(InvalidOperationError);
  });

  it("rejects symbolic-link chapters instead of following them", () => {
    const source = makeWorkspace("chapter-link", {
      chapters: [{ filename: "chapter-001.md", content: "# One\n" }],
    });
    const target = makeWorkspace("chapter-target", {
      chapters: [{ filename: "chapter-001.md", content: "# Outside\n" }],
    });
    symlinkSync(
      join(target, "manuscript", "chapters", "chapter-001.md"),
      join(source, "manuscript", "chapters", "chapter-002.md"),
    );

    expect(() => reader.read(source)).toThrowError(InvalidOperationError);
  });

  it("reads a direct data/imports child for the web preview without mutation", () => {
    const dataDirectory = workspacePath("web-data");
    const source = makeLegacyWorkspace(join(dataDirectory, "imports", "safe-workspace"), {
      title: "Confined Story",
      chapters: [
        { filename: "chapter-010.md", content: "# Ten\n" },
        { filename: "chapter-002.md", content: "# Two\r\n" },
      ],
    });
    const before = directoryFingerprint(source);

    const workspace = reader.readConfinedLegacyWorkspace(dataDirectory, "safe-workspace");

    expect(workspace.source).toBe(realpathSync(source));
    expect(workspace.title).toBe("Confined Story");
    expect(workspace.chapters.map((chapter) => chapter.filename)).toEqual([
      "chapter-002.md",
      "chapter-010.md",
    ]);
    expect(workspace.chapters[0]?.contentMarkdown).toBe("# Two\r\n");
    expect(directoryFingerprint(source)).toBe(before);
  });

  it("rejects unsafe web source names before looking below data/imports", () => {
    const dataDirectory = workspacePath("unsafe-web-source");

    const unsafeSources = ["", "   ", ".", "..", "a/b", "a\\b", "../safe", "/tmp/safe", "C:\\safe"];
    for (const source of unsafeSources) {
      expect(() => reader.readConfinedLegacyWorkspace(dataDirectory, source)).toThrowError(
        new InvalidOperationError(WEB_SOURCE_ERROR),
      );
    }
  });

  it("rejects missing, non-directory, and symbolic-link web roots or sources", () => {
    const missingRoot = workspacePath("missing-web-root");
    expect(() => reader.readConfinedLegacyWorkspace(missingRoot, "safe")).toThrowError(
      new NotFoundError(IMPORT_NOT_FOUND_ERROR),
    );

    const dataDirectory = workspacePath("web-source-shapes");
    const importsRoot = join(dataDirectory, "imports");
    mkdirSync(importsRoot, { recursive: true });
    writeFileSync(join(importsRoot, "not-a-directory"), "plain file", "utf8");
    const outside = makeWorkspace("outside-web-source", {
      chapters: [{ filename: "chapter-001.md", content: "# Outside\n" }],
    });
    symlinkSync(outside, join(importsRoot, "linked-source"), "dir");

    for (const source of ["missing", "not-a-directory", "linked-source"]) {
      expect(() => reader.readConfinedLegacyWorkspace(dataDirectory, source)).toThrowError(
        new NotFoundError(IMPORT_NOT_FOUND_ERROR),
      );
    }

    const linkedRootData = workspacePath("linked-web-root");
    mkdirSync(linkedRootData, { recursive: true });
    symlinkSync(outside, join(linkedRootData, "imports"), "dir");
    expect(() => reader.readConfinedLegacyWorkspace(linkedRootData, "safe")).toThrowError(
      new NotFoundError(IMPORT_NOT_FOUND_ERROR),
    );
  });

  it("validates confined workspace files without traversing their links", () => {
    const dataDirectory = workspacePath("web-structure");
    const importsRoot = join(dataDirectory, "imports");
    mkdirSync(join(importsRoot, "missing-story"), { recursive: true });
    expect(() => reader.readConfinedLegacyWorkspace(dataDirectory, "missing-story")).toThrowError(
      new InvalidOperationError("Legacy workspace must contain story.yaml."),
    );

    const source = makeLegacyWorkspace(join(importsRoot, "linked-chapter"), {
      chapters: [{ filename: "chapter-001.md", content: "# One\n" }],
    });
    const outside = makeWorkspace("outside-chapter", {
      chapters: [{ filename: "chapter-001.md", content: "# Outside\n" }],
    });
    const linkedStory = makeLegacyWorkspace(join(importsRoot, "linked-story"), { chapters: [] });
    unlinkSync(join(linkedStory, "story.yaml"));
    symlinkSync(join(outside, "story.yaml"), join(linkedStory, "story.yaml"));
    expect(() => reader.readConfinedLegacyWorkspace(dataDirectory, "linked-story")).toThrowError(
      new InvalidOperationError("Legacy workspace must contain story.yaml."),
    );

    symlinkSync(
      join(outside, "manuscript", "chapters", "chapter-001.md"),
      join(source, "manuscript", "chapters", "chapter-002.md"),
    );

    expect(() => reader.readConfinedLegacyWorkspace(dataDirectory, "linked-chapter")).toThrowError(
      new InvalidOperationError("Legacy workspace must not contain symbolic links."),
    );
  });
});
