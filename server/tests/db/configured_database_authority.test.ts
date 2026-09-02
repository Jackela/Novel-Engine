import { existsSync } from "node:fs";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

describe("configured database authority", () => {
  it("opens the exact path without creating the default sibling", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-exact-db-"));
    const databasePath = join(directory, "author.sqlite3");
    const legacyPath = join(directory, "novel-engine.sqlite3");

    const studio = await openStudioDatabase(databasePath);
    try {
      expect(studio.databasePath).toBe(databasePath);
      expect(existsSync(databasePath)).toBe(true);
      expect(existsSync(legacyPath)).toBe(false);
    } finally {
      studio.close();
    }
  });

  it("fails before backup or opening when the default sibling exists", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-legacy-db-"));
    const databasePath = join(directory, "author.sqlite3");
    const legacyPath = join(directory, "novel-engine.sqlite3");
    await writeFile(legacyPath, "legacy authority");

    await expect(openStudioDatabase(databasePath)).rejects.toThrow(
      expect.objectContaining({ message: expect.stringContaining(databasePath) }),
    );
    expect(existsSync(databasePath)).toBe(false);
    expect(existsSync(join(directory, "backups"))).toBe(false);
  });

  it("does not select or mutate either file when both candidates exist", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-ambiguous-db-"));
    const databasePath = join(directory, "author.sqlite3");
    const legacyPath = join(directory, "novel-engine.sqlite3");
    await writeFile(databasePath, "configured authority");
    await writeFile(legacyPath, "legacy authority");

    await expect(openStudioDatabase(databasePath)).rejects.toThrow(
      /will not move, merge, or fall back/i,
    );
    await expect(readFile(databasePath, "utf8")).resolves.toBe("configured authority");
    await expect(readFile(legacyPath, "utf8")).resolves.toBe("legacy authority");
    expect(existsSync(join(directory, "backups"))).toBe(false);
  });
});
