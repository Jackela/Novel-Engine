import { OperationInFlightError } from "../domain/exceptions.js";

export interface InFlightTarget {
  readonly projectId: string;
  readonly documentId: string | null;
  readonly operation: string;
}

/**
 * Serializes identical synchronous pipeline operations inside one app
 * instance (#305). The pipeline records only terminal job rows — work runs
 * before any row exists — so a database constraint cannot see the in-flight
 * window; this process-local guard closes it. Targets are principal-scoped
 * by construction: a project (and its documents) belongs to exactly one
 * principal, so identical target ids imply the same principal.
 */
export class InFlightOperationGuard {
  private readonly running = new Set<string>();

  private static keyFor(target: InFlightTarget): string {
    return target.documentId === null
      ? `${target.projectId}:${target.operation}`
      : `${target.projectId}:${target.documentId}:${target.operation}`;
  }

  enter(target: InFlightTarget): void {
    const key = InFlightOperationGuard.keyFor(target);
    if (this.running.has(key)) {
      throw new OperationInFlightError(target.projectId, target.documentId, target.operation);
    }
    this.running.add(key);
  }

  exit(target: InFlightTarget): void {
    this.running.delete(InFlightOperationGuard.keyFor(target));
  }
}
