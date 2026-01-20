/**
 * OrchestrationPage - Main orchestration control page
 */
import { useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  useOrchestrationState,
  useAdvanceTurn,
  usePauseOrchestration,
  useResumeOrchestration,
  useMakeDecision,
  useNarrativeHistory,
} from './api/orchestrationApi';
import { useOrchestrationEvents } from './hooks/useOrchestrationEvents';
import { CommandDeck } from './components/CommandDeck';
import { PipelineStatus } from './components/PipelineStatus';
import { DecisionDialog } from './components/DecisionDialog';
import { NarrativeOutput } from './components/NarrativeOutput';
import { ErrorState, LoadingSpinner } from '@/shared/components/feedback';
import type { DecisionPoint, NarrativeOutput as NarrativeOutputType } from '@/shared/types/orchestration';

export default function OrchestrationPage() {
  const [searchParams] = useSearchParams();
  const campaignId = searchParams.get('campaign') || '';

  const [showDecisionDialog, setShowDecisionDialog] = useState(false);
  const [currentDecision, setCurrentDecision] = useState<DecisionPoint | null>(null);

  // Queries
  const {
    data: state,
    isLoading: isLoadingState,
    error: stateError,
  } = useOrchestrationState(campaignId);

  const { data: narratives = [] } = useNarrativeHistory(campaignId);

  // Mutations
  const advanceTurn = useAdvanceTurn(campaignId);
  const pauseOrchestration = usePauseOrchestration(campaignId);
  const resumeOrchestration = useResumeOrchestration(campaignId);
  const makeDecision = useMakeDecision(campaignId);

  // SSE Events
  const handleDecisionRequired = useCallback((decision: DecisionPoint) => {
    setCurrentDecision(decision);
    setShowDecisionDialog(true);
  }, []);

  const handleNarrativeOutput = useCallback((narrative: NarrativeOutputType) => {
    // Could show toast notification here
    console.log('New narrative:', narrative.id);
  }, []);

  useOrchestrationEvents({
    campaignId,
    onDecisionRequired: handleDecisionRequired,
    onNarrativeOutput: handleNarrativeOutput,
    enabled: !!campaignId,
  });

  // Handlers
  const handleDecide = async (optionId: string) => {
    if (currentDecision) {
      await makeDecision.mutateAsync({
        decisionId: currentDecision.id,
        optionId,
      });
      setShowDecisionDialog(false);
      setCurrentDecision(null);
    }
  };

  if (!campaignId) {
    return (
      <ErrorState
        title="No campaign selected"
        message="Please select a campaign to control the orchestration."
        action={{
          label: 'Go to Campaigns',
          onClick: () => (window.location.href = '/campaigns'),
        }}
      />
    );
  }

  if (isLoadingState) {
    return <LoadingSpinner fullScreen text="Loading orchestration state..." />;
  }

  if (stateError) {
    return (
      <ErrorState
        title="Failed to load orchestration"
        message={stateError.message}
        onRetry={() => window.location.reload()}
      />
    );
  }

  if (!state) {
    return (
      <ErrorState
        title="Orchestration not available"
        message="The orchestration state could not be loaded."
      />
    );
  }

  const isLoading =
    advanceTurn.isPending ||
    pauseOrchestration.isPending ||
    resumeOrchestration.isPending;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Orchestration Control</h1>
        <p className="text-muted-foreground">
          Control the narrative generation pipeline
        </p>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Controls */}
        <div className="space-y-6">
          <CommandDeck
            status={state.status}
            metrics={state.metrics}
            onAdvanceTurn={() => advanceTurn.mutate()}
            onPause={() => pauseOrchestration.mutate()}
            onResume={() => resumeOrchestration.mutate()}
            isLoading={isLoading}
          />

          <PipelineStatus
            status={state.status}
            currentPhase={state.currentPhase}
            agents={state.activeAgents}
          />
        </div>

        {/* Right Column - Narrative */}
        <div className="lg:col-span-2">
          <NarrativeOutput narratives={narratives} maxVisible={5} />
        </div>
      </div>

      {/* Decision Dialog */}
      <DecisionDialog
        decision={currentDecision || state.pendingDecision || null}
        open={showDecisionDialog || !!state.pendingDecision}
        onClose={() => {
          setShowDecisionDialog(false);
          setCurrentDecision(null);
        }}
        onDecide={handleDecide}
        isLoading={makeDecision.isPending}
      />
    </div>
  );
}
