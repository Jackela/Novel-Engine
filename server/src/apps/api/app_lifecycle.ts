import type { FastifyInstance } from "fastify";

/**
 * Close a resource without discarding either the primary or cleanup failure.
 *
 * The aggregate is thrown only because the cleanup failed — when `close()`
 * succeeds the original error propagates alone — so the cleanup failure is also
 * attached as the `cause`, while `errors` keeps both failures reachable.
 */
export async function closeResourceAndRethrow(
  close: () => Promise<unknown> | unknown,
  originalError: unknown,
  aggregateMessage: string,
): Promise<never> {
  try {
    await close();
  } catch (cleanupError) {
    throw new AggregateError([originalError, cleanupError], aggregateMessage, {
      cause: cleanupError,
    });
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
