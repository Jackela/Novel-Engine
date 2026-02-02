/**
 * QuickActionsPanel - Quick orchestration controls + connection indicator
 */
import { Play, Pause, Square, RefreshCcw, Wifi } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/shared/components/ui/Card';
import { Button } from '@/shared/components/ui/Button';
import { useOrchestrationStore } from '../stores/orchestrationStore';

export function QuickActionsPanel() {
  const { start, pause, stop, runState } = useOrchestrationStore();

  return (
    <Card className="h-full min-h-[140px]" data-testid="quick-actions">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Quick Actions</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            onClick={start}
            data-testid="quick-action-play"
            aria-label="Start"
          >
            <Play className="mr-2 h-4 w-4" />
            Start
          </Button>
          <Button
            type="button"
            size="sm"
            variant="secondary"
            onClick={pause}
            data-testid="quick-action-pause"
            aria-label="Pause"
          >
            <Pause className="mr-2 h-4 w-4" />
            Pause
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={stop}
            data-testid="quick-action-stop"
            aria-label="Stop"
          >
            <Square className="mr-2 h-4 w-4" />
            Stop
          </Button>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={start}
            data-testid="quick-action-refresh"
            aria-label="Refresh"
          >
            <RefreshCcw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </div>

        <div
          className="flex items-center gap-2 rounded-md bg-muted/40 px-3 py-2 text-sm"
          data-testid="connection-status"
        >
          <Wifi className="h-4 w-4 text-green-500" />
          <span>Connection: Online</span>
          <span className="ml-auto text-xs text-muted-foreground">
            {runState === 'running' ? 'Streaming' : 'Idle'}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
