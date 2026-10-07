import { useCallback } from "react";

import { api } from "@/app/api";
import { translateActive } from "@/app/i18n/translate";
import type { ProjectUsage } from "@/app/types/studio";

import { useScopedProjectResource } from "./useScopedProjectResource";

/**
 * Loads the project-level cumulative usage (#377) lazily: the request fires
 * the first time the Usage inspector tab becomes active, and can be repeated
 * through the panel's refresh command. Scope, abort, epoch and projection
 * semantics belong to `useScopedProjectResource`; the failure message is the
 * usage dictionary entry the shared error reduction falls back to.
 */
export function useProjectUsage(projectId: string, active: boolean) {
  const loadUsage = useCallback(
    (signal: AbortSignal) => api.usage(projectId, { signal }),
    [projectId],
  );
  const { data, isLoading, error, reload } = useScopedProjectResource<ProjectUsage>({
    active,
    projectId,
    load: loadUsage,
    loadErrorMessage: translateActive("errors.loadUsage"),
  });

  return { usage: data, isLoading, error, reload };
}
