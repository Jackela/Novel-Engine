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
  private readonly running = new Map<string, InFlightTarget>();
  private readonly projectActivity = new Map<string, number>();
  private readonly projectExclusive = new Map<string, string>();

  private static keyFor(target: InFlightTarget): string {
    return target.documentId === null
      ? `${target.projectId}:${target.operation}`
      : `${target.projectId}:${target.documentId}:${target.operation}`;
  }

  enter(target: InFlightTarget): void {
    const exclusiveOperation = this.projectExclusive.get(target.projectId);
    if (exclusiveOperation !== undefined) {
      throw new OperationInFlightError(target.projectId, null, exclusiveOperation);
    }
    const key = InFlightOperationGuard.keyFor(target);
    if (this.running.has(key)) {
      throw new OperationInFlightError(target.projectId, target.documentId, target.operation);
    }
    this.running.set(key, target);
    this.projectActivity.set(
      target.projectId,
      (this.projectActivity.get(target.projectId) ?? 0) + 1,
    );
  }

  exit(target: InFlightTarget): void {
    if (!this.running.delete(InFlightOperationGuard.keyFor(target))) return;
    const remaining = (this.projectActivity.get(target.projectId) ?? 1) - 1;
    if (remaining === 0) this.projectActivity.delete(target.projectId);
    else this.projectActivity.set(target.projectId, remaining);
  }

  /**
   * Excludes every provider/export operation for a project while an
   * irreversible project-wide transition commits and performs its cleanup.
   */
  enterProjectExclusive(projectId: string, operation: string): void {
    const exclusiveOperation = this.projectExclusive.get(projectId);
    if (exclusiveOperation !== undefined) {
      throw new OperationInFlightError(projectId, null, exclusiveOperation);
    }
    if ((this.projectActivity.get(projectId) ?? 0) > 0) {
      const blocker = [...this.running.values()].find((target) => target.projectId === projectId);
      if (blocker !== undefined) {
        throw new OperationInFlightError(blocker.projectId, blocker.documentId, blocker.operation);
      }
    }
    this.projectExclusive.set(projectId, operation);
  }

  exitProjectExclusive(projectId: string): void {
    this.projectExclusive.delete(projectId);
  }
}
