import { useQuery } from 'react-query';
import api from './api';

export const queryKeys = {
  characters: ['characters', 'list'] as const,
  characterDetails: (name: string) => ['characters', 'detail', name] as const,
  generationStatus: (id: string) => ['stories', 'generation', id] as const,
  health: ['system', 'health'] as const,
  systemStatus: ['system', 'status'] as const,
  campaigns: ['campaigns', 'list'] as const,
};

const shouldDisableQueryRetry = import.meta.env.VITE_DISABLE_QUERY_RETRY === 'true';

export function useCharactersQuery() {
  return useQuery(queryKeys.characters, () => api.getCharacters(), {
    staleTime: 60_000,
    ...(shouldDisableQueryRetry ? { retry: false } : {}),
  });
}

export function useCharacterDetailsQuery(name: string) {
  return useQuery(queryKeys.characterDetails(name), () => api.getCharacterDetails(name), {
    enabled: !!name,
    staleTime: 60_000,
  });
}

export function useGenerationStatusQuery(id: string) {
  return useQuery(queryKeys.generationStatus(id), () => api.getGenerationStatus(id), {
    enabled: !!id,
    refetchInterval: 2000,
  });
}

export function useHealthQuery() {
  return useQuery(queryKeys.health, () => api.getHealth(), { staleTime: 30_000 });
}

export function useSystemStatusQuery() {
  return useQuery(queryKeys.systemStatus, () => api.getSystemStatus(), { staleTime: 30_000 });
}

export function useCampaignsQuery() {
  return useQuery(queryKeys.campaigns, () => api.getCampaigns(), { staleTime: 60_000 });
}
