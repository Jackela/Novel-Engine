import { useCallback } from "react";
import type { NavigateFunction } from "react-router-dom";

import type { DocumentSummary } from "@/app/types/studio";

import type { ProjectShellReadAuthority } from "./projectShellReadAuthority";
import { useCurrentDocument } from "./useCurrentDocument";

export function usePageCurrentDocument(
  projectId: string,
  summary: DocumentSummary | null,
  lifecycle: symbol,
  shellReadAuthority: ProjectShellReadAuthority,
  navigate: NavigateFunction,
) {
  const onSessionLoss = useCallback(() => navigate("/", { replace: true }), [navigate]);
  const onProjectMissing = useCallback(() => navigate("/projects", { replace: true }), [navigate]);
  return useCurrentDocument(projectId, {
    summary,
    lifecycle,
    ...shellReadAuthority,
    onSessionLoss,
    onProjectMissing,
  });
}
