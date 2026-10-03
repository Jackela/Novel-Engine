import { lstat } from "node:fs/promises";
import { basename, dirname, join } from "node:path";

import { errorCode } from "../error_code.js";
import { DATABASE_FILENAME } from "./backup.js";

/** Directory resources owned by one exact configured SQLite file. */
export function databaseDataDirectory(databasePath: string): string {
  return dirname(databasePath);
}

/**
 * The legacy default sibling standing beside a configured database, or null
 * when the configured path is the default itself or no sibling exists. The
 * read-only doctor reports this ambiguity without holding data-directory
 * ownership; startup still asserts through `assertNoLegacyDatabaseSibling`
 * while its ownership lock makes the decision race-free.
 */
export async function legacyDatabaseSibling(
  databasePath: string,
  dataDirectory: string,
): Promise<string | null> {
  if (basename(databasePath) === DATABASE_FILENAME) return null;
  const legacyPath = join(dataDirectory, DATABASE_FILENAME);
  try {
    await lstat(legacyPath);
  } catch (error) {
    if (errorCode(error) === "ENOENT") return null;
    throw error;
  }
  return legacyPath;
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
  const legacyPath = await legacyDatabaseSibling(databasePath, dataDirectory);
  if (legacyPath === null) return;

  throw new Error(
    `Refusing configured database ${databasePath}: legacy default sibling ${legacyPath} exists. ` +
      "Choose one database authority explicitly; Novel Engine will not move, merge, or fall back.",
  );
}
