import { randomUUID } from "node:crypto";
import { existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type Database from "better-sqlite3";
import { eq } from "drizzle-orm";
import { migrate } from "drizzle-orm/better-sqlite3/migrator";

import { backupDatabaseFile, DATABASE_FILENAME } from "./backup.js";
import { openConnection, type StudioSqliteDatabase } from "./connection.js";
import { jobEvents, jobs } from "./schema.js";

const SEARCH_DEPTH = 8;
const PACKAGE_ROOT_MARKER = "drizzle.config.ts";
const MIGRATIONS_DIRECTORY = "drizzle";

/** The fixed restart error and event reason are contract surfaces; keep byte-identical. */
const RESTART_INTERRUPTED_ERROR = "Job lost its execution lease during process restart.";
const RESTART_EVENT_DETAILS = '{"reason":"execution_lease_lost_during_restart"}';

export interface StudioDatabase {
  readonly db: StudioSqliteDatabase;
  readonly raw: Database.Database;
  readonly databasePath: string;
  close(): void;
}

/**
 * The startup pipeline of the content authority, in the adjudicated order:
 * online backup of any pre-existing non-empty database, then schema
 * migrations, then restart recovery — only afterwards may the caller serve.
 */
export async function openStudioDatabase(directory: string): Promise<StudioDatabase> {
  mkdirSync(directory, { recursive: true });
  const databasePath = join(directory, DATABASE_FILENAME);
  await backupDatabaseFile(databasePath);

  const { raw, db } = openConnection(databasePath);
  try {
    migrate(db, { migrationsFolder: locateMigrationsFolder() });
    recoverInterruptedJobs(db);
  } catch (error) {
    raw.close();
    throw error;
  }
  return {
    db,
    raw,
    databasePath,
    close: () => {
      raw.close();
    },
  };
}

/**
 * Restart recovery is startup-time row updates and event inserts only: every
 * running job becomes interrupted with the fixed restart error and one job
 * event naming the restart reason. No other machinery participates.
 */
function recoverInterruptedJobs(db: StudioSqliteDatabase): number {
  const now = new Date();
  return db.transaction((tx) => {
    const running = tx.select({ id: jobs.id }).from(jobs).where(eq(jobs.status, "running")).all();
    for (const job of running) {
      const jobId = job.id;
      tx.update(jobs)
        .set({
          status: "interrupted",
          error: RESTART_INTERRUPTED_ERROR,
          updated_at: now,
          finished_at: now,
        })
        .where(eq(jobs.id, jobId))
        .run();
      tx.insert(jobEvents)
        .values({
          id: randomUUID(),
          job_id: jobId,
          status: "interrupted",
          details_json: RESTART_EVENT_DETAILS,
          created_at: now,
        })
        .run();
    }
    return running.length;
  });
}

function locateMigrationsFolder(): string {
  let directory = dirname(fileURLToPath(import.meta.url));
  for (let depth = 0; depth < SEARCH_DEPTH; depth += 1) {
    if (existsSync(join(directory, PACKAGE_ROOT_MARKER))) {
      return join(directory, MIGRATIONS_DIRECTORY);
    }
    const parent = dirname(directory);
    if (parent === directory) {
      break;
    }
    directory = parent;
  }
  throw new Error(
    "drizzle migrations folder not found above server/src — run the server from the workspace checkout",
  );
}
