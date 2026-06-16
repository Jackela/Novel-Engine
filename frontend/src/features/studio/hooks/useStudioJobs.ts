import { useCallback, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';

import { api } from '@/app/api';
import type { StudioJob } from '@/app/types/studio';

export function useStudioJobs(
  projectId: string,
  setError: Dispatch<SetStateAction<string | null>>,
) {
  const [jobs, setJobs] = useState<StudioJob[]>([]);

  const loadJobs = useCallback(async () => {
    try {
      const response = await api.jobs(projectId);
      setJobs(response.jobs);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to load jobs.');
    }
  }, [projectId, setError]);

  return { jobs, loadJobs };
}
