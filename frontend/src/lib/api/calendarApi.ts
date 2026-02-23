/**
 * Calendar API Hooks using TanStack Query (SIM-004)
 *
 * Provides type-safe access to Calendar endpoints with optimistic
 * updates and cache invalidation for world time management.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  CalendarResponseSchema,
  AdvanceCalendarRequestSchema,
  type CalendarResponse,
} from '@/types/schemas';

/**
 * Query key factory for calendar.
 * Why: Centralizes key creation for consistent cache management.
 */
const calendarKeys = {
  all: ['calendar'] as const,
  detail: (worldId: string) => [...calendarKeys.all, worldId] as const,
};

// ============ Raw API Functions ============

/**
 * Get the current calendar state for a world.
 */
async function getCalendar(worldId: string): Promise<CalendarResponse> {
  const data = await api.get<unknown>(`/calendar/${worldId}`);
  return CalendarResponseSchema.parse(data);
}

/**
 * Advance the calendar for a world by a specified number of days.
 */
async function advanceCalendar(
  worldId: string,
  days: number
): Promise<CalendarResponse> {
  const payload = AdvanceCalendarRequestSchema.parse({ days });
  const data = await api.post<unknown>(`/calendar/${worldId}/advance`, payload);
  return CalendarResponseSchema.parse(data);
}

// ============ TanStack Query Hooks ============

/**
 * Hook to fetch the current calendar state for a world.
 *
 * @param worldId - The unique identifier for the world
 * @returns Query result with calendar data
 */
export function useCalendar(worldId: string | undefined) {
  return useQuery({
    queryKey: calendarKeys.detail(worldId ?? ''),
    queryFn: () => getCalendar(worldId!),
    enabled: !!worldId,
  });
}

/**
 * Hook to advance the calendar by a number of days.
 *
 * Why: Provides optimistic updates for immediate UI feedback
 * with rollback on failure.
 *
 * @returns Mutation hook with mutate function
 */
export function useAdvanceCalendar() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ worldId, days }: { worldId: string; days: number }) =>
      advanceCalendar(worldId, days),
    // Optimistic update for immediate visual feedback
    onMutate: async ({ worldId, days }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: calendarKeys.detail(worldId) });

      // Snapshot the previous value for rollback
      const previousCalendar = queryClient.getQueryData<CalendarResponse>(
        calendarKeys.detail(worldId)
      );

      // Optimistically update calendar (approximate - actual dates computed server-side)
      if (previousCalendar) {
        let newDay = previousCalendar.day + days;
        let newMonth = previousCalendar.month;
        let newYear = previousCalendar.year;
        const daysPerMonth = previousCalendar.days_per_month;
        const monthsPerYear = previousCalendar.months_per_year;

        // Handle overflow (simplified - server does proper calculation)
        while (newDay > daysPerMonth) {
          newDay -= daysPerMonth;
          newMonth += 1;
        }
        while (newMonth > monthsPerYear) {
          newMonth -= monthsPerYear;
          newYear += 1;
        }

        const optimisticCalendar: CalendarResponse = {
          ...previousCalendar,
          day: newDay,
          month: newMonth,
          year: newYear,
          formatted_date: `Year ${newYear}, Month ${newMonth}, Day ${newDay} - ${previousCalendar.era_name}`,
        };

        queryClient.setQueryData<CalendarResponse>(
          calendarKeys.detail(worldId),
          optimisticCalendar
        );
      }

      return { previousCalendar };
    },
    // If mutation fails, roll back to previous value
    onError: (_, variables, context) => {
      if (context?.previousCalendar) {
        queryClient.setQueryData(
          calendarKeys.detail(variables.worldId),
          context.previousCalendar
        );
      }
    },
    // Persist server-truth response in cache to avoid UI flicker back to stale GET data.
    onSuccess: (data, variables) => {
      queryClient.setQueryData(calendarKeys.detail(variables.worldId), data);
    },
  });
}

// Export raw functions for non-hook usage
export { getCalendar, advanceCalendar };
