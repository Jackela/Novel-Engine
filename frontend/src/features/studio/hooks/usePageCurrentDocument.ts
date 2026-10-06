import { useCallback, useEffect, useRef } from "react";
import type { NavigateFunction } from "react-router-dom";

import { useSessionExpiredRedirect } from "@/app/sessionExpiry";
import type { DocumentSummary } from "@/app/types/studio";

import type { ProjectShellReadAuthority } from "./projectShellReadAuthority";
import { useCurrentDocument } from "./useCurrentDocument";

/**
 * Page adapter for `useCurrentDocument`: keeps session/project-loss
 * navigation identity-stable so document reads never re-trigger on pathname
 * changes (#465).
 */
export function usePageCurrentDocument(
  projectId: string,
  summary: DocumentSummary | null,
  lifecycle: symbol,
  shellReadAuthority: ProjectShellReadAuthority,
  navigate: NavigateFunction,
) {
  // react-router re-creates `navigate` on every pathname change; these loss
  // callbacks feed `useCurrentDocument`'s effect deps, so they read the latest
  // `navigate` through a ref and stay identity-stable (#465). The ref updates
  // in an effect, never during render.
  const navigateRef = useRef(navigate);
  useEffect(() => {
    navigateRef.current = navigate;
  }, [navigate]);
  // DR-020: the rejected document read returns to the entry page carrying the
  // route of the document being read, and the reader comes back to it.
  const onSessionLoss = useSessionExpiredRedirect();
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
