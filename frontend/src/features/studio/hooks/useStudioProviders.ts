import { useEffect, useState } from 'react';

import { api } from '@/app/api';
import type { ProviderInfo } from '@/app/types/studio';

import { DEFAULT_PROVIDER_OPTIONS } from '../studioConstants';

export function useStudioProviders(): ProviderInfo[] {
  const [providers, setProviders] = useState<ProviderInfo[]>(DEFAULT_PROVIDER_OPTIONS);

  useEffect(() => {
    let cancelled = false;
    api
      .providers()
      .then((response) => {
        if (cancelled || response.providers.length === 0) return;
        setProviders(response.providers);
      })
      .catch(() => {
        // Keep fallback providers on failure so the UI remains usable.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return providers;
}
