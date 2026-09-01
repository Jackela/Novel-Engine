import { execFile, spawn } from "node:child_process";
import { once } from "node:events";
import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { promisify } from "node:util";

import Database from "better-sqlite3";
import { describe, expect, it } from "vitest";

import { acquireDataDirectoryLock } from "../../src/shared/infrastructure/db/data_directory_lock.js";

const runFile = promisify(execFile);
const serverRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const lockModuleUrl = pathToFileURL(
  resolve(serverRoot, "src/shared/infrastructure/db/data_directory_lock.ts"),
).href;
const childScript = `
  import { acquireDataDirectoryLock } from ${JSON.stringify(lockModuleUrl)};
  const lock = acquireDataDirectoryLock(process.argv.at(-1));
  lock.close();
`;
const holdingChildScript = `
  import { acquireDataDirectoryLock } from ${JSON.stringify(lockModuleUrl)};
  acquireDataDirectoryLock(process.argv.at(-1));
  process.stdout.write("locked\\n");
  setInterval(() => undefined, 1_000);
`;

function acquireFromChild(directory: string) {
  return runFile(process.execPath, ["--input-type=module", "--eval", childScript, directory], {
    cwd: serverRoot,
  });
}

describe("data-directory process lock", () => {
  it("excludes a separate Node process and releases ownership on close", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-process-lock-"));
    const first = acquireDataDirectoryLock(directory);
    try {
      await expect(acquireFromChild(directory)).rejects.toMatchObject({
        stderr: expect.stringMatching(/already owned by another Novel Engine process/i),
      });
    } finally {
      first.close();
    }

    await expect(acquireFromChild(directory)).resolves.toMatchObject({ stderr: "" });
  });

  it("lets a later process acquire ownership after an abrupt owner exit", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-process-lock-crash-"));
    const child = spawn(
      process.execPath,
      ["--input-type=module", "--eval", holdingChildScript, directory],
      { cwd: serverRoot, stdio: ["ignore", "pipe", "pipe"] },
    );
    try {
      const ready = await Promise.race([
        once(child.stdout, "data").then(([chunk]) => String(chunk)),
        once(child, "exit").then(([code]) => {
          throw new Error(`Lock-holder child exited before readiness with code ${String(code)}.`);
        }),
      ]);
      expect(ready).toContain("locked");
      expect(() => acquireDataDirectoryLock(directory)).toThrow(
        /already owned by another Novel Engine process/i,
      );
    } finally {
      child.kill("SIGKILL");
      if (child.exitCode === null && child.signalCode === null) await once(child, "exit");
    }

    const recovered = acquireDataDirectoryLock(directory);
    recovered.close();
  });

  it("keeps a failed release retryable without dropping ownership", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-process-lock-retry-"));
    const originalClose = Database.prototype.close;
    let failOwnershipClose = true;
    Database.prototype.close = function closeWithOneFailure() {
      if (failOwnershipClose && this.name.endsWith(".novel-engine-ownership.sqlite3")) {
        failOwnershipClose = false;
        throw new Error("simulated ownership close failure");
      }
      return originalClose.call(this);
    };

    const ownership = acquireDataDirectoryLock(directory);
    try {
      expect(() => ownership.close()).toThrow("simulated ownership close failure");
      expect(() => acquireDataDirectoryLock(directory)).toThrow(
        /already owned by another Novel Engine process/i,
      );

      expect(() => ownership.close()).not.toThrow();
      const reacquired = acquireDataDirectoryLock(directory);
      reacquired.close();
    } finally {
      Database.prototype.close = originalClose;
      ownership.close();
    }
  });
});
