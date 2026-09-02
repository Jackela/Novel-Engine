import type { Dispatch, SetStateAction } from "react";
import { useCallback, useLayoutEffect, useRef, useState } from "react";

import { ProposalOutcomeUnknownError, streamProposal } from "@/app/proposalStream";
import type { Project, StudioDocument } from "@/app/types/studio";

import { AcceptedProposalRefreshError, acceptProposalAndRefresh } from "./acceptProposalAndRefresh";
import { toErrorMessage } from "./toErrorMessage";
import type { ProposalAuditControl } from "./useStudioJobs";
import type { WholeBookChapter } from "./wholeBookPlan";

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

interface UseWholeBookLoopArgs {
  readonly projectId: string;
  readonly provider: string;
  readonly setProject: Dispatch<SetStateAction<Project | null>>;
  readonly loadJobs: () => void;
  readonly proposalAudit?: ProposalAuditControl;
  /** Captures the draft version an acceptance may replace before its request starts. */
  readonly captureAcceptedDocument?: (
    documentId: string,
  ) => ((document: StudioDocument) => void) | undefined;
}

const INACTIVE_PROPOSAL_AUDIT: ProposalAuditControl = {
  status: "idle",
  audit: async () => false,
  clear: () => undefined,
  epoch: () => 0,
  isGated: () => false,
};

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

interface CommittedChapters {
  readonly projectId: string;
  readonly documentIds: Set<string>;
}

/**
 * The frontend-driven whole-book generation loop (#318): over the existing
 * streaming endpoint it drafts a `generate` proposal per planned chapter,
 * auto-accepts it, and refreshes project/jobs state exactly like the manual
 * copilot accept flow. Stop ends client observation and prevents automatic
 * acceptance or continuation; an unobserved terminal outcome enters the shared
 * jobs-audit gate. An acceptance that already started remains atomic and is
 * counted if it completes. Resume recomputes the persisted plan from the first
 * chapter whose current revision is not `ai-accepted`.
 */
