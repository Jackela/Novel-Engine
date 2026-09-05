import { useCallback } from "react";

import { api } from "@/app/api";
import type { StudioExport } from "@/app/types/studio";
import type { InspectorTab } from "../studioConstants";

import { useLazyInspectorResource } from "./useLazyInspectorResource";
import { type ReviewHistoryState, useReviewHistory } from "./useReviewHistory";

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
}: UseLazyInspectorHistoriesOptions): {
  review: ReviewHistoryState;
  export: ReturnType<typeof useLazyInspectorResource<StudioExport[]>>;
} {
  const review = useReviewHistory({
    enabled,
    inspector,
    projectId,
    recheckProject,
    onSessionLost,
  });
  const requestExports = useCallback(
    async (signal: AbortSignal) => (await api.exports(projectId, { signal })).exports,
    [projectId],
  );
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
