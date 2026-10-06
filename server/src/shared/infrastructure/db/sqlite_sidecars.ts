import { unlink } from "node:fs/promises";

import { errorCode } from "../error_code.js";

/**
 * Sidecars SQLite creates next to a database it opens: the write-ahead log
 * and its shared-memory index, plus the rollback journal in non-WAL modes.
 * None of them are part of a finished backup artifact, so a read-only
 * inspection must not leave them behind.
 */
export const SQLITE_SIDECAR_SUFFIXES = ["-wal", "-shm", "-journal"] as const;

/**
 * Remove the sidecars of `filePath` after an inspection connection closed.
 * A missing sidecar is the clean case (ENOENT); any other removal failure
 * throws naming the exact file so a residue is never silently accepted.
 */
export async function removeSqliteSidecars(filePath: string): Promise<void> {
  for (const suffix of SQLITE_SIDECAR_SUFFIXES) {
    try {
      await unlink(filePath + suffix);
    } catch (error) {
      if (errorCode(error) === "ENOENT") continue;
      const detail = error instanceof Error ? error.message : String(error);
      throw new Error(`Removing the ${suffix} sidecar of ${filePath} failed: ${detail}`, {
        cause: error,
      });
    }
  }
}