export function useWholeBookLoop({
  projectId,
  provider,
  setProject,
  loadJobs,
  proposalAudit = INACTIVE_PROPOSAL_AUDIT,
  captureAcceptedDocument,
}: UseWholeBookLoopArgs) {
  const [projectPhase, setProjectPhase] = useState<ProjectPhase>({
    projectId,
    epoch: 0,
    value: { kind: "idle" },
  });
  const ownerProjectRef = useRef<string | null>(projectId);
  const runEpochRef = useRef(0);
  const activeRunRef = useRef<WholeBookRun | null>(null);
  const committedChaptersRef = useRef<CommittedChapters>({
    projectId,
    documentIds: new Set<string>(),
  });
  const phase: WholeBookPhase =
    ownerProjectRef.current === projectId &&
    projectPhase.projectId === projectId &&
    projectPhase.epoch === runEpochRef.current
      ? projectPhase.value
      : { kind: "idle" };
  const proposalOutcomeUnknown = proposalAudit.status !== "idle";
  const proposalActionsGated = proposalAudit.isGated();

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

  // #390: a project identity owns exactly one loop lifecycle. Its cleanup
  // invalidates publications before aborting both cancellable transports.
  useLayoutEffect(() => {
    ownerProjectRef.current = projectId;
    committedChaptersRef.current = { projectId, documentIds: new Set<string>() };

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

  const start = useCallback(
    (plan: WholeBookChapter[]): Promise<void> => {
      const committedChapters = committedChaptersRef.current;
      if (ownerProjectRef.current !== projectId || committedChapters.projectId !== projectId) {
        return Promise.resolve();
      }
      if (proposalAudit.isGated()) return Promise.resolve();
      const activeRun = activeRunRef.current;
      if (activeRun && isCurrentRun(activeRun)) return Promise.resolve();
      const auditEpoch = proposalAudit.epoch();
      proposalAudit.clear();
      const epoch = runEpochRef.current + 1;
      runEpochRef.current = epoch;
      const currentRun: WholeBookRun = {
        projectId,
        epoch,
        auditEpoch,
        stopped: false,
        proposalController: null,
        refreshController: null,
      };
      activeRunRef.current = currentRun;
      const remainingPlan = plan.filter(
        (chapter) => !committedChapters.documentIds.has(chapter.id),
      );
      publishPhase(currentRun, { kind: "running", current: 1, total: remainingPlan.length });

      const run = async (): Promise<void> => {
        let generated = 0;
        let failingTitle = remainingPlan[0]?.title ?? "";
        try {
          for (let index = 0; index < remainingPlan.length; index += 1) {
            if (
              !isCurrentRun(currentRun) ||
              currentRun.stopped ||
              proposalAudit.epoch() !== currentRun.auditEpoch
            ) {
              if (proposalAudit.epoch() !== currentRun.auditEpoch) currentRun.stopped = true;
              break;
            }
            const chapter = remainingPlan[index];
            failingTitle = chapter.title;
            publishPhase(currentRun, {
              kind: "running",
              current: index + 1,
              total: remainingPlan.length,
            });
            // The accepted result may replace only the draft version present
            // before this chapter starts generating. Later author edits win.
            const onAccepted = captureAcceptedDocument?.(chapter.id);
            // Each proposal depends on the preceding acceptance, so parallel
            // requests would violate reading order and resident context.
            const proposalController = new AbortController();
            currentRun.proposalController = proposalController;
            // react-doctor-disable-next-line async-await-in-loop
            const job = await streamProposal({
              projectId,
              documentId: chapter.id,
              operation: "generate",
              instruction: "",
              provider,
              signal: proposalController.signal,
              onDelta: () => undefined,
            });
            if (currentRun.proposalController === proposalController) {
              currentRun.proposalController = null;
            }
            if (
              !isCurrentRun(currentRun) ||
              currentRun.stopped ||
              proposalAudit.epoch() !== currentRun.auditEpoch
            ) {
              if (proposalAudit.epoch() !== currentRun.auditEpoch) currentRun.stopped = true;
              break;
            }
            const refreshController = new AbortController();
            currentRun.refreshController = refreshController;
            // Acceptance must finish before the next chapter can be drafted.
            // react-doctor-disable-next-line async-await-in-loop
            await acceptProposalAndRefresh({
              projectId,
              proposalId: job.id,
              documentId: chapter.id,
              setProject,
              onAccepted,
              loadJobs,
              signal: refreshController.signal,
              isProjectCurrent: () => isCurrentRun(currentRun) && !refreshController.signal.aborted,
              onAcceptanceCommitted: () => {
                committedChapters.documentIds.add(chapter.id);
                generated += 1;
              },
            });
            if (currentRun.refreshController === refreshController) {
              currentRun.refreshController = null;
            }
            if (!isCurrentRun(currentRun)) return;
            if (proposalAudit.epoch() !== currentRun.auditEpoch) currentRun.stopped = true;
          }
          if (!isCurrentRun(currentRun)) return;
          publishPhase(currentRun, {
            kind: "done",
            generated,
            stoppedEarly: currentRun.stopped,
          });
        } catch (reason) {
          if (!isCurrentRun(currentRun)) return;
          if (reason instanceof ProposalOutcomeUnknownError) {
            currentRun.proposalController = null;
            publishPhase(currentRun, {
              kind: "outcome_unknown",
              generated,
              interruptedChapterTitle: failingTitle,
            });
            if (activeRunRef.current === currentRun) activeRunRef.current = null;
            await proposalAudit.audit();
            return;
          }
          // A stopped proposal/accept request is expected noise. Once acceptance
          // committed, however, a failed aggregate refresh must remain visible
          // because the local workbench needs an explicit reload to synchronize.
          if (currentRun.stopped && !(reason instanceof AcceptedProposalRefreshError)) {
            publishPhase(currentRun, { kind: "done", generated, stoppedEarly: true });
          } else {
            publishPhase(currentRun, {
              kind: "failed",
              generated,
              failedChapterTitle: failingTitle,
              message: toErrorMessage(reason, "Unable to generate the chapter."),
            });
          }
        } finally {
          currentRun.proposalController = null;
          currentRun.refreshController = null;
          if (activeRunRef.current === currentRun) activeRunRef.current = null;
        }
      };

      return run();
    },
    [
      captureAcceptedDocument,
      isCurrentRun,
      loadJobs,
      projectId,
      provider,
      proposalAudit,
      publishPhase,
      setProject,
    ],
  );

  const retryProposalAudit = useCallback(async (): Promise<boolean> => {
    if (proposalAudit.status !== "audit_failed") return false;
    return proposalAudit.audit();
  }, [proposalAudit]);

  return {
    phase,
    start,
    stop,
    proposalOutcomeUnknown,
    proposalAuditStatus: proposalAudit.status,
    proposalActionsGated,
    retryProposalAudit,
  };
}
