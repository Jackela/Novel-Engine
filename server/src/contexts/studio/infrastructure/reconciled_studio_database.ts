import {
  openStudioDatabase,
  type StudioDatabase,
} from "../../../shared/infrastructure/db/startup.js";
import {
  type ExportPublicationRecoveryReport,
  reconcileExportPublications,
} from "./export_publication_recovery.js";

export interface ReconciledStudioDatabaseOptions {
  readonly onReconciled?:
    | ((report: ExportPublicationRecoveryReport) => Promise<void> | void)
    | undefined;
}

/** Production/maintenance opener: migrations, export reconciliation, then job recovery. */
export function openReconciledStudioDatabase(
  databasePath: string,
  options: ReconciledStudioDatabaseOptions = {},
): Promise<StudioDatabase> {
  return openStudioDatabase(databasePath, {
    beforeJobRecovery: async (database, dataDirectory) => {
      const report = await reconcileExportPublications(database, dataDirectory);
      await options.onReconciled?.(report);
    },
  });
}
