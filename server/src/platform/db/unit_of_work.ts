/**
 * The SQLite implementation of the transaction boundary the use cases own.
 *
 * `better-sqlite3`'s `transaction()` is used rather than hand-written
 * BEGIN/COMMIT for one reason: nesting. A use case may call a helper that also
 * wraps work in `run`, and a manual implementation would either issue a second
 * BEGIN (an error) or need its own depth counter and savepoint logic. The driver
 * already does that correctly, so the port delegates instead of reimplementing.
 *
 * `IMMEDIATE` rather than the default deferred mode: the write lock is taken at
 * BEGIN, so a transaction that reads-then-writes cannot fail halfway with
 * SQLITE_BUSY after it has already decided what to write.
 */

import type Database from "better-sqlite3";

import type { UnitOfWork } from "../kernel/unit_of_work.js";

export function createUnitOfWork(raw: Database.Database): UnitOfWork {
  return {
    run<T>(fn: () => T): T {
      // The driver returns a wrapped function; invoking it opens the outermost
      // transaction, or a savepoint when one is already open.
      return raw.transaction(fn).immediate();
    },
  };
}
