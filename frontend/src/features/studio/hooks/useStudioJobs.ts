import { useCallback, useRef, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';

import { api } from '@/app/api';
import type { StudioJob } from '@/app/types/studio';

export function useStudioJobs(
  projectId: string,
  setError: Dispatch<SetStateAction<string | null>>,
) {
  const [jobs, setJobs] = useState<StudioJob[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const loadingRef = useRef(false);

  const loadJobs = useCallback(async () => {
    if (loadingRef.current) return;
    loadingRef.current = true;
    setIsLoading(true);
    try {
      const response = await api.jobs(projectId);
      setJobs(response.jobs);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to load jobs.');
    } finally {
      loadingRef.current = false;
      setIsLoading(false);
    }
  }, [projectId, setError]);

  return { jobs, loadJobs, isLoading };
}
