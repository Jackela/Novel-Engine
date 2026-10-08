import { mkdir, mkdtemp, readFile, rm, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { AcpWorkspace } from "../../src/contexts/ai/infrastructure/providers/AcpWorkspace.js";

describe("ACP client-owned material workspace", () => {
  it("reads and writes material copies while refusing traversal, secret/database paths and symlinks", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-acp-materials-"));
    const outside = await mkdtemp(join(tmpdir(), "novel-engine-acp-canary-"));
    try {
      const canary = join(outside, "canary.md");
      await writeFile(canary, "untouched");
      await writeFile(join(directory, "material.md"), "first\nsecond\nthird");
      await symlink(canary, join(directory, "link.md"));
      const workspace = await AcpWorkspace.open(directory);
      expect(
        await workspace.read({ sessionId: "session", path: "material.md", line: 2, limit: 1 }),
      ).toEqual({ content: "second" });
      await workspace.write({ sessionId: "session", path: "copy.md", content: "edited copy" });
      expect(await readFile(join(directory, "copy.md"), "utf8")).toBe("edited copy");
      for (const path of [
        canary,
        "../outside.md",
        ".env.local",
        "novel-engine.sqlite3",
        "exports/original.md",
        "link.md",
      ]) {
        await expect(
          workspace.write({ sessionId: "session", path, content: "bad" }),
        ).rejects.toThrow();
      }
      expect(await readFile(canary, "utf8")).toBe("untouched");
    } finally {
      await rm(directory, { recursive: true, force: true });
      await rm(outside, { recursive: true, force: true });
    }
  });
  it("refuses directory aliases into protected originals before reading or writing", async () => {
    const root = await mkdtemp(join(tmpdir(), "novel-engine-acp-alias-"));
    try {
      await mkdir(join(root, "exports"));
      await writeFile(join(root, "exports", "original.md"), "immutable-original");
      await symlink(join(root, "exports"), join(root, "copies"));
      const workspace = await AcpWorkspace.open(root);
      await expect(
        workspace.read({ sessionId: "s", path: "copies/original.md" }),
      ).rejects.toThrow();
      await expect(
        workspace.write({ sessionId: "s", path: "copies/original.md", content: "bad" }),
      ).rejects.toThrow();
      expect(await readFile(join(root, "exports", "original.md"), "utf8")).toBe(
        "immutable-original",
      );
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });
});
