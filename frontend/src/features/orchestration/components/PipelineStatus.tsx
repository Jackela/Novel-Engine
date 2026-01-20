/**
 * PipelineStatus - Visual display of orchestration pipeline state
 */
import { Activity, Brain, Zap, FileText, CheckCircle, Loader2 } from 'lucide-react';
import { Card, CardContent, Badge } from '@/shared/components/ui';
import { cn } from '@/shared/lib/utils';
import type { PipelinePhase, AgentStatus, OrchestrationStatus } from '@/shared/types/orchestration';

interface PipelineStatusProps {
  status: OrchestrationStatus;
  currentPhase: PipelinePhase;
  agents: AgentStatus[];
}

const phases: { phase: PipelinePhase; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { phase: 'context_gathering', label: 'Context', icon: Brain },
  { phase: 'planning', label: 'Planning', icon: Activity },
  { phase: 'execution', label: 'Execution', icon: Zap },
  { phase: 'synthesis', label: 'Synthesis', icon: FileText },
  { phase: 'output', label: 'Output', icon: CheckCircle },
];

const statusColors: Record<OrchestrationStatus, string> = {
  idle: 'text-muted-foreground',
  running: 'text-green-500',
  paused: 'text-yellow-500',
  waiting_decision: 'text-blue-500',
  error: 'text-red-500',
};

const agentStatusColors: Record<AgentStatus['status'], string> = {
  idle: 'bg-muted text-muted-foreground',
  thinking: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  acting: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  waiting: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
};

export function PipelineStatus({ status, currentPhase, agents }: PipelineStatusProps) {
  const currentPhaseIndex = phases.findIndex((p) => p.phase === currentPhase);

  return (
    <Card>
      <CardContent className="p-4">
        {/* Status Header */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">Pipeline Status</h3>
          <Badge variant="outline" className={cn(statusColors[status])}>
            {status === 'running' && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
            {status.replace('_', ' ')}
          </Badge>
        </div>

        {/* Phase Progress */}
        <div className="relative mb-6">
          <div className="flex justify-between items-center">
            {phases.map((phase, index) => {
              const Icon = phase.icon;
              const isActive = phase.phase === currentPhase;
              const isComplete = index < currentPhaseIndex;

              return (
                <div
                  key={phase.phase}
                  className={cn(
                    'flex flex-col items-center gap-1 relative z-10',
                    isActive && 'text-primary',
                    isComplete && 'text-green-500',
                    !isActive && !isComplete && 'text-muted-foreground'
                  )}
                >
                  <div
                    className={cn(
                      'w-8 h-8 rounded-full flex items-center justify-center border-2',
                      isActive && 'border-primary bg-primary/10',
                      isComplete && 'border-green-500 bg-green-500/10',
                      !isActive && !isComplete && 'border-muted bg-muted'
                    )}
                  >
                    {isComplete ? (
                      <CheckCircle className="h-4 w-4" />
                    ) : isActive && status === 'running' ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Icon className="h-4 w-4" />
                    )}
                  </div>
                  <span className="text-xs">{phase.label}</span>
                </div>
              );
            })}
          </div>

          {/* Progress Line */}
          <div className="absolute top-4 left-4 right-4 h-0.5 bg-muted -z-0">
            <div
              className="h-full bg-green-500 transition-all duration-500"
              style={{
                width: `${(currentPhaseIndex / (phases.length - 1)) * 100}%`,
              }}
            />
          </div>
        </div>

        {/* Active Agents */}
        <div>
          <h4 className="text-sm font-medium mb-2">Active Agents</h4>
          <div className="space-y-2">
            {agents.map((agent) => (
              <div
                key={agent.id}
                className="flex items-center justify-between p-2 rounded-lg bg-muted/50"
              >
                <div className="flex items-center gap-2">
                  <div
                    className={cn(
                      'w-2 h-2 rounded-full',
                      agent.status === 'acting' && 'bg-green-500 animate-pulse',
                      agent.status === 'thinking' && 'bg-blue-500 animate-pulse',
                      agent.status === 'waiting' && 'bg-yellow-500',
                      agent.status === 'idle' && 'bg-muted-foreground'
                    )}
                  />
                  <span className="text-sm font-medium">{agent.name}</span>
                </div>
                <Badge className={cn('text-xs', agentStatusColors[agent.status])}>
                  {agent.status}
                </Badge>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
