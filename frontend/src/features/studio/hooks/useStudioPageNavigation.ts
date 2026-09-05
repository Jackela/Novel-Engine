import { useCallback } from "react";
import type { NavigateFunction } from "react-router-dom";

import type { Project } from "@/app/types/studio";
import { type StudioRouteState, studioInspectorPath } from "../studioRouteState";
import { buildProposalAuditView } from "./proposalAuditView";
import type { useStudioGeneration } from "./useStudioGeneration";
import { wholeBookPlan } from "./wholeBookPlan";

interface NavigationOptions {
  readonly navigate: NavigateFunction;
  readonly projectId: string;
  readonly section: string;
  readonly routeInspector: StudioRouteState["inspector"];
}

export function useStudioPageNavigation({
  navigate,
  projectId,
  section,
  routeInspector,
}: NavigationOptions) {
  const onProjectResourceSessionLost = useCallback(
    () => navigate("/", { replace: true }),
    [navigate],
  );
  const onSettingsProjectMissing = useCallback(
    () => navigate("/projects", { replace: true }),
    [navigate],
  );
  const onSelectInspector = useCallback(
    (nextInspector: Parameters<typeof studioInspectorPath>[2]) => {
      if (nextInspector === routeInspector) return;
      navigate(studioInspectorPath(projectId, section, nextInspector));
    },
    [navigate, projectId, routeInspector, section],
  );
  return { onProjectResourceSessionLost, onSettingsProjectMissing, onSelectInspector };
}

interface InspectorPendingOptions {
  readonly copilot: {
    readonly isRunningProposal: boolean;
    readonly isAcceptingProposal: boolean;
  };
  readonly isRunningReview: boolean;
  readonly jobs: {
    readonly isLoading: boolean;
    readonly loadingInitiator: ReturnType<typeof useStudioGeneration>["loadingInitiator"];
    readonly isRetrying: boolean;
    readonly retryGated: boolean;
    readonly retryingJobId: string | null;
  };
  readonly isUpdatingSettings: boolean;
  readonly restoringRevisionId: string | null;
}

export function buildInspectorPending(options: InspectorPendingOptions) {
  return {
    proposal: {
      running: options.copilot.isRunningProposal,
      accepting: options.copilot.isAcceptingProposal,
    },
    review: options.isRunningReview,
    jobs: {
      loading: options.jobs.isLoading,
      loadingInitiator: options.jobs.loadingInitiator,
      retrying: options.jobs.isRetrying,
      retryGated: options.jobs.retryGated,
      retryingJobId: options.jobs.retryingJobId,
    },
    settings: options.isUpdatingSettings,
    history: { restoringRevisionId: options.restoringRevisionId },
  };
}

export function buildWholeBookNavigatorModel(
  project: Project,
  loop: ReturnType<typeof useStudioGeneration>["wholeBookLoop"],
) {
  return {
    phase: loop.phase,
    remaining: wholeBookPlan(project).length,
    onStart: () => loop.start(wholeBookPlan(project)),
    onStop: () => loop.stop(),
    ...buildProposalAuditView(
      loop.proposalOutcomeUnknown,
      loop.proposalAuditStatus,
      loop.retryProposalAudit,
    ),
  };
}
