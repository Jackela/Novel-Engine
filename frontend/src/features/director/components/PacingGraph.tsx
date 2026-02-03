/**
 * PacingGraph - Visualizes tension and energy curves across scenes in a chapter.
 *
 * Why: Directors and writers need to see the narrative rhythm of their story.
 * This component uses a dual-axis AreaChart to show how tension and energy
 * flow across scenes, helping identify monotonous sections or abrupt shifts.
 *
 * Uses Recharts for visualization with custom styling to match the design system.
 */
import { useMemo } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
} from 'recharts';
import { Loader2, AlertTriangle, BarChart3 } from 'lucide-react';

import { cn } from '@/lib/utils';
import { useChapterPacing } from '../api/pacingApi';
import type { ScenePacingMetrics, PacingIssue } from '@/types/schemas';

/**
 * Custom tooltip for the pacing chart.
 * Shows scene title and both tension/energy values on hover.
 */
interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: ChartDataPoint;
    dataKey: string;
    value: number;
    color: string;
  }>;
  label?: string;
}

interface ChartDataPoint {
  name: string;
  sceneId: string;
  sceneTitle: string;
  tension: number;
  energy: number;
}

function PacingTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  const firstPayload = payload[0];
  if (!firstPayload) return null;

  const data = firstPayload.payload;

  return (
    <div className="rounded-md border bg-popover px-3 py-2 shadow-md">
      <p className="mb-1 font-medium">{data.sceneTitle}</p>
      <div className="space-y-1 text-sm">
        <p className="flex items-center gap-2">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ backgroundColor: 'hsl(var(--primary))' }}
          />
          Tension: {data.tension}
        </p>
        <p className="flex items-center gap-2">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ backgroundColor: 'hsl(var(--destructive))' }}
          />
          Energy: {data.energy}
        </p>
      </div>
    </div>
  );
}

/**
 * Severity badge for pacing issues.
 */
function SeverityBadge({ severity }: { severity: PacingIssue['severity'] }) {
  const colors: Record<PacingIssue['severity'], string> = {
    low: 'bg-muted text-muted-foreground',
    medium: 'bg-warning/20 text-warning',
    high: 'bg-destructive/20 text-destructive',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
        colors[severity]
      )}
    >
      {severity}
    </span>
  );
}

interface PacingGraphProps {
  /** Story ID for fetching pacing data */
  storyId: string;
  /** Chapter ID for fetching pacing data */
  chapterId: string;
  /** Optional CSS class name */
  className?: string;
  /** Height of the chart container (default: 300px) */
  height?: number;
  /** Show issues panel below the chart (default: true) */
  showIssues?: boolean;
}

/**
 * PacingGraph - Main component for visualizing chapter pacing.
 *
 * Features:
 * - Dual-axis AreaChart showing tension (blue) and energy (red) curves
 * - X-axis: Scene sequence (by order_index)
 * - Y-axis: Scale 0-10 for both metrics
 * - Tooltips showing scene title on hover
 * - Reference lines for average values
 * - Issues panel showing detected pacing problems
 */
