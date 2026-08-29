import { useCallback, useEffect, useRef, useState } from 'react';

import { api } from '@/app/api';
import type { ProjectUsage } from '@/app/types/studio';

/**
 * Loads the project-level cumulative usage (#377) lazily: the request fires
 * the first time the Usage inspector tab becomes active, and can be repeated
 * through the panel's refresh command.
 */
export function useProjectUsage(projectId: string, active: boolean) {
  const [usage, setUsage] = useState<ProjectUsage | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const loadingRef = useRef(false);
  const loadedRef = useRef(false);

  const loadUsage = useCallback(async () => {
    if (loadingRef.current) return;
    loadingRef.current = true;
    setIsLoading(true);
    try {
      const response = await api.usage(projectId);
      setUsage(response);
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to load usage.');
    } finally {
      loadingRef.current = false;
      loadedRef.current = true;
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (active && !loadedRef.current) {
      void loadUsage();
    }
  }, [active, loadUsage]);

  return { usage, isLoading, error, reload: loadUsage };
}
