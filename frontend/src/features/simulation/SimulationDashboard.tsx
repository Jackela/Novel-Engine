/**
 * SimulationDashboard Component (SIM-031)
 *
 * Main simulation dashboard page with controls, events, and faction displays.
 * Uses a 3-column responsive grid layout.
 *
 * Features:
 * - Calendar display with advance controls
 * - Preview and commit simulation buttons
 * - Snapshot creation and restoration
 * - Events timeline and rumors display
 * - Faction status summary
 * - Accessible with WCAG 2.1 AA compliance
 */
import { useState, useCallback } from 'react';
import { Link } from '@tanstack/react-router';
import {
  Clock,
  Play,
  FastForward,
  Camera,
  RotateCcw,
  ChevronDown,
  ChevronUp,
  Users,
  ExternalLink,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/shared/components/ui';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/shared/components/ui/Skeleton';
import { Badge } from '@/shared/components/ui/Badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { CalendarDisplay } from '@/components/world/CalendarDisplay';
import WorldTimeline from '@/components/world/WorldTimeline';
import { RumorBoard } from '@/components/world/RumorBoard';
import {
  usePreviewSimulation,
  useCommitSimulation,
  useSnapshots,
  useCreateSnapshot,
  useRestoreSnapshot,
  useSimulationHistory,
} from '@/lib/api';
import { useSimulationStore } from './stores/simulationStore';
import type { SnapshotSummary } from '@/types/schemas';

const DEFAULT_WORLD_ID = 'default-world';

/**
 * SimulationDashboard - Main simulation control page
 */
export function SimulationDashboard() {
  const [showRumors, setShowRumors] = useState(true);
  const worldId = DEFAULT_WORLD_ID;

  // Store state and actions
  const {
    isLoading,
    isPreviewing,
    lastTick,
    error,
    statusMessage,
    setLoading,
    setPreviewing,
    setLastTick,
    setError,
    setStatusMessage,
    clearError,
  } = useSimulationStore();

  // API hooks
  const previewMutation = usePreviewSimulation();
  const commitMutation = useCommitSimulation();
  const { data: snapshotsData, isLoading: snapshotsLoading } = useSnapshots(worldId, 5);
  const { data: historyData } = useSimulationHistory(worldId, 10);
  const createSnapshotMutation = useCreateSnapshot();
  const restoreSnapshotMutation = useRestoreSnapshot();

  // Handlers
  const handlePreview = useCallback(
    async (days: number) => {
      clearError();
      setPreviewing(true);
      setStatusMessage(`Previewing ${days} day${days > 1 ? 's' : ''}...`);
      try {
        const result = await previewMutation.mutateAsync({ worldId, days });
        setLastTick(result);
        setStatusMessage(`Preview complete: ${result.days_advanced} days`);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Preview failed');
      } finally {
        setPreviewing(false);
      }
    },
    [worldId, previewMutation, clearError, setPreviewing, setLastTick, setError, setStatusMessage]
  );

  const handleCommit = useCallback(
    async (days: number) => {
      clearError();
      setLoading(true);
      setStatusMessage(`Simulating ${days} day${days > 1 ? 's' : ''}...`);
      try {
        const result = await commitMutation.mutateAsync({ worldId, days });
        setLastTick(result);
        setStatusMessage(`Simulation complete: ${result.days_advanced} days advanced`);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Simulation failed');
      } finally {
        setLoading(false);
      }
    },
    [worldId, commitMutation, clearError, setLoading, setLastTick, setError, setStatusMessage]
  );

  const handleCreateSnapshot = useCallback(async () => {
    clearError();
    setStatusMessage('Creating snapshot...');
    try {
      const tickNumber = historyData?.total ?? 0;
      await createSnapshotMutation.mutateAsync({
        worldId,
        request: {
          tick_number: tickNumber,
          state_json: '{}',
          description: `Tick ${tickNumber}`,
        },
      });
      setStatusMessage('Snapshot created');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create snapshot');
    }
  }, [worldId, historyData, createSnapshotMutation, clearError, setError, setStatusMessage]);

  const handleRestoreSnapshot = useCallback(
    async (snapshotId: string) => {
      clearError();
      setLoading(true);
      setStatusMessage('Restoring snapshot...');
      try {
        await restoreSnapshotMutation.mutateAsync({ worldId, snapshotId });
        setStatusMessage('Snapshot restored');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to restore snapshot');
      } finally {
        setLoading(false);
      }
    },
    [worldId, restoreSnapshotMutation, clearError, setLoading, setError, setStatusMessage]
  );

  const isOperating = isLoading || isPreviewing;

  return (
    <main
      className="container mx-auto p-4 lg:p-6"
      role="main"
      aria-label="Simulation Dashboard"
    >
      <div className="grid gap-6 lg:grid-cols-4">
        {/* Left Column - Controls (25%) */}
        <div className="lg:col-span-1 space-y-4">
          {/* Calendar Display */}
          <CalendarDisplay worldId={worldId} />

          {/* Simulation Controls */}
          <Card data-testid="simulation-controls">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Play className="h-5 w-5 text-primary" />
                Simulate
              </CardTitle>
              <CardDescription>Preview or commit world simulation</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Preview Buttons */}
              <div className="space-y-2">
                <span className="text-sm font-medium text-muted-foreground">
                  Preview (Read-only)
                </span>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePreview(1)}
                    disabled={isOperating}
                    aria-label="Preview 1 day"
                  >
                    <FastForward className="mr-1 h-4 w-4" />1d
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePreview(7)}
                    disabled={isOperating}
                    aria-label="Preview 7 days"
                  >
                    <FastForward className="mr-1 h-4 w-4" />7d
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePreview(30)}
                    disabled={isOperating}
                    aria-label="Preview 30 days"
                  >
                    <FastForward className="mr-1 h-4 w-4" />30d
                  </Button>
                </div>
              </div>

              {/* Commit Buttons */}
              <div className="space-y-2">
                <span className="text-sm font-medium text-muted-foreground">
                  Commit (Persist)
                </span>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="default"
                    size="sm"
                    onClick={() => handleCommit(1)}
                    disabled={isOperating}
                    aria-label="Commit 1 day simulation"
                  >
                    <Play className="mr-1 h-4 w-4" />1d
                  </Button>
                  <Button
                    variant="default"
                    size="sm"
                    onClick={() => handleCommit(7)}
                    disabled={isOperating}
                    aria-label="Commit 7 days simulation"
                  >
                    <Play className="mr-1 h-4 w-4" />7d
                  </Button>
                  <Button
                    variant="default"
                    size="sm"
                    onClick={() => handleCommit(30)}
                    disabled={isOperating}
                    aria-label="Commit 30 days simulation"
                  >
                    <Play className="mr-1 h-4 w-4" />30d
                  </Button>
                </div>
              </div>

              {/* Progress Indicator */}
              {isOperating && (
                <div
                  className="flex items-center gap-2 text-sm text-muted-foreground"
                  aria-live="polite"
                >
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>{statusMessage || 'Simulating...'}</span>
                </div>
              )}

              {/* Error Display */}
              {error && (
                <div
                  className="flex items-center gap-2 text-sm text-destructive"
                  role="alert"
                >
                  <AlertCircle className="h-4 w-4" />
                  <span>{error}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={clearError}
                    aria-label="Dismiss error"
                  >
                    Dismiss
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Snapshot Controls */}
          <Card data-testid="snapshot-controls">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Camera className="h-5 w-5 text-primary" />
                Snapshots
              </CardTitle>
              <CardDescription>Save and restore world states</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Create Snapshot */}
              <Button
                variant="outline"
                size="sm"
                onClick={handleCreateSnapshot}
                disabled={isOperating}
                className="w-full"
                aria-label="Create snapshot"
              >
                <Camera className="mr-2 h-4 w-4" />
                Create Snapshot
              </Button>

              {/* Restore Dropdown */}
              <div className="space-y-2">
                <span className="text-sm font-medium text-muted-foreground">
                  Restore Snapshot
                </span>
                {snapshotsLoading ? (
                  <Skeleton className="h-10 w-full" />
                ) : snapshotsData && snapshotsData.snapshots.length > 0 ? (
                  <Select onValueChange={handleRestoreSnapshot} disabled={isOperating}>
                    <SelectTrigger aria-label="Select snapshot to restore">
                      <SelectValue placeholder="Select snapshot..." />
                    </SelectTrigger>
                    <SelectContent>
                      {snapshotsData.snapshots.map((snapshot: SnapshotSummary) => (
                        <SelectItem key={snapshot.snapshot_id} value={snapshot.snapshot_id}>
                          {snapshot.description || `Tick ${snapshot.tick_number}`}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <p className="text-sm text-muted-foreground">No snapshots available</p>
                )}
              </div>

              {/* Snapshot List */}
              {snapshotsData && snapshotsData.snapshots.length > 0 && (
                <div className="space-y-1">
                  <span className="text-xs font-medium text-muted-foreground">
                    Recent Snapshots
                  </span>
                  <ScrollArea className="h-24">
                    <ul className="space-y-1 text-sm">
                      {snapshotsData.snapshots.slice(0, 5).map((snapshot: SnapshotSummary) => (
                        <li
                          key={snapshot.snapshot_id}
                          className="flex items-center justify-between rounded p-1 hover:bg-muted"
                        >
                          <span className="truncate">
                            {snapshot.description || `Tick ${snapshot.tick_number}`}
                          </span>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0"
                            onClick={() => handleRestoreSnapshot(snapshot.snapshot_id)}
                            disabled={isOperating}
                            aria-label={`Restore ${snapshot.description}`}
                          >
                            <RotateCcw className="h-3 w-3" />
                          </Button>
                        </li>
                      ))}
                    </ul>
                  </ScrollArea>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Last Tick Result */}
          {lastTick && (
            <Card data-testid="last-tick-result">
              <CardHeader>
                <CardTitle className="text-sm">Last Result</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Days Advanced:</span>
                    <span className="font-medium" data-testid="days-advanced-value">
                      {lastTick.days_advanced}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Events Generated:</span>
                    <span className="font-medium" data-testid="events-generated-value">
                      {lastTick.events_generated.length}
                    </span>
                  </div>
                  {lastTick.calendar_after && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">New Date:</span>
                      <span className="font-medium" data-testid="new-date-value">
                        {lastTick.calendar_after.formatted_date}
                      </span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Center Column - Events (50%) */}
        <div className="lg:col-span-2 space-y-4">
          {/* Events Timeline */}
          <WorldTimeline worldId={worldId} />

          {/* Rumor Board (Collapsible) */}
          <Card>
            <button
              type="button"
              className="w-full flex items-center justify-between p-4 text-left"
              onClick={() => setShowRumors(!showRumors)}
              aria-expanded={showRumors}
              aria-controls="rumor-board-content"
            >
              <CardTitle className="flex items-center gap-2">
                Rumors
                <Badge variant="secondary" className="text-xs">
                  Optional
                </Badge>
              </CardTitle>
              {showRumors ? (
                <ChevronUp className="h-5 w-5" />
              ) : (
                <ChevronDown className="h-5 w-5" />
              )}
            </button>
            {showRumors && (
              <div id="rumor-board-content">
                <RumorBoard worldId={worldId} maxItems={10} />
              </div>
            )}
          </Card>
        </div>

        {/* Right Column - Factions (25%) */}
        <div className="lg:col-span-1 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5 text-primary" />
                Factions
              </CardTitle>
              <CardDescription>Current faction status</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  Faction status summaries will appear here as simulations progress.
                </p>
                <Link
                  to="/world"
                  className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
                >
                  View Full Matrix
                  <ExternalLink className="h-3 w-3" />
                </Link>
              </div>
            </CardContent>
          </Card>

          {/* Simulation History */}
          {historyData && historyData.ticks.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="h-5 w-5 text-primary" />
                  Recent Simulations
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-40">
                  <ul className="space-y-2 text-sm">
                    {historyData.ticks.slice(0, 5).map((tick) => (
                      <li
                        key={tick.tick_id}
                        className="flex items-center justify-between rounded border p-2"
                      >
                        <div>
                          <span className="font-medium">{tick.days_advanced} days</span>
                          <span className="ml-2 text-xs text-muted-foreground">
                            {tick.events_count} events
                          </span>
                        </div>
                        <span className="text-xs text-muted-foreground">
                          {new Date(tick.created_at).toLocaleTimeString()}
                        </span>
                      </li>
                    ))}
                  </ul>
                </ScrollArea>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Live Region for Status Updates */}
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {statusMessage}
      </div>
    </main>
  );
}

export default SimulationDashboard;
