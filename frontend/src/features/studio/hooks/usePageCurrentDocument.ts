import type { Dispatch, SetStateAction } from "react";
import { useCallback } from "react";
import type { NavigateFunction } from "react-router-dom";

import type { DocumentSummary, ProjectShell } from "@/app/types/studio";

import { useCurrentDocument } from "./useCurrentDocument";

export function usePageCurrentDocument(
  projectId: string,
  summary: DocumentSummary | null,
  lifecycle: symbol,
  setProject: Dispatch<SetStateAction<ProjectShell | null>>,
  navigate: NavigateFunction,
) {
  const onSessionLoss = useCallback(() => navigate("/", { replace: true }), [navigate]);
  const onProjectMissing = useCallback(() => navigate("/projects", { replace: true }), [navigate]);
  return useCurrentDocument(projectId, {
    summary,
    lifecycle,
    setProject,
    onSessionLoss,
    onProjectMissing,
  });
}
