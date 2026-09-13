import type { FastifyInstance } from "fastify";

/** Close a resource without discarding either the primary or cleanup failure. */
export async function closeResourceAndRethrow(
  close: () => Promise<unknown> | unknown,
  originalError: unknown,
  aggregateMessage: string,
): Promise<never> {
  try {
    await close();
  } catch (cleanupError) {
    throw new AggregateError([originalError, cleanupError], aggregateMessage);
  }
  throw originalError;
}

/** Close a partially initialized app without discarding either failure. */
export async function closeAppAndRethrow(
  app: FastifyInstance,
  originalError: unknown,
  aggregateMessage: string,
): Promise<never> {
  return closeResourceAndRethrow(() => app.close(), originalError, aggregateMessage);
}