export function PacingGraph({
  storyId,
  chapterId,
  className,
  height = 300,
  showIssues = true,
}: PacingGraphProps) {
  const { data, isLoading, error } = useChapterPacing(storyId, chapterId);

  // Transform scene metrics into chart-friendly format
  const chartData = useMemo<ChartDataPoint[]>(() => {
    if (!data?.scene_metrics) return [];

    return data.scene_metrics.map((metric: ScenePacingMetrics, index: number) => ({
      name: `Scene ${index + 1}`,
      sceneId: metric.scene_id,
      sceneTitle: metric.scene_title,
      tension: metric.tension_level,
      energy: metric.energy_level,
    }));
  }, [data?.scene_metrics]);

  // Loading state
  if (isLoading) {
    return (
      <div
        className={cn('flex items-center justify-center', className)}
        style={{ height }}
      >
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        className={cn(
          'flex flex-col items-center justify-center gap-2 text-destructive',
          className
        )}
        style={{ height }}
      >
        <AlertTriangle className="h-6 w-6" />
        <p className="text-sm">Failed to load pacing data</p>
      </div>
    );
  }

  // Empty state
  if (!data || chartData.length === 0) {
    return (
      <div
        className={cn(
          'flex flex-col items-center justify-center gap-2 text-muted-foreground',
          className
        )}
        style={{ height }}
      >
        <BarChart3 className="h-8 w-8" />
        <p className="text-sm">No scenes in this chapter yet.</p>
        <p className="text-xs">Add scenes to see the pacing graph.</p>
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Chart */}
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={chartData}
            margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
          >
            <defs>
              {/* Gradient for tension area */}
              <linearGradient id="tensionGradient" x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="5%"
                  stopColor="hsl(var(--primary))"
                  stopOpacity={0.4}
                />
                <stop
                  offset="95%"
                  stopColor="hsl(var(--primary))"
                  stopOpacity={0}
                />
              </linearGradient>
              {/* Gradient for energy area */}
              <linearGradient id="energyGradient" x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="5%"
                  stopColor="hsl(var(--destructive))"
                  stopOpacity={0.4}
                />
                <stop
                  offset="95%"
                  stopColor="hsl(var(--destructive))"
                  stopOpacity={0}
                />
              </linearGradient>
            </defs>

            <CartesianGrid
              strokeDasharray="3 3"
              stroke="hsl(var(--border))"
              vertical={false}
            />

            <XAxis
              dataKey="name"
              tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
              tickLine={{ stroke: 'hsl(var(--border))' }}
              axisLine={{ stroke: 'hsl(var(--border))' }}
            />

            <YAxis
              domain={[0, 10]}
              tickCount={6}
              tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
              tickLine={{ stroke: 'hsl(var(--border))' }}
              axisLine={{ stroke: 'hsl(var(--border))' }}
            />

            {/* Average tension reference line */}
            <ReferenceLine
              y={data.average_tension}
              stroke="hsl(var(--primary))"
              strokeDasharray="5 5"
              strokeOpacity={0.5}
            />

            {/* Average energy reference line */}
            <ReferenceLine
              y={data.average_energy}
              stroke="hsl(var(--destructive))"
              strokeDasharray="5 5"
              strokeOpacity={0.5}
            />

            <Tooltip content={<PacingTooltip />} />

            <Legend
              verticalAlign="top"
              height={36}
              iconType="circle"
              formatter={(value: string) => (
                <span className="text-sm text-foreground">{value}</span>
              )}
            />

            {/* Tension area */}
            <Area
              type="monotone"
              dataKey="tension"
              name="Tension"
              stroke="hsl(var(--primary))"
              fill="url(#tensionGradient)"
              strokeWidth={2}
              dot={{ r: 4, fill: 'hsl(var(--primary))' }}
              activeDot={{ r: 6, fill: 'hsl(var(--primary))' }}
            />

            {/* Energy area */}
            <Area
              type="monotone"
              dataKey="energy"
              name="Energy"
              stroke="hsl(var(--destructive))"
              fill="url(#energyGradient)"
              strokeWidth={2}
              dot={{ r: 4, fill: 'hsl(var(--destructive))' }}
              activeDot={{ r: 6, fill: 'hsl(var(--destructive))' }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Statistics summary */}
      <div className="flex flex-wrap gap-4 text-sm">
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">Avg Tension:</span>
          <span className="font-medium">{data.average_tension.toFixed(1)}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">Avg Energy:</span>
          <span className="font-medium">{data.average_energy.toFixed(1)}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">Tension Range:</span>
          <span className="font-medium">
            {data.tension_range[0]} - {data.tension_range[1]}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">Energy Range:</span>
          <span className="font-medium">
            {data.energy_range[0]} - {data.energy_range[1]}
          </span>
        </div>
      </div>

      {/* Issues panel */}
      {showIssues && data.issues.length > 0 && (
        <div className="space-y-2 rounded-lg border bg-muted/30 p-4">
          <h4 className="flex items-center gap-2 text-sm font-medium">
            <AlertTriangle className="h-4 w-4 text-warning" />
            Pacing Issues ({data.issues.length})
          </h4>
          <ul className="space-y-2">
            {data.issues.map((issue: PacingIssue, index: number) => (
              <li
                key={`${issue.issue_type}-${index}`}
                className="rounded-md bg-background p-3 text-sm"
              >
                <div className="mb-1 flex items-center gap-2">
                  <SeverityBadge severity={issue.severity} />
                  <span className="font-medium capitalize">
                    {issue.issue_type.replace(/_/g, ' ')}
                  </span>
                </div>
                <p className="mb-1 text-muted-foreground">{issue.description}</p>
                <p className="text-xs text-muted-foreground italic">
                  {issue.suggestion}
                </p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default PacingGraph;
