import Database from "better-sqlite3";
import { describe, expect, it } from "vitest";

import { sqliteHealthProbe } from "../../src/shared/infrastructure/db/sqlite_health_probe.js";

describe("SQLite health probe", () => {
  it("reports the live handle healthy and the same closed handle unhealthy", async () => {
    const raw = new Database(":memory:");
    const probe = sqliteHealthProbe(raw);

    await expect(probe()).resolves.toEqual({
      components: [{ name: "database", status: "healthy", message: "SQLite ready" }],
    });

    raw.close();
    await expect(probe()).resolves.toEqual({
      components: [
        { name: "database", status: "unhealthy", error: "database health check failed" },
      ],
    });
  });

  it("normalizes known SQLite failures but exposes unexpected programming errors", async () => {
    const sqliteFailure = new Database(":memory:");
    Object.defineProperty(sqliteFailure, "prepare", {
      configurable: true,
      value: () => {
        throw new Database.SqliteError("busy", "SQLITE_BUSY");
      },
    });
    await expect(sqliteHealthProbe(sqliteFailure)()).resolves.toEqual({
      components: [
        { name: "database", status: "unhealthy", error: "database health check failed" },
      ],
    });
    sqliteFailure.close();

    const programmingFailure = new Database(":memory:");
    Object.defineProperty(programmingFailure, "prepare", {
      configurable: true,
      value: () => {
        throw new TypeError("unexpected probe bug");
      },
    });
    await expect(sqliteHealthProbe(programmingFailure)()).rejects.toThrow("unexpected probe bug");
    programmingFailure.close();
  });
});
