/**
 * Transaction boundary owned by the use case, not by the adapter.
 *
 * The contract is deliberately narrow: a use case wraps its writes in one
 * `run`, and every repository call inside that closure participates in the same
 * transaction. Adapters must never open their own transaction — nested `run`
 * calls join the outer one and only the outermost commits.
 *
 * Why a closure instead of passing a transaction handle: better-sqlite3 is
 * synchronous, so there is no interleaving to guard against, and keeping `tx`
 * out of every repository signature keeps the ports readable. The adapter reads
 * the ambient transaction from this module.
 *
 * Failure semantics: if `fn` throws, the transaction rolls back and the error
 * propagates unchanged. A use case that throws after a partial write leaves no
 * trace.
 */

export interface UnitOfWork {
  run<T>(fn: () => T): T;
}

/**
 * A no-op implementation for tests and for read-only paths that do not need
 * atomicity. It runs the closure immediately and swallows nothing.
 */
export const passthroughUnitOfWork: UnitOfWork = {
  run: <T>(fn: () => T): T => fn(),
};
