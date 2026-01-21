/**
 * Character API hooks using TanStack Query
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import type { CharacterDetail, CreateCharacterInput, UpdateCharacterInput } from '@/shared/types/character';
import { CharactersListResponseSchema, CharacterDetailSchema } from '@/types/schemas';

const CHARACTERS_KEY = ['characters'];

// Fetch all characters
export function useCharacters() {
  return useQuery({
    queryKey: CHARACTERS_KEY,
    queryFn: async () => {
      const data = await api.get<unknown>('/characters');
      return CharactersListResponseSchema.parse(data).characters;
    },
  });
}

// Fetch single character
export function useCharacter(id: string) {
  return useQuery({
    queryKey: [...CHARACTERS_KEY, id],
    queryFn: async () => {
      const data = await api.get<unknown>(`/characters/${id}`);
      return CharacterDetailSchema.parse(data);
    },
    enabled: !!id,
  });
}

// Create character
export function useCreateCharacter() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: CreateCharacterInput) =>
      api.post<CharacterDetail>('/characters', input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CHARACTERS_KEY });
    },
  });
}

// Update character
export function useUpdateCharacter() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, ...input }: UpdateCharacterInput) =>
      api.put<CharacterDetail>(`/characters/${id}`, input),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: CHARACTERS_KEY });
      queryClient.setQueryData([...CHARACTERS_KEY, data.id], data);
    },
  });
}

// Delete character
export function useDeleteCharacter() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.delete(`/characters/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CHARACTERS_KEY });
    },
  });
}
