import { useCallback, useLayoutEffect, useRef, useState } from "react";

/**
 * #318 whole-book loop state machine: idle → running(current,total) →
 * done(generated, stoppedEarly) | failed(generated, chapter, message).
 * Terminal phases carry how many chapters this run accepted so the control
 * can report preserved work after a stop or failure.
 */
export type WholeBookPhase =
  | { readonly kind: "idle" }
  | {
      readonly kind: "running";
      readonly current: number;
      readonly total: number;
    }
  | {
      readonly kind: "done";
      readonly generated: number;
      readonly stoppedEarly: boolean;
    }
  | {
      readonly kind: "failed";
      readonly generated: number;
      readonly failedChapterTitle: string;
      readonly message: string;
    }
  | {
      readonly kind: "outcome_unknown";
      readonly generated: number;
      readonly interruptedChapterTitle: string;
    };

/** One registered whole-book run: identity, stop flag, and its two cancellable transports. */
interface WholeBookRun {
  readonly projectId: string;
  readonly epoch: number;
  readonly auditEpoch: number;
  stopped: boolean;
  proposalController: AbortController | null;
  refreshController: AbortController | null;
}

interface ProjectPhase {
  readonly projectId: string;
  readonly epoch: number;
  readonly value: WholeBookPhase;
}

export interface WholeBookRunLedger {
  /** The phase published by the current owner's current run, or idle. */
  readonly phase: WholeBookPhase;
  /** True only while `run` is still the ledger's registered current run. */
  readonly isCurrentRun: (run: WholeBookRun) => boolean;
  /** Publishes `nextPhase` for `run` unless the run has been superseded. */
  readonly publishPhase: (run: WholeBookRun, nextPhase: WholeBookPhase) => void;
  /** Registers a fresh run as current; every earlier run becomes stale. */
  readonly beginRun: (auditEpoch: number) => WholeBookRun;
  /** Detaches `run` when it is still the registered active run. */
  readonly detachRun: (run: WholeBookRun) => void;
  readonly getActiveRun: () => WholeBookRun | null;
  readonly isOwnerProject: () => boolean;
  /** Ends client observation of the current run and aborts its proposal transport. */
  readonly stop: () => void;
}

interface UseWholeBookRunLedgerArgs {
  readonly projectId: string;
}

/**
 * Run ledger for the whole-book loop: owns run identity (owner project, run
 * epoch, active run), the published phase state machine, and stop. The
 * owner-reconciliation effect (#390) invalidates publications before aborting
 * both cancellable transports of the superseded lifecycle.
 */
export function useWholeBookRunLedger({
  projectId,
}: UseWholeBookRunLedgerArgs): WholeBookRunLedger {
  const [projectPhase, setProjectPhase] = useState<ProjectPhase>({
    projectId,
    epoch: 0,
    value: { kind: "idle" },
  });
  const ownerProjectRef = useRef<string | null>(projectId);
  const runEpochRef = useRef(0);
  const activeRunRef = useRef<WholeBookRun | null>(null);
  const phase: WholeBookPhase =
    ownerProjectRef.current === projectId &&
    projectPhase.projectId === projectId &&
    projectPhase.epoch === runEpochRef.current
      ? projectPhase.value
      : { kind: "idle" };

  const isCurrentRun = useCallback(
    (run: WholeBookRun) =>
      activeRunRef.current === run &&
      ownerProjectRef.current === run.projectId &&
      runEpochRef.current === run.epoch,
    [],
  );

  const publishPhase = useCallback(
    (run: WholeBookRun, nextPhase: WholeBookPhase) => {
      if (!isCurrentRun(run)) return;
      setProjectPhase({ projectId: run.projectId, epoch: run.epoch, value: nextPhase });
    },
    [isCurrentRun],
  );

  const stop = useCallback(() => {
    const run = activeRunRef.current;
    if (!run || !isCurrentRun(run)) return;
    run.stopped = true;
    run.proposalController?.abort();
  }, [isCurrentRun]);

  const beginRun = useCallback(
    (auditEpoch: number): WholeBookRun => {
      const epoch = runEpochRef.current + 1;
      runEpochRef.current = epoch;
      const run: WholeBookRun = {
        projectId,
        epoch,
        auditEpoch,
        stopped: false,
        proposalController: null,
        refreshController: null,
      };
      activeRunRef.current = run;
      return run;
    },
    [projectId],
  );

  const detachRun = useCallback((run: WholeBookRun) => {
    if (activeRunRef.current === run) activeRunRef.current = null;
  }, []);

  const getActiveRun = useCallback(() => activeRunRef.current, []);

  const isOwnerProject = useCallback(() => ownerProjectRef.current === projectId, [projectId]);

  // #390: a project identity owns exactly one loop lifecycle. Its cleanup
  // invalidates publications before aborting both cancellable transports.
  useLayoutEffect(() => {
    ownerProjectRef.current = projectId;

    return () => {
      runEpochRef.current += 1;
      const run = activeRunRef.current;
      if (run?.projectId === projectId) {
        run.stopped = true;
        run.proposalController?.abort();
        run.refreshController?.abort();
        if (activeRunRef.current === run) activeRunRef.current = null;
      }
      if (ownerProjectRef.current === projectId) ownerProjectRef.current = null;
    };
  }, [projectId]);

  return {
    phase,
    isCurrentRun,
    publishPhase,
    beginRun,
    detachRun,
    getActiveRun,
    isOwnerProject,
    stop,
  };
}
