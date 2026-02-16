/**
 * ChapterHealth - Stats and health indicators for chapter structure.
 *
 * Why: Writers need to understand if their chapter is structurally sound.
 * This component displays word count target vs actual, phase distribution,
 * health warnings, and actionable recommendations from the ChapterAnalysisService.
 *
 * DIR-056: Frontend: Chapter Health Dashboard
 */
import { useMemo } from 'react';
import {
  Loader2,
  FileText,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

import { cn } from '@/lib/utils';
import { useChapterHealth } from '../api/chapterAnalysisApi';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { Badge } from '@/components/ui/badge';
import type { HealthWarning, HealthScore } from '@/types/schemas';

/**
 * Health score icon component.
 */
function HealthScoreIcon({ score }: { score: HealthScore }) {
  const config: Record<HealthScore, { Icon: typeof CheckCircle2; className: string }> =
    {
      excellent: { Icon: CheckCircle2, className: 'text-green-500' },
      good: { Icon: CheckCircle2, className: 'text-emerald-500' },
      fair: { Icon: AlertCircle, className: 'text-yellow-500' },
      poor: { Icon: AlertTriangle, className: 'text-orange-500' },
      critical: { Icon: XCircle, className: 'text-destructive' },
    };

  const { Icon, className } = config[score];
  return <Icon className={cn('h-5 w-5', className)} />;
}

/**
 * Health score badge component.
 */
function HealthScoreBadge({ score }: { score: HealthScore }) {
  const colors: Record<HealthScore, string> = {
    excellent: 'bg-green-500/10 text-green-500 border-green-500/20',
    good: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
    fair: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
    poor: 'bg-orange-500/10 text-orange-500 border-orange-500/20',
    critical: 'bg-destructive/10 text-destructive border-destructive/20',
  };

  return (
    <Badge
      variant="outline"
      className={cn('text-xs font-medium uppercase', colors[score])}
    >
      {score}
    </Badge>
  );
}

/**
 * Severity badge for health warnings.
 */
function WarningSeverityBadge({ severity }: { severity: HealthWarning['severity'] }) {
  const colors: Record<HealthWarning['severity'], string> = {
    low: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
    medium: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
    high: 'bg-orange-500/10 text-orange-500 border-orange-500/20',
    critical: 'bg-destructive/10 text-destructive border-destructive/20',
  };

  const icons: Record<HealthWarning['severity'], string> = {
    low: '⚪',
    medium: '⚠️',
    high: '🔶',
    critical: '🔴',
  };

  return (
    <Badge
      variant="outline"
      className={cn('shrink-0 text-xs font-medium uppercase', colors[severity])}
    >
      <span className="mr-1">{icons[severity]}</span>
      {severity}
    </Badge>
  );
}

/**
 * Phase distribution pie chart colors.
 *
 * Why HSL variables: Follows design system token-first approach.
 * These colors match the story phase semantic meaning while staying
 * consistent with the app's color theme.
 */
const PHASE_COLORS = {
  setup: 'hsl(var(--primary))', // blue - setup phase
  inciting_incident: 'hsl(38 92% 50%)', // amber - inciting incident
  rising_action: 'hsl(262 83% 58%)', // purple - rising action
  climax: 'hsl(var(--destructive))', // red - climax
  resolution: 'hsl(142 71% 45%)', // green - resolution
};

/**
 * Phase labels for display.
 */
const PHASE_LABELS = {
  setup: 'Setup',
  inciting_incident: 'Inciting',
  rising_action: 'Rising',
  climax: 'Climax',
  resolution: 'Resolution',
} as const;

/**
 * Warning item component with collapsible details.
 */
interface WarningItemProps {
  warning: HealthWarning;
  index: number;
  defaultOpen?: boolean;
}

function WarningItem({ warning, index, defaultOpen = false }: WarningItemProps) {
  const [isOpen, setIsOpen] = React.useState(defaultOpen);

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <div className="rounded-md border bg-card">
        <CollapsibleTrigger className="flex w-full items-center justify-between p-3 hover:bg-muted/50">
          <div className="flex items-center gap-2">
            <WarningSeverityBadge severity={warning.severity} />
            <span className="font-medium">{warning.title}</span>
          </div>
          {isOpen ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </CollapsibleTrigger>
        <CollapsibleContent className="px-3 pb-3">
          <div className="space-y-2 text-sm">
            <p className="text-muted-foreground">{warning.description}</p>
            <div className="rounded-md bg-muted p-2">
              <p className="text-xs font-medium uppercase text-muted-foreground">
                Recommendation
              </p>
              <p className="mt-1">{warning.recommendation}</p>
            </div>
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  );
}

interface ChapterHealthProps {
  /** Story ID for fetching health data */
  storyId: string;
  /** Chapter ID for fetching health data */
  chapterId: string;
  /** Optional CSS class name */
  className?: string;
  /** Target word count for progress bar (default: 5000) */
  targetWordCount?: number;
  /** Show recommendations panel (default: true) */
  showRecommendations?: boolean;
}

/**
 * ChapterHealth - Main component for displaying chapter health metrics.
 *
 * Features:
 * - Word count target vs actual (progress bar)
 * - Phase distribution pie chart
 * - Health score badge
 * - Health warnings as colored badges
 * - Expandable recommendations section
 */
export function ChapterHealth({
  storyId,
  chapterId,
  className,
  targetWordCount = 5000,
  showRecommendations = true,
}: ChapterHealthProps) {
  const { data, isLoading, error } = useChapterHealth(storyId, chapterId);

  // Transform phase distribution into chart-friendly format
  const phaseData = useMemo(() => {
    if (!data?.phase_distribution) return [];

    const entries = Object.entries(data.phase_distribution);
    return entries
      .filter(([_, count]) => count > 0)
      .map(([phase, count]) => ({
        name: PHASE_LABELS[phase as keyof typeof PHASE_LABELS],
        value: count,
        color: PHASE_COLORS[phase as keyof typeof PHASE_COLORS],
      }));
  }, [data?.phase_distribution]);

  // Calculate word count progress percentage
  const wordCountProgress = useMemo(() => {
    if (!data?.word_count) return 0;
    return Math.min((data.word_count.total_words / targetWordCount) * 100, 100);
  }, [data?.word_count, targetWordCount]);

  // Group warnings by category
  const warningsByCategory = useMemo(() => {
    if (!data?.warnings) return {};

    return data.warnings.reduce(
      (acc, warning) => {
        const category = warning.category;
        if (!acc[category]) {
          acc[category] = [];
        }
        acc[category]!.push(warning);
        return acc;
      },
      {} as Record<string, HealthWarning[]>
    );
  }, [data?.warnings]);

  // Loading state
  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Chapter Health
          </CardTitle>
          <CardDescription>Structural analysis for this chapter</CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  // Error state
  if (error) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Chapter Health
          </CardTitle>
          <CardDescription>Structural analysis for this chapter</CardDescription>
        </CardHeader>
        <CardContent className="py-12 text-center">
          <AlertTriangle className="mx-auto mb-2 h-8 w-8 text-destructive" />
          <p className="text-sm text-muted-foreground">
            Failed to load chapter health data
          </p>
        </CardContent>
      </Card>
    );
  }

  // Empty state (no data)
  if (!data) {
    return null;
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            <CardTitle>Chapter Health</CardTitle>
            <HealthScoreBadge score={data.health_score} />
          </div>
          <HealthScoreIcon score={data.health_score} />
        </div>
        <CardDescription>
          Structural analysis based on {data.total_scenes} scene
          {data.total_scenes !== 1 ? 's' : ''} and {data.total_beats} beat
          {data.total_beats !== 1 ? 's' : ''}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Word Count Progress */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">Word Count Estimate</span>
            <span className="text-muted-foreground">
              {data.word_count.total_words.toLocaleString()} /{' '}
              {targetWordCount.toLocaleString()}
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
            <div
              className="h-full bg-primary transition-all"
              style={{ width: `${wordCountProgress}%` }}
            />
          </div>
          <p className="text-xs text-muted-foreground">
            Range: {data.word_count.min_words.toLocaleString()} -{' '}
            {data.word_count.max_words.toLocaleString()} words (
            {data.word_count.per_scene_average.toFixed(0)} avg/scene)
          </p>
        </div>

        {/* Phase Distribution Pie Chart */}
        <div className="space-y-2">
          <h3 className="text-sm font-medium">Phase Distribution</h3>
          {phaseData.length > 0 ? (
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={phaseData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) =>
                      `${name} ${((percent ?? 0) * 100).toFixed(0)}%`
                    }
                    outerRadius={60}
                    fill="hsl(var(--primary))"
                    dataKey="value"
                  >
                    {phaseData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-center text-sm text-muted-foreground">
              No scenes with assigned phases
            </p>
          )}
        </div>

        {/* Health Warnings */}
        {data.warnings.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-sm font-medium">
              Health Warnings ({data.warnings.length})
            </h3>
            <div className="space-y-2">
              {Object.entries(warningsByCategory).map(([category, warnings]) => (
                <div key={category} className="space-y-2">
                  <p className="text-xs font-medium uppercase text-muted-foreground">
                    {category}
                  </p>
                  {warnings.map((warning, index) => (
                    <WarningItem
                      key={`${warning.category}-${index}`}
                      warning={warning}
                      index={index}
                    />
                  ))}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tension Arc Info */}
        <div className="rounded-md border bg-muted/50 p-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Tension Arc</span>
            <Badge variant="outline" className="capitalize">
              {data.tension_arc.shape_type}
            </Badge>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            Starts at {data.tension_arc.starts_at}, peaks at {data.tension_arc.peaks_at}
            , ends at {data.tension_arc.ends_at}
            {data.tension_arc.has_clear_climax && (
              <span className="ml-1">• Clear climax ✓</span>
            )}
          </p>
        </div>

        {/* Recommendations */}
        {showRecommendations && data.recommendations.length > 0 && (
          <Collapsible defaultOpen={data.warnings.length > 0}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" className="w-full justify-between">
                <span className="text-sm font-medium">
                  Recommendations ({data.recommendations.length})
                </span>
                <ChevronDown className="h-4 w-4" />
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2 space-y-2">
              <ul className="space-y-2 text-sm">
                {data.recommendations.map((recommendation, index) => (
                  <li key={index} className="flex gap-2 rounded-md border bg-card p-3">
                    <span className="text-primary">•</span>
                    <span className="text-muted-foreground">{recommendation}</span>
                  </li>
                ))}
              </ul>
            </CollapsibleContent>
          </Collapsible>
        )}
      </CardContent>
    </Card>
  );
}

// Import React for useState
import React from 'react';
