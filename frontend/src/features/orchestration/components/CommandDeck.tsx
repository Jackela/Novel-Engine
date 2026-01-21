/**
 * CommandDeck - Main control panel for orchestration
 */
import { Play, Pause, SkipForward, Settings, Zap, Activity } from 'lucide-react';
import { Button, Card, CardContent } from '@/shared/components/ui';
import { cn } from '@/lib/utils';
import type { OrchestrationStatus, OrchestrationMetrics } from '@/shared/types/orchestration';

interface CommandDeckProps {
  status: OrchestrationStatus;
  metrics: OrchestrationMetrics;
  onAdvanceTurn: () => void;
  onPause: () => void;
  onResume: () => void;
  onOpenSettings?: () => void;
  isLoading?: boolean;
}

export function CommandDeck({
  status,
  metrics,
  onAdvanceTurn,
  onPause,
  onResume,
  onOpenSettings,
  isLoading = false,
}: CommandDeckProps) {
  const isRunning = status === 'running';
  const isPaused = status === 'paused';
  const isIdle = status === 'idle';
  const isWaitingDecision = status === 'waiting_decision';

  return (
    <Card>
      <CardContent className="p-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-primary" />
            <h3 className="font-semibold">Command Deck</h3>
          </div>
          {onOpenSettings && (
            <Button variant="ghost" size="icon" onClick={onOpenSettings}>
              <Settings className="h-4 w-4" />
            </Button>
          )}
        </div>

        {/* Main Controls */}
        <div className="flex gap-2 mb-4">
          {isRunning ? (
            <Button
              variant="outline"
              className="flex-1"
              onClick={onPause}
              disabled={isLoading}
            >
              <Pause className="h-4 w-4 mr-2" />
              Pause
            </Button>
          ) : (
            <Button
              variant="default"
              className="flex-1"
              onClick={isPaused ? onResume : onAdvanceTurn}
              disabled={isLoading || isWaitingDecision}
            >
              <Play className="h-4 w-4 mr-2" />
              {isPaused ? 'Resume' : isIdle ? 'Start' : 'Continue'}
            </Button>
          )}

          <Button
            variant="outline"
            onClick={onAdvanceTurn}
            disabled={isLoading || isRunning || isWaitingDecision}
          >
            <SkipForward className="h-4 w-4 mr-2" />
            Next Turn
          </Button>
        </div>

        {/* Status Indicator */}
        {isWaitingDecision && (
          <div className="p-3 mb-4 rounded-lg bg-blue-100 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800">
            <p className="text-sm text-blue-800 dark:text-blue-200">
              Waiting for your decision to continue...
            </p>
          </div>
        )}

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 gap-3">
          <MetricCard
            label="Turns"
            value={metrics.turnsCompleted}
            icon={<Activity className="h-4 w-4" />}
          />
          <MetricCard
            label="Tokens"
            value={formatNumber(metrics.totalTokens)}
            icon={<Zap className="h-4 w-4" />}
          />
          <MetricCard
            label="Avg Latency"
            value={`${metrics.averageLatency.toFixed(0)}ms`}
            icon={<Activity className="h-4 w-4" />}
          />
          <MetricCard
            label="Decisions"
            value={metrics.decisionsResolved}
            icon={<Activity className="h-4 w-4" />}
          />
        </div>

        {/* Errors */}
        {metrics.errorsEncountered > 0 && (
          <div className="mt-3 p-2 rounded-lg bg-red-100 dark:bg-red-900/30">
            <span className="text-sm text-red-800 dark:text-red-200">
              {metrics.errorsEncountered} error(s) encountered
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface MetricCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
}

function MetricCard({ label, value, icon }: MetricCardProps) {
  return (
    <div className="p-3 rounded-lg bg-muted/50">
      <div className="flex items-center gap-2 text-muted-foreground mb-1">
        {icon}
        <span className="text-xs">{label}</span>
      </div>
      <p className="text-lg font-semibold">{value}</p>
    </div>
  );
}

function formatNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return num.toString();
}
