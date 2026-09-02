import { OperationCapacityExceededError, OperationInFlightError } from "../domain/exceptions.js";

export interface InFlightTarget {
  readonly projectId: string;
  readonly documentId: string | null;
  readonly operation: string;
}

export interface OperationCapacityPolicy {
  readonly applicationLimit: number;
  readonly projectLimit: number;
}

export const DEFAULT_OPERATION_CAPACITY_POLICY: OperationCapacityPolicy = Object.freeze({
  applicationLimit: 4,
  projectLimit: 2,
});

export interface InFlightOperationPermit {
  release(): void;
}

interface RunningOperation {
  readonly target: InFlightTarget;
  readonly token: symbol;
}

interface ProjectExclusiveOperation {
  readonly operation: string;
  readonly token: symbol;
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
  private readonly running = new Map<string, RunningOperation>();
  private readonly projectActivity = new Map<string, number>();
  private readonly projectExclusive = new Map<string, ProjectExclusiveOperation>();
  private readonly policy: OperationCapacityPolicy;

  constructor(policy: OperationCapacityPolicy = DEFAULT_OPERATION_CAPACITY_POLICY) {
    this.policy = { ...policy };
  }

  private static keyFor(target: InFlightTarget): string {
    return JSON.stringify([target.projectId, target.documentId, target.operation]);
  }

  acquire(target: InFlightTarget): InFlightOperationPermit {
    const exclusiveOperation = this.projectExclusive.get(target.projectId);
    if (exclusiveOperation !== undefined) {
      throw new OperationInFlightError(target.projectId, null, exclusiveOperation.operation);
    }
    const key = InFlightOperationGuard.keyFor(target);
    if (this.running.has(key)) {
      throw new OperationInFlightError(target.projectId, target.documentId, target.operation);
    }
    const projectInFlight = this.projectActivity.get(target.projectId) ?? 0;
    if (projectInFlight >= this.policy.projectLimit) {
      throw new OperationCapacityExceededError(
        "project",
        this.policy.projectLimit,
        projectInFlight,
        target.projectId,
      );
    }
    if (this.running.size >= this.policy.applicationLimit) {
      throw new OperationCapacityExceededError(
        "application",
        this.policy.applicationLimit,
        this.running.size,
        target.projectId,
      );
    }
    const token = Symbol("in-flight-operation");
    const ownedTarget = { ...target };
    this.running.set(key, { target: ownedTarget, token });
    this.projectActivity.set(target.projectId, projectInFlight + 1);
    return this.permit(() => this.releaseOperation(key, ownedTarget, token));
  }

  private releaseOperation(key: string, target: InFlightTarget, token: symbol): void {
    if (this.running.get(key)?.token !== token) return;
    this.running.delete(key);
    const remaining = (this.projectActivity.get(target.projectId) ?? 1) - 1;
    if (remaining === 0) this.projectActivity.delete(target.projectId);
    else this.projectActivity.set(target.projectId, remaining);
  }

  /**
   * Excludes every provider/export operation for a project while an
   * irreversible project-wide transition commits and performs its cleanup.
   */
  acquireProjectExclusive(projectId: string, operation: string): InFlightOperationPermit {
    const exclusiveOperation = this.projectExclusive.get(projectId);
    if (exclusiveOperation !== undefined) {
      throw new OperationInFlightError(projectId, null, exclusiveOperation.operation);
    }
    if ((this.projectActivity.get(projectId) ?? 0) > 0) {
      const blocker = [...this.running.values()].find(
        ({ target }) => target.projectId === projectId,
      )?.target;
      if (blocker !== undefined) {
        throw new OperationInFlightError(blocker.projectId, blocker.documentId, blocker.operation);
      }
    }
    const token = Symbol("project-exclusive-operation");
    this.projectExclusive.set(projectId, { operation, token });
    return this.permit(() => this.releaseProjectExclusive(projectId, token));
  }

  private releaseProjectExclusive(projectId: string, token: symbol): void {
    if (this.projectExclusive.get(projectId)?.token !== token) return;
    this.projectExclusive.delete(projectId);
  }

  private permit(releaseOwned: () => void): InFlightOperationPermit {
    let released = false;
    return {
      release: () => {
        if (released) return;
        released = true;
        releaseOwned();
      },
    };
  }
}
