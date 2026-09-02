import type { FastifyInstance } from "fastify";
import { openReconciledStudioDatabase } from "../../contexts/studio/infrastructure/reconciled_studio_database.js";
import type { StudioDatabase } from "../../shared/infrastructure/db/startup.js";

/** Persistence handles bound to a configured data directory. */
export interface PersistenceHandles {
  dataDirectory: string;
  db: StudioDatabase;
}

/** Open the content-authority database and immediately bind its lifetime to the app. */
export async function openPersistence(
  app: FastifyInstance,
  databasePath: string,
): Promise<PersistenceHandles> {
  const db = await openReconciledStudioDatabase(databasePath, {
    onReconciled: (report) => {
      app.log.info(
        { export_publication_recovery: true, ...report },
        "export publication recovery completed",
      );
    },
  });
  try {
    app.addHook("onClose", async () => {
      db.close();
    });
  } catch (error) {
    try {
      db.close();
    } catch (cleanupError) {
      throw new AggregateError(
        [error, cleanupError],
        "Database opened but lifecycle registration and cleanup both failed.",
      );
    }
    throw error;
  }
  return { dataDirectory: db.dataDirectory, db };
}
