import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { HttpError, api } from '@/app/api';
import type { Project, Review, Session, StudioExport } from '@/app/types/studio';

const DEFAULT_LOAD_ERROR = 'Unable to load the project. Please retry.';

/**
 * #390 request lifecycle: the project aggregate loads under an abortable
 * signal owned by the loading effect. A stale load (project switched or the
 * page unmounted) is discarded instead of overwriting the current state, and
 * the loader never swallows a real failure — only a missing project (404)
 * redirects back to the project list; every other error surfaces as a
 * readable load error state.
 */
export function useStudioProject(projectId: string) {
  const navigate = useNavigate();
  const [session, setSession] = useState<Session | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [exports, setExports] = useState<StudioExport[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadProject = useCallback(
    async (signal: AbortSignal) => {
      try {
        const [nextSession, nextProject, reviewResponse, exportResponse] = await Promise.all([
          api.session({ signal }),
          api.project(projectId, { signal }),
          api.reviews(projectId, { signal }),
          api.exports(projectId, { signal }),
        ]);
        setLoadError(null);
        setSession(nextSession);
        setProject(nextProject);
        setReviews(reviewResponse.reviews);
        setExports(exportResponse.exports);
      } catch (reason) {
        // Stale load (project switched or unmounted): discard, never publish.
        if (signal.aborted) return;
        if (reason instanceof HttpError && reason.status === 404) {
          navigate('/', { replace: true });
          return;
        }
        setLoadError(reason instanceof Error ? reason.message : DEFAULT_LOAD_ERROR);
      }
    },
    [navigate, projectId],
  );

  useEffect(() => {
    const controller = new AbortController();
    void loadProject(controller.signal);
    return () => controller.abort();
  }, [loadProject]);

  return {
    project,
    setProject,
    session,
    reviews,
    setReviews,
    exports,
    setExports,
    error,
    setError,
    loadError,
  };
}
