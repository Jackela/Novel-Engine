/**
 * RelationshipStatusBars - Sims-style relationship progress bars
 *
 * Why: Provides visual feedback for relationship metrics (Trust and Romance).
 * Uses color coding from Red (Hate/0) to Green (Love/100), similar to The Sims.
 */
import { Heart, Shield } from 'lucide-react';
import { Progress } from '@/shared/components/ui';
import { cn } from '@/lib/utils';

export interface RelationshipStatusBarsProps {
  /** Trust level (0-100). 0 = distrust, 50 = neutral, 100 = complete trust */
  trust: number;
  /** Romance level (0-100). 0 = none, 100 = deep romantic connection */
  romance: number;
  /** Optional CSS class name */
  className?: string;
  /** Compact mode for smaller displays */
  compact?: boolean;
}

/**
 * Get color class based on value (0-100).
 * Color scale: Red (0-30) -> Yellow (31-50) -> Green (51-100)
 */
function getStatusColor(value: number): string {
  if (value <= 30) {
    return 'bg-red-500';
  }
  if (value <= 50) {
    return 'bg-amber-500';
  }
  if (value <= 70) {
    return 'bg-lime-500';
  }
  return 'bg-green-500';
}

/**
 * Get text label for trust level.
 */
function getTrustLabel(value: number): string {
  if (value <= 20) return 'Distrusted';
  if (value <= 40) return 'Wary';
  if (value <= 60) return 'Neutral';
  if (value <= 80) return 'Trusted';
  return 'Complete Trust';
}

/**
 * Get text label for romance level.
 */
function getRomanceLabel(value: number): string {
  if (value === 0) return 'None';
  if (value <= 20) return 'Acquaintance';
  if (value <= 40) return 'Friendship';
  if (value <= 60) return 'Affection';
  if (value <= 80) return 'Love';
  return 'Soulmates';
}

/**
 * RelationshipStatusBars displays Trust and Romance as Sims-style progress bars.
 * Color coding helps quickly understand the relationship state:
 * - Red (0-30): Negative/Poor
 * - Yellow (31-50): Cautious/Neutral
 * - Lime (51-70): Positive
 * - Green (71-100): Excellent
 */
export function RelationshipStatusBars({
  trust,
  romance,
  className,
  compact = false,
}: RelationshipStatusBarsProps) {
  const trustColor = getStatusColor(trust);
  const romanceColor = getStatusColor(romance);

  if (compact) {
    return (
      <div className={cn('space-y-2', className)}>
        <div className="flex items-center gap-2">
          <Shield className="h-3 w-3 text-muted-foreground" />
          <Progress
            value={trust}
            className="h-1.5 flex-1"
            indicatorClassName={trustColor}
          />
          <span className="w-8 text-right text-xs text-muted-foreground">{trust}</span>
        </div>
        <div className="flex items-center gap-2">
          <Heart className="h-3 w-3 text-muted-foreground" />
          <Progress
            value={romance}
            className="h-1.5 flex-1"
            indicatorClassName={romanceColor}
          />
          <span className="w-8 text-right text-xs text-muted-foreground">
            {romance}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Trust Bar */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">Trust</span>
          </div>
          <span className="text-sm text-muted-foreground">
            {trust}% - {getTrustLabel(trust)}
          </span>
        </div>
        <Progress value={trust} className="h-2" indicatorClassName={trustColor} />
      </div>

      {/* Romance Bar */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Heart className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">Romance</span>
          </div>
          <span className="text-sm text-muted-foreground">
            {romance}% - {getRomanceLabel(romance)}
          </span>
        </div>
        <Progress value={romance} className="h-2" indicatorClassName={romanceColor} />
      </div>
    </div>
  );
}

export default RelationshipStatusBars;
