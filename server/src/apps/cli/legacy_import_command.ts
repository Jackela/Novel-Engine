import { randomBytes } from "node:crypto";
import { textProviderFactory } from "../../contexts/ai/infrastructure/providers/text_provider_factory.js";
import type { LegacyImportResult } from "../../contexts/studio/application/import_service.js";
import { createStudioServices } from "../../contexts/studio/application/studio_services.js";
import { DrizzleStudioStore } from "../../contexts/studio/infrastructure/drizzle_studio_store.js";
import { FilesystemExportArtifactGateway } from "../../contexts/studio/infrastructure/export_artifact_files.js";
import { DatabaseExportPublicationCleanupJournal } from "../../contexts/studio/infrastructure/export_publication_cleanup_journal.js";
import { ExportStorePart } from "../../contexts/studio/infrastructure/export_store_part.js";
import { FsLegacyWorkspaceReader } from "../../contexts/studio/infrastructure/fs_legacy_workspace_reader.js";
import { FilesystemProjectArtifactCleaner } from "../../contexts/studio/infrastructure/project_artifact_files.js";
import { openReconciledStudioDatabase } from "../../contexts/studio/infrastructure/reconciled_studio_database.js";
import { AuthService } from "../../shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../shared/infrastructure/db/auth_store.js";

export interface LegacyImportCommandInput {
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
    const services = createStudioServices(new DrizzleStudioStore({ database: database.db }), {
      providerFactory: textProviderFactory({}),
      legacyWorkspaceReader: new FsLegacyWorkspaceReader(),
      // The import command never touches exports, but the service graph is
      // complete: the same store/gateway the API composition root wires.
      artifactStore: new ExportStorePart(database.db),
      artifactFiles: new FilesystemExportArtifactGateway(database.dataDirectory, {
        cleanupJournal: new DatabaseExportPublicationCleanupJournal(database.db),
      }),
      projectArtifactCleaner: new FilesystemProjectArtifactCleaner(database.dataDirectory),
    });
    return await services.imports.importLegacyWorkspace(principal, input.source);
  } finally {
    database.close();
  }
}
