import type { Dispatch, SetStateAction } from "react";
import { useCallback, useLayoutEffect, useRef } from "react";

import { ProposalOutcomeUnknownError, streamProposal } from "@/app/proposalStream";
import type { Project, StudioDocument } from "@/app/types/studio";

import { AcceptedProposalRefreshError, acceptProposalAndRefresh } from "./acceptProposalAndRefresh";
import { toErrorMessage } from "./toErrorMessage";
import type { ProposalAuditControl } from "./useStudioJobs";
import type { WholeBookRunLedger } from "./useWholeBookRunLedger";
import type { WholeBookChapter } from "./wholeBookPlan";

interface CommittedChapters {
  readonly projectId: string;
  readonly documentIds: Set<string>;
}

interface UseWholeBookChapterRunArgs {
  readonly projectId: string;
  readonly provider: string;
  readonly setProject: Dispatch<SetStateAction<Project | null>>;
  readonly loadJobs: () => void;
  readonly proposalAudit: ProposalAuditControl;
  /** Captures the draft version an acceptance may replace before its request starts. */
  readonly captureAcceptedDocument?: (
    documentId: string,
  ) => ((document: StudioDocument) => void) | undefined;
  readonly ledger: WholeBookRunLedger;
}

/**
 * Executor of the frontend-driven whole-book generation loop (#318): over the
 * existing streaming endpoint it drafts a `generate` proposal per planned
 * chapter, auto-accepts it, and refreshes project/jobs state exactly like the
 * manual copilot accept flow. Stop ends client observation and prevents
 * automatic acceptance or continuation; an unobserved terminal outcome enters
 * the shared jobs-audit gate. An acceptance that already started remains
 * atomic and is counted if it completes. Resume recomputes the persisted plan
 * from the first chapter whose current revision is not `ai-accepted`.
 */
export function useWholeBookChapterRun({
  projectId,
  provider,
  setProject,
  loadJobs,
  proposalAudit,
  captureAcceptedDocument,
  ledger,
}: UseWholeBookChapterRunArgs) {
  const committedChaptersRef = useRef<CommittedChapters>({
    projectId,
    documentIds: new Set<string>(),
  });
  const { beginRun, detachRun, getActiveRun, isCurrentRun, isOwnerProject, publishPhase } = ledger;

  // The committed set is scoped to one project identity and resets with it.
  useLayoutEffect(() => {
    committedChaptersRef.current = { projectId, documentIds: new Set<string>() };
  }, [projectId]);

  const start = useCallback(
    (plan: WholeBookChapter[]): Promise<void> => {
      const committedChapters = committedChaptersRef.current;
      if (!isOwnerProject() || committedChapters.projectId !== projectId) {
        return Promise.resolve();
      }
      if (proposalAudit.isGated()) return Promise.resolve();
      const activeRun = getActiveRun();
      if (activeRun && isCurrentRun(activeRun)) return Promise.resolve();
      const auditEpoch = proposalAudit.epoch();
      proposalAudit.clear();
      const currentRun = beginRun(auditEpoch);
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
            detachRun(currentRun);
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
          detachRun(currentRun);
        }
      };

      return run();
    },
    [
      beginRun,
      captureAcceptedDocument,
      detachRun,
      getActiveRun,
      isCurrentRun,
      isOwnerProject,
      loadJobs,
      projectId,
      provider,
      proposalAudit,
      publishPhase,
      setProject,
    ],
  );

  return { start };
}
