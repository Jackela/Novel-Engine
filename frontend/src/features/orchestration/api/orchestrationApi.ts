/**
 * Orchestration API hooks using TanStack Query
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import type {
  OrchestrationState,
  CommandInput,
  NarrativeOutput,
  DecisionOption,
} from '@/shared/types/orchestration';

const ORCHESTRATION_KEY = ['orchestration'];
const NARRATIVE_KEY = ['narrative'];

// Fetch orchestration state
export function useOrchestrationState(campaignId: string) {
  return useQuery({
    queryKey: [...ORCHESTRATION_KEY, campaignId],
    queryFn: () => api.get<OrchestrationState>(`/orchestration/${campaignId}/state`),
    enabled: !!campaignId,
    refetchInterval: 2000, // Poll every 2 seconds when active
  });
}

// Send command to orchestrator
export function useSendCommand(campaignId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (command: CommandInput) =>
      api.post<OrchestrationState>(`/orchestration/${campaignId}/command`, command),
    onSuccess: (data) => {
      queryClient.setQueryData([...ORCHESTRATION_KEY, campaignId], data);
    },
  });
}

// Advance turn
export function useAdvanceTurn(campaignId: string) {
  const sendCommand = useSendCommand(campaignId);

  return {
    ...sendCommand,
    mutate: () => sendCommand.mutate({ type: 'advance_turn' }),
    mutateAsync: () => sendCommand.mutateAsync({ type: 'advance_turn' }),
  };
}

// Pause orchestration
export function usePauseOrchestration(campaignId: string) {
  const sendCommand = useSendCommand(campaignId);

  return {
    ...sendCommand,
    mutate: () => sendCommand.mutate({ type: 'pause' }),
    mutateAsync: () => sendCommand.mutateAsync({ type: 'pause' }),
  };
}

// Resume orchestration
export function useResumeOrchestration(campaignId: string) {
  const sendCommand = useSendCommand(campaignId);

  return {
    ...sendCommand,
    mutate: () => sendCommand.mutate({ type: 'resume' }),
    mutateAsync: () => sendCommand.mutateAsync({ type: 'resume' }),
  };
}

// Make decision
export function useMakeDecision(campaignId: string) {
  const sendCommand = useSendCommand(campaignId);

  return useMutation({
    mutationFn: ({ decisionId, optionId }: { decisionId: string; optionId: string }) =>
      sendCommand.mutateAsync({
        type: 'decide',
        payload: { decisionId, optionId },
      }),
  });
}

// Fetch narrative history
export function useNarrativeHistory(campaignId: string) {
  return useQuery({
    queryKey: [...NARRATIVE_KEY, campaignId],
    queryFn: () => api.get<NarrativeOutput[]>(`/orchestration/${campaignId}/narrative`),
    enabled: !!campaignId,
  });
}

// Fetch latest narrative output
export function useLatestNarrative(campaignId: string) {
  return useQuery({
    queryKey: [...NARRATIVE_KEY, campaignId, 'latest'],
    queryFn: () => api.get<NarrativeOutput>(`/orchestration/${campaignId}/narrative/latest`),
    enabled: !!campaignId,
  });
}
