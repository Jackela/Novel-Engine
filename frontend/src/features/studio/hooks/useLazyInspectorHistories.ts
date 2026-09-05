import type { InspectorTab } from "../studioConstants";

import { type ReviewHistoryState, useReviewHistory } from "./useReviewHistory";

interface UseLazyInspectorHistoriesOptions {
  readonly enabled: boolean;
  readonly inspector: InspectorTab;
  readonly projectId: string;
  readonly recheckProject: (signal: AbortSignal) => Promise<boolean>;
  readonly onSessionLost: () => void;
}

export function useLazyInspectorHistories({
  enabled,
  inspector,
  projectId,
  recheckProject,
  onSessionLost,
}: UseLazyInspectorHistoriesOptions): {
  review: ReviewHistoryState;
} {
  const review = useReviewHistory({
    enabled,
    inspector,
    projectId,
    recheckProject,
    onSessionLost,
  });

  return { review };
}
