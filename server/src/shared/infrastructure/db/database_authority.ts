import { lstat } from "node:fs/promises";
import { basename, dirname, join } from "node:path";

import { DATABASE_FILENAME } from "./backup.js";

/** Directory resources owned by one exact configured SQLite file. */
export function databaseDataDirectory(databasePath: string): string {
  return dirname(databasePath);
}

/**
 * Fail closed when an older runtime may have written the default sibling
 * instead of the configured basename. Callers hold data-directory ownership
 * before invoking this check, so no competing startup can race the decision.
 */
export async function assertNoLegacyDatabaseSibling(
  databasePath: string,
  dataDirectory: string,
): Promise<void> {
  if (basename(databasePath) === DATABASE_FILENAME) return;
  const legacyPath = join(dataDirectory, DATABASE_FILENAME);
  try {
    await lstat(legacyPath);
  } catch (error) {
    if (errorCode(error) === "ENOENT") return;
    throw error;
  }

  throw new Error(
    `Refusing configured database ${databasePath}: legacy default sibling ${legacyPath} exists. ` +
      "Choose one database authority explicitly; Novel Engine will not move, merge, or fall back.",
  );
}

function errorCode(error: unknown): string | undefined {
  if (typeof error !== "object" || error === null || !("code" in error)) return undefined;
  return typeof error.code === "string" ? error.code : undefined;
}
