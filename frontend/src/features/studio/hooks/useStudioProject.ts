import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { api } from '@/app/api';
import type { Project, Review, Session, StudioExport } from '@/app/types/studio';

export function useStudioProject(projectId: string) {
  const navigate = useNavigate();
  const [session, setSession] = useState<Session | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [exports, setExports] = useState<StudioExport[]>([]);
  const [error, setError] = useState<string | null>(null);

  const loadProject = useCallback(async () => {
    try {
      const [nextSession, nextProject, reviewResponse, exportResponse] = await Promise.all([
        api.session(),
        api.project(projectId),
        api.reviews(projectId),
        api.exports(projectId),
      ]);
      setSession(nextSession);
      setProject(nextProject);
      setReviews(reviewResponse.reviews);
      setExports(exportResponse.exports);
    } catch {
      navigate('/', { replace: true });
    }
  }, [navigate, projectId]);

  useEffect(() => {
    void loadProject();
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
  };
}
