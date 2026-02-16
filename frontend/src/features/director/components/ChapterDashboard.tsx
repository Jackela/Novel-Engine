/**
 * ChapterDashboard - Director Mode chapter-level metrics and pacing visualization.
 *
 * Why: Provides authors with an overview of their chapter's narrative rhythm
 * through the PacingGraph, along with key statistics. This is the central
 * hub for Director Mode chapter analysis features.
 *
 * Future: Will be expanded with:
 * - Conflict tracking (DIR-046)
 * - Chapter health metrics (DIR-056)
 * - Beat summary statistics
 */
import { cn } from '@/lib/utils';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { PacingGraph } from './PacingGraph';

interface ChapterDashboardProps {
  /** Story ID */
  storyId: string;
  /** Chapter ID */
  chapterId: string;
  /** Chapter title for display */
  chapterTitle?: string;
  /** Optional CSS class name */
  className?: string;
}

/**
 * ChapterDashboard - Director Mode chapter overview.
 *
 * Features:
 * - Pacing Graph showing tension/energy curves across scenes
 * - Summary statistics (average tension, energy, ranges)
 * - Pacing issues detection and suggestions
 *
 * Usage:
 * ```tsx
 * <ChapterDashboard
 *   storyId="story-123"
 *   chapterId="chapter-456"
 *   chapterTitle="Chapter 1: The Beginning"
 * />
 * ```
 */
export function ChapterDashboard({
  storyId,
  chapterId,
  chapterTitle,
  className,
}: ChapterDashboardProps) {
  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div>
        <h2 className="text-xl font-semibold">{chapterTitle || 'Chapter Dashboard'}</h2>
        <p className="text-sm text-muted-foreground">Director Mode - Pacing Analysis</p>
      </div>

      {/* Pacing Graph Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Pacing Overview</CardTitle>
          <CardDescription>
            Visualize tension and energy flow across scenes in this chapter. Hover over
            points to see scene details.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <PacingGraph
            storyId={storyId}
            chapterId={chapterId}
            height={350}
            showIssues={true}
          />
        </CardContent>
      </Card>

      {/* Placeholder for future Director Mode features */}
      {/*
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Conflict Tracker</CardTitle>
          <CardDescription>
            Coming in DIR-046: Track conflicts and their resolution.
          </CardDescription>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Chapter Health</CardTitle>
          <CardDescription>
            Coming in DIR-056: Structural analysis and recommendations.
          </CardDescription>
        </CardHeader>
      </Card>
      */}
    </div>
  );
}

export default ChapterDashboard;
