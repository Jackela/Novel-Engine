/**
 * World Data API hooks for fetching locations and characters
 *
 * Why: Provides TanStack Query hooks for fetching world entities
 * (characters, locations) with caching and lazy loading support.
 */
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  LocationListResponseSchema,
  CharactersListResponseSchema,
} from '@/types/schemas';

const LOCATIONS_KEY = ['locations'];

/**
 * Fetch all locations.
 * Why: Provides location data for the LocationTree component.
 */
export function useLocations(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: LOCATIONS_KEY,
    queryFn: async () => {
      const data = await api.get<unknown>('/locations');
      return LocationListResponseSchema.parse(data).locations;
    },
    enabled: options?.enabled ?? true,
  });
}

/**
 * Combined hook for world sidebar data (characters + locations).
 * Why: Efficiently loads both datasets for the World sidebar tab
 * with a single enabled flag for lazy loading.
 */
export function useWorldSidebarData(options?: { enabled?: boolean }) {
  const enabled = options?.enabled ?? true;

  const charactersQuery = useQuery({
    queryKey: ['characters'],
    queryFn: async () => {
      const data = await api.get<unknown>('/characters');
      return CharactersListResponseSchema.parse(data).characters;
    },
    enabled,
  });

  const locationsQuery = useQuery({
    queryKey: LOCATIONS_KEY,
    queryFn: async () => {
      const data = await api.get<unknown>('/locations');
      return LocationListResponseSchema.parse(data).locations;
    },
    enabled,
  });

  return {
    characters: charactersQuery.data ?? [],
    locations: locationsQuery.data ?? [],
    isLoading: charactersQuery.isLoading || locationsQuery.isLoading,
    isError: charactersQuery.isError || locationsQuery.isError,
    error: charactersQuery.error || locationsQuery.error,
  };
}
