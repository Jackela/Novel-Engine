import { useCallback, useRef } from "react";
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
  // react-router re-creates `navigate` on every pathname change; these loss
  // callbacks feed `useCurrentDocument`'s effect deps, so they read the latest
  // `navigate` through a ref and stay identity-stable (#465).
  const navigateRef = useRef(navigate);
  navigateRef.current = navigate;
  const onSessionLoss = useCallback(() => navigateRef.current("/", { replace: true }), []);
  const onProjectMissing = useCallback(
    () => navigateRef.current("/projects", { replace: true }),
    [],
  );
  return useCurrentDocument(projectId, {
    summary,
    lifecycle,
    ...shellReadAuthority,
    onSessionLoss,
    onProjectMissing,
  });
}
