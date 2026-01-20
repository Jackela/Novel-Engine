/**
 * useOrchestrationEvents - SSE hook for real-time orchestration events
 */
import { useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useRealtimeEvents } from '@/shared/hooks/useRealtimeEvents';
import type {
  OrchestrationEvent,
  OrchestrationState,
  DecisionPoint,
  NarrativeOutput,
} from '@/shared/types/orchestration';

interface UseOrchestrationEventsOptions {
  campaignId: string;
  onDecisionRequired?: (decision: DecisionPoint) => void;
  onNarrativeOutput?: (narrative: NarrativeOutput) => void;
  onError?: (error: Error) => void;
  enabled?: boolean;
}

export function useOrchestrationEvents({
  campaignId,
  onDecisionRequired,
  onNarrativeOutput,
  onError,
  enabled = true,
}: UseOrchestrationEventsOptions) {
  const queryClient = useQueryClient();

  const handleEvent = useCallback(
    (event: OrchestrationEvent) => {
      switch (event.type) {
        case 'phase_change':
        case 'agent_update':
          // Invalidate orchestration state to refetch
          queryClient.invalidateQueries({
            queryKey: ['orchestration', campaignId],
          });
          break;

        case 'decision_required':
          onDecisionRequired?.(event.data as DecisionPoint);
          // Also update state
          queryClient.setQueryData(
            ['orchestration', campaignId],
            (old: OrchestrationState | undefined) =>
              old
                ? { ...old, status: 'waiting_decision', pendingDecision: event.data }
                : undefined
          );
          break;

        case 'decision_resolved':
          queryClient.setQueryData(
            ['orchestration', campaignId],
            (old: OrchestrationState | undefined) =>
              old ? { ...old, status: 'running', pendingDecision: undefined } : undefined
          );
          break;

        case 'narrative_output':
          onNarrativeOutput?.(event.data as NarrativeOutput);
          // Invalidate narrative queries
          queryClient.invalidateQueries({
            queryKey: ['narrative', campaignId],
          });
          break;

        case 'error':
          onError?.(new Error(String(event.data)));
          break;

        case 'heartbeat':
          // Just keep-alive, no action needed
          break;
      }
    },
    [campaignId, queryClient, onDecisionRequired, onNarrativeOutput, onError]
  );

  return useRealtimeEvents({
    url: `/api/orchestration/${campaignId}/events`,
    onEvent: handleEvent,
    enabled: enabled && !!campaignId,
    maxRetries: 5,
    heartbeatInterval: 30000,
  });
}
