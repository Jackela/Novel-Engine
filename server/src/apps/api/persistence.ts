import type { FastifyInstance } from "fastify";
import { openStudioDatabase, type StudioDatabase } from "../../shared/infrastructure/db/startup.js";

/** Persistence handles bound to a configured data directory. */
export interface PersistenceHandles {
  dataDirectory: string;
  db: StudioDatabase;
}

/**
 * Open the content-authority database for a configured data directory. A
 * failed start closes the app before rethrowing so no listeners survive.
 */
export async function openPersistence(
  app: FastifyInstance,
  dataDirectory: string,
): Promise<PersistenceHandles> {
  try {
    return { dataDirectory, db: await openStudioDatabase(dataDirectory) };
  } catch (error) {
    await app.close();
    throw error;
  }
}
