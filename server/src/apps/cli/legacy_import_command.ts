import { randomBytes } from "node:crypto";
import {
  ImportService,
  type LegacyImportResult,
} from "../../contexts/studio/application/import_service.js";
import { FsLegacyWorkspaceReader } from "../../contexts/studio/infrastructure/fs_legacy_workspace_reader.js";
import { ProjectStorePart } from "../../contexts/studio/infrastructure/project_store_part.js";
import { openReconciledStudioDatabase } from "../../contexts/studio/infrastructure/reconciled_studio_database.js";
import { AuthService } from "../../shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../shared/infrastructure/db/auth_store.js";

interface LegacyImportCommandInput {
  /** Exact database authority (backup → migrate → reconcile exports → recover jobs runs first). */
  databasePath: string;
  /** Explicit legacy workspace path; the CLI is not confined to data/imports. */
  source: string;
  /** Owner username; omitted falls back to the installation's single owner. */
  owner?: string | undefined;
}

/**
 * The `novel-engine import` command body — the programmatic entry the CLI
 * dispatcher (#272) registers. It owns a short-lived runtime (database
 * lifecycle included), runs as the owner principal without HTTP
 * authentication, and returns a bounded import summary for the dispatcher to
 * print. The legacy source directory is never modified.
 */
export async function runLegacyImportCommand(
  input: LegacyImportCommandInput,
): Promise<LegacyImportResult> {
  const database = await openReconciledStudioDatabase(input.databasePath);
  try {
    const authService = new AuthService({
      store: new DrizzleAuthStore(database.db),
      // The maintenance principal never mints or validates session tokens,
      // so the HMAC key is an ephemeral per-run value.
      sessionSecret: randomBytes(32).toString("base64url"),
    });
    const principal = authService.localOwnerPrincipal(input.owner);
    const imports = new ImportService(
      new ProjectStorePart(database.db),
      new FsLegacyWorkspaceReader(),
    );
    return await imports.importLegacyWorkspace(principal, input.source);
  } finally {
    database.close();
  }
}
