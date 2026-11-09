import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { afterEach, describe, expect, it } from "vitest";

import { type DatabaseHandle, openDatabase } from "../../src/platform/db/connection.js";
import { createUnitOfWork } from "../../src/platform/db/unit_of_work.js";

const opened: DatabaseHandle[] = [];
const directories: string[] = [];

function memoryDatabase(): DatabaseHandle {
  const handle = openDatabase({ path: ":memory:" });
  opened.push(handle);
  return handle;
}

function fileDatabase(): DatabaseHandle {
  const directory = mkdtempSync(join(tmpdir(), "novel-engine-db-"));
  directories.push(directory);
  const handle = openDatabase({ path: join(directory, "probe.sqlite3") });
  opened.push(handle);
  return handle;
}

afterEach(() => {
  for (const handle of opened.splice(0)) handle.close();
  for (const directory of directories.splice(0))
    rmSync(directory, { recursive: true, force: true });
});

function probeTable(handle: DatabaseHandle): void {
  handle.raw.exec("CREATE TABLE probe (id TEXT PRIMARY KEY NOT NULL)");
}

function count(handle: DatabaseHandle): number {
  const row = handle.raw.prepare("SELECT COUNT(*) AS n FROM probe").get() as { n: number };
  return row.n;
}

function insert(handle: DatabaseHandle, id: string): void {
  handle.raw.prepare("INSERT INTO probe (id) VALUES (?)").run(id);
}

describe("openDatabase", () => {
  it("enforces foreign keys and uses WAL on a file database", () => {
    const handle = fileDatabase();
    expect(handle.raw.pragma("foreign_keys", { simple: true })).toBe(1);
    expect(handle.raw.pragma("journal_mode", { simple: true })).toBe("wal");
    expect(handle.raw.pragma("synchronous", { simple: true })).toBe(2);
  });

  it("applies the configured busy timeout", () => {
    const handle = openDatabase({ path: ":memory:", busyTimeoutMs: 250 });
    opened.push(handle);
    expect(handle.raw.pragma("busy_timeout", { simple: true })).toBe(250);
  });
});

describe("createUnitOfWork", () => {
  it("commits a successful run", () => {
    const handle = memoryDatabase();
    probeTable(handle);
    const uow = createUnitOfWork(handle.raw);
    uow.run(() => insert(handle, "a"));
    expect(count(handle)).toBe(1);
  });

  it("rolls back the whole run when the body throws", () => {
    const handle = memoryDatabase();
    probeTable(handle);
    const uow = createUnitOfWork(handle.raw);
    expect(() =>
      uow.run(() => {
        insert(handle, "a");
        throw new Error("boom");
      }),
    ).toThrow("boom");
    expect(count(handle)).toBe(0);
  });

  it("joins an outer transaction rather than opening a second one", () => {
    const handle = memoryDatabase();
    probeTable(handle);
    const uow = createUnitOfWork(handle.raw);
    uow.run(() => {
      insert(handle, "outer");
      uow.run(() => insert(handle, "inner"));
    });
    expect(count(handle)).toBe(2);
  });

  it("rolls back only the inner scope when a nested run fails and is caught", () => {
    const handle = memoryDatabase();
    probeTable(handle);
    const uow = createUnitOfWork(handle.raw);
    uow.run(() => {
      insert(handle, "kept");
      try {
        uow.run(() => {
          insert(handle, "discarded");
          throw new Error("inner");
        });
      } catch {
        // The outer scope decides to continue.
      }
    });
    expect(count(handle)).toBe(1);
    const remaining = handle.raw.prepare("SELECT id FROM probe").all() as Array<{ id: string }>;
    expect(remaining.map((row) => row.id)).toEqual(["kept"]);
  });

  it("propagates a nested failure that is not caught, discarding the outer work too", () => {
    const handle = memoryDatabase();
    probeTable(handle);
    const uow = createUnitOfWork(handle.raw);
    expect(() =>
      uow.run(() => {
        insert(handle, "outer");
        uow.run(() => {
          throw new Error("inner");
        });
      }),
    ).toThrow("inner");
    expect(count(handle)).toBe(0);
  });
});
