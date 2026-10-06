import { openReconciledStudioDatabase } from "../../contexts/studio/infrastructure/reconciled_studio_database.js";
import type { ServerConfig } from "../../shared/infrastructure/config/server_config.js";
import {
  type OwnerResetSummary,
  resetOwnerState,
} from "../../shared/infrastructure/db/owner_reset.js";

type WriteLine = (line: string) => void;

/**
 * `novel-engine owner reset`: the out-of-band recovery for a lost, forgotten,
 * or taken Owner credential. There is no email recovery by design; this
 * command is the recovery path. It opens the reconciled database, which takes
 * the same exclusive data-directory ownership every maintenance command
 * takes, so a running server refuses the reset before any row is read or
 * written. The Owner and its sessions are deleted in one transaction
 * (sessions first — they are live bearer credentials), and the
 * machine-readable summary is printed: owners_deleted, sessions_deleted, and
 * the removed username. Book content is never touched; the next
 * `POST /api/setup` creates a fresh Owner. An unrecognized subcommand prints
 * the command usage and returns exit code 2 without touching the database.
 */
export async function runOwnerResetCommand(
  flags: ReadonlyMap<string, string | true>,
  config: ServerConfig,
  writeLine: WriteLine,
): Promise<number> {
  if (flags.get("reset") !== true) {
    writeLine("Usage: novel-engine owner reset");
    return 2;
  }
  const studio = await openReconciledStudioDatabase(config.databasePath);
  let summary: OwnerResetSummary;
  try {
    summary = resetOwnerState(studio.db);
  } finally {
    studio.close();
  }
  writeLine(JSON.stringify(summary));
  return 0;
}
