import type { InspectorTab } from "../studioConstants";

import { type ExportHistoryState, useExportHistory } from "./useExportHistory";
import { type ReviewHistoryState, useReviewHistory } from "./useReviewHistory";

interface UseLazyInspectorHistoriesOptions {
  readonly enabled: boolean;
  readonly inspector: InspectorTab;
  readonly projectId: string;
  readonly recheckProject: (signal: AbortSignal) => Promise<boolean>;
  readonly onSessionLost: () => void;
}

/**
 * Own every URL-selected Inspector history family. Activation for each member
 * derives only here, from one gate: the project shell exists and the route
 * selects that member's tab, so no family bypasses the shell or re-derives it.
 */
export function useLazyInspectorHistories({
  enabled,
  inspector,
  projectId,
  recheckProject,
  onSessionLost,
}: UseLazyInspectorHistoriesOptions): {
  review: ReviewHistoryState;
  exportHistory: ExportHistoryState;
} {
  const review = useReviewHistory({
    active: enabled && inspector === "review",
    projectId,
    recheckProject,
    onSessionLost,
  });

  const exportHistory = useExportHistory({
    active: enabled && inspector === "export",
    projectId,
    recheckProject,
    onSessionLost,
  });

  return { review, exportHistory };
}
