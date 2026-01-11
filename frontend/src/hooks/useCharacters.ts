import { useQuery, useMutation, useQueryClient } from 'react-query';
import api from '@/services/api';
import type { CharacterFormData } from '@/types';
import { logger } from '@/services/logging/LoggerFactory';
import { queryKeys } from '@/services/queries';
import { ApiError } from '@/lib/api/errors';

export function useCharacters() {
  return useQuery(queryKeys.characters, () => api.getCharacters(), {
    staleTime: 2 * 60 * 1000, // 2 minutes
    cacheTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useCharacterDetails(name: string | null) {
  return useQuery(
    queryKeys.characterDetails(name || ''),
    () => name ? api.getCharacter(name) : null,
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
    ({ data }: { data: CharacterFormData; files?: File[] }) =>
      api.createCharacter(data),
    {
      onSuccess: async () => {
        // Invalidate and refetch character list
        await queryClient.invalidateQueries(queryKeys.characters);
      },
      onError: (error) => {
        logger.error('Character creation failed', error as Error, { component: 'useCreateCharacter' });

        // Extract and log validation errors for debugging
        if (error instanceof ApiError && error.kind === 'validation' && error.fields) {
          // Map backend field names to frontend field names
          const fieldMap: Record<string, string> = {
            'agent_id': 'name',
            'background_summary': 'description',
            'personality_traits': 'role',
          };

          const mappedErrors = error.fields.map(field => ({
            ...field,
            path: fieldMap[field.path] || field.path,
            originalPath: field.path,
          }));

          logger.warn('Validation errors:', { errors: mappedErrors, component: 'useCreateCharacter' });
        }
      },
    }
  );
}

export function useUpdateCharacter() {

  const queryClient = useQueryClient();



  return useMutation(

    ({ characterId, data }: { characterId: string; data: CharacterFormData; files?: File[] }) =>   

      api.updateCharacter(characterId, data),

    {

      onSuccess: (_result, variables) => {


        queryClient.invalidateQueries(queryKeys.characters);
        queryClient.invalidateQueries(queryKeys.characterDetails(variables.characterId));
        queryClient.invalidateQueries(['character-card', variables.characterId]);
      },
      onError: (error) => {
        logger.error('Character update failed', error as Error, { component: 'useUpdateCharacter' });

        // Extract and log validation errors for debugging
        if (error instanceof ApiError && error.kind === 'validation' && error.fields) {
          const fieldMap: Record<string, string> = {
            'agent_id': 'name',
            'background_summary': 'description',
            'personality_traits': 'role',
          };

          const mappedErrors = error.fields.map(field => ({
            ...field,
            path: fieldMap[field.path] || field.path,
            originalPath: field.path,
          }));

          logger.warn('Validation errors:', { errors: mappedErrors, component: 'useUpdateCharacter' });
        }
      },
    }
  );
}

export function useDeleteCharacter() {
  const queryClient = useQueryClient();

  return useMutation((characterId: string) => api.deleteCharacter(characterId), {
    onSuccess: (_result, characterId) => {
      queryClient.invalidateQueries(queryKeys.characters);
      queryClient.invalidateQueries(queryKeys.characterDetails(characterId));
      queryClient.invalidateQueries(['character-card', characterId]);
    },
    onError: (error) => {
      logger.error('Character delete failed', error as Error, { component: 'useDeleteCharacter' });
    },
  });
}
