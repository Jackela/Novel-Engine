import { useQuery, useMutation, useQueryClient } from 'react-query';
import api from '@/services/api';
import type { CharacterFormData } from '@/types';
import { logger } from '@/services/logging/LoggerFactory';
import { queryKeys } from '@/services/queries';

export function useCharacters() {
  return useQuery(queryKeys.characters, api.getCharacters, {
    staleTime: 2 * 60 * 1000, // 2 minutes
    cacheTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useCharacterDetails(name: string | null) {
  return useQuery(
    queryKeys.characterDetails(name || ''),
    () => name ? api.getCharacterDetails(name) : null,
    {
      enabled: !!name,
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 2,
    }
  );
}

export function useCreateCharacter() {
  const queryClient = useQueryClient();

  return useMutation(
    ({ data, files }: { data: CharacterFormData; files?: File[] }) =>
      api.createCharacter(data, files),
    {
      onSuccess: () => {
        // Invalidate and refetch character list
        queryClient.invalidateQueries(queryKeys.characters);
      },
      onError: (error) => {
        logger.error('Character creation failed', error as Error, { component: 'useCreateCharacter' });
      },
    }
  );
}
