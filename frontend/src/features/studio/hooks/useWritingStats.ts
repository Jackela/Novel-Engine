import { useCallback } from "react";

import { api } from "@/app/api";
import { translateActive } from "@/app/i18n/translate";
import type { WritingStats } from "@/app/types/studio";

import { useScopedProjectResource } from "./useScopedProjectResource";

/**
 * Loads the project writing-statistics summary (#653) lazily: the request
 * fires the first time the Stats inspector tab becomes active, and can be
 * repeated through the panel's refresh command — a refresh aborts the
 * in-flight request, so a duplicate submission never double-publishes. Scope,
 * abort, epoch and projection semantics belong to `useScopedProjectResource`.
 */
export function useWritingStats(projectId: string, active: boolean) {
  const loadStats = useCallback(
    (signal: AbortSignal) => api.writingStats(projectId, { signal }),
    [projectId],
  );
  const { data, isLoading, error, reload } = useScopedProjectResource<WritingStats>({
    active,
    projectId,
    load: loadStats,
    loadErrorMessage: translateActive("errors.loadStats"),
  });

  return { stats: data, isLoading, error, reload };
}
