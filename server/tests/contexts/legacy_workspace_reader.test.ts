import { realpathSync, symlinkSync, unlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";
import { describe, expect, it } from "vitest";

import { FsLegacyWorkspaceReader } from "../../src/contexts/studio/infrastructure/fs_legacy_workspace_reader.js";
import { InvalidOperationError } from "../../src/shared/domain/exceptions.js";
import {
  directoryFingerprint,
  type LegacyWorkspaceInput,
  makeLegacyWorkspace,
} from "../legacy_workspace_fixtures.js";

const reader = new FsLegacyWorkspaceReader();

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
});
