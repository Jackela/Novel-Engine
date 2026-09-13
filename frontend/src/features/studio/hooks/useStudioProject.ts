import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useProjectShellLoad } from "./useProjectShellLoad";
import { useProjectShellState } from "./useProjectShellState";

/**
 * Compose the route-scoped project model behind one contract: the bounded
 * shell state with its read authority (`useProjectShellState`) and the
 * bootstrap/retry load lifecycle that feeds it (`useProjectShellLoad`). Both
 * hold `navigate` behind refs updated in effects, because react-router
 * re-creates it on every pathname change and identity-stable callbacks must
 * never replay reads on same-project navigations (#465).
 */
export function useStudioProject(projectId: string) {
  const navigate = useNavigate();
  const [lifecycle] = useState(() => Symbol("studio lifecycle"));

  const shell = useProjectShellState(projectId, navigate);
  const { loadError, isLoading, retryLoad } = useProjectShellLoad(projectId, {
    navigate,
    isActiveProject: shell.isActiveProject,
    setError: shell.setError,
    beginShellLoad: shell.beginShellLoad,
    commitLoadedShell: shell.commitLoadedShell,
  });

  return {
    project: shell.project,
    setProject: shell.setProject,
    captureProjectShellRead: shell.captureProjectShellRead,
    publishProjectShellRead: shell.publishProjectShellRead,
    recheckProject: shell.recheckProject,
    error: shell.error,
    setError: shell.setError,
    loadError,
    isLoading,
    retryLoad,
    lifecycle,
  };
}
