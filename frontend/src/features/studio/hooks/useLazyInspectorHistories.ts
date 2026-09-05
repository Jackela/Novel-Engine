import { useCallback } from "react";

import { api } from "@/app/api";
import type { Review } from "@/app/types/studio";
import type { InspectorTab } from "../studioConstants";

import { useLazyInspectorResource } from "./useLazyInspectorResource";

const EMPTY_REVIEWS: Review[] = [];

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
}: UseLazyInspectorHistoriesOptions) {
  const requestReviews = useCallback(
    async (signal: AbortSignal) => (await api.reviews(projectId, { signal })).reviews,
    [projectId],
  );
  const review = useLazyInspectorResource({
    active: enabled && inspector === "review",
    projectId,
    empty: EMPTY_REVIEWS,
    request: requestReviews,
    recheckProject,
    onSessionLost,
    missingResourceMessage: "Review history is unavailable for this project.",
    loadErrorMessage: "Unable to load review history.",
  });

  return { review };
}
