import { useCallback } from "react";

import { api } from "@/app/api";
import type { Review, StudioExport } from "@/app/types/studio";
import type { InspectorTab } from "../studioConstants";

import { useLazyInspectorResource } from "./useLazyInspectorResource";

const EMPTY_REVIEWS: Review[] = [];
const EMPTY_EXPORTS: StudioExport[] = [];

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
  const requestExports = useCallback(
    async (signal: AbortSignal) => (await api.exports(projectId, { signal })).exports,
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
  const exportHistory = useLazyInspectorResource({
    active: enabled && inspector === "export",
    projectId,
    empty: EMPTY_EXPORTS,
    request: requestExports,
    recheckProject,
    onSessionLost,
    missingResourceMessage: "Export history is unavailable for this project.",
    loadErrorMessage: "Unable to load export history.",
  });

  return { review, export: exportHistory };
}
