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
  dataDirectory: string,
  options: ReconciledStudioDatabaseOptions = {},
): Promise<StudioDatabase> {
  return openStudioDatabase(dataDirectory, {
    beforeJobRecovery: async (database) => {
      const report = await reconcileExportPublications(database, dataDirectory);
      await options.onReconciled?.(report);
    },
  });
}
