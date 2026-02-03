/**
 * TurnPipelinePanel - Shows orchestration phases + run status
 */
import { Card, CardHeader, CardTitle, CardContent } from '@/shared/components/ui/Card';
import { useOrchestrationStore } from '../stores/orchestrationStore';

export function TurnPipelinePanel() {
  const { phases, runState } = useOrchestrationStore();

  return (
    <Card className="h-full min-h-[140px]" data-testid="turn-pipeline-status">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Turn Pipeline</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Run state</span>
          <span data-testid="pipeline-run-state" className="font-medium">
            {runState === 'paused'
              ? 'Paused'
              : runState === 'running'
                ? 'Running'
                : 'Idle'}
          </span>
        </div>
        <div className="space-y-2">
          {phases.map((phase) => (
            <div
              key={phase.name}
              data-phase-name={phase.name}
              data-status={phase.status === 'processing' ? 'processing' : phase.status}
              className="flex items-center justify-between rounded-md bg-muted/30 px-3 py-2 text-sm"
            >
              <span className="flex items-center gap-2">
                <span
                  className="h-2 w-2 rounded-full bg-primary/40"
                  data-testid="pipeline-stage-marker"
                />
                {phase.name}
              </span>
              <span className="text-xs text-muted-foreground">
                {phase.status === 'processing'
                  ? 'Processing'
                  : phase.status === 'completed'
                    ? 'Completed'
                    : 'Pending'}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
