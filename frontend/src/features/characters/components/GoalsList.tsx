import { CheckCircle2, Circle, XCircle, AlertTriangle, Flame } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import type { CharacterGoal } from '@/types/schemas';

type Props = {
  goals: CharacterGoal[];
};

/**
 * Map urgency to visual indicator.
 * LOW = no indicator, MEDIUM = subtle, HIGH = warning, CRITICAL = danger
 */
function UrgencyIndicator({ urgency }: { urgency: CharacterGoal['urgency'] }) {
  if (urgency === 'LOW') return null;

  const config = {
    MEDIUM: { icon: Circle, className: 'text-muted-foreground', label: 'Medium' },
    HIGH: { icon: AlertTriangle, className: 'text-amber-500', label: 'High' },
    CRITICAL: { icon: Flame, className: 'text-red-500', label: 'Critical' },
  };

  const { icon: Icon, className, label } = config[urgency];

  return (
    <span title={`${label} urgency`}>
      <Icon className={cn('h-4 w-4', className)} />
    </span>
  );
}

/**
 * Status icon and checkbox-like appearance.
 */
function StatusIcon({ status }: { status: CharacterGoal['status'] }) {
  const config = {
    ACTIVE: { icon: Circle, className: 'text-muted-foreground' },
    COMPLETED: { icon: CheckCircle2, className: 'text-green-500' },
    FAILED: { icon: XCircle, className: 'text-red-500' },
  };

  const { icon: Icon, className } = config[status];

  return <Icon className={cn('h-5 w-5 flex-shrink-0', className)} />;
}

/**
 * Single goal item in the list.
 */
function GoalItem({ goal }: { goal: CharacterGoal }) {
  const isResolved = goal.status !== 'ACTIVE';

  return (
    <div
      className={cn(
        'flex items-start gap-3 rounded-lg border p-3 transition-colors',
        isResolved && 'bg-muted/50'
      )}
    >
      <StatusIcon status={goal.status} />

      <div className="flex-1 min-w-0">
        <p
          className={cn(
            'text-sm leading-relaxed',
            isResolved && 'line-through text-muted-foreground'
          )}
        >
          {goal.description}
        </p>

        <div className="mt-2 flex items-center gap-2">
          <Badge
            variant="outline"
            className={cn(
              'text-xs',
              goal.status === 'COMPLETED' && 'border-green-500 text-green-500',
              goal.status === 'FAILED' && 'border-red-500 text-red-500'
            )}
          >
            {goal.status}
          </Badge>

          {goal.is_urgent && (
            <Badge variant="destructive" className="text-xs">
              Urgent
            </Badge>
          )}

          <UrgencyIndicator urgency={goal.urgency} />
        </div>
      </div>
    </div>
  );
}

/**
 * GoalsList displays a scrollable list of character goals.
 *
 * Features:
 * - Checkbox-style status indicators (circle, check, X)
 * - Strikethrough for completed/failed goals
 * - Urgency badges for high-priority goals
 * - Grouped by status: active first, then resolved
 */
export default function GoalsList({ goals }: Props) {
  if (!goals || goals.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-muted-foreground">
        No goals defined for this character.
      </div>
    );
  }

  // Sort: active goals first (by urgency descending), then resolved (by completion date)
  const urgencyOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
  const sortedGoals = [...goals].sort((a, b) => {
    // Active goals come first
    if (a.status === 'ACTIVE' && b.status !== 'ACTIVE') return -1;
    if (a.status !== 'ACTIVE' && b.status === 'ACTIVE') return 1;

    // Among active goals, sort by urgency
    if (a.status === 'ACTIVE' && b.status === 'ACTIVE') {
      return urgencyOrder[a.urgency] - urgencyOrder[b.urgency];
    }

    // Among resolved goals, sort by completion date (newest first)
    const aDate = a.completed_at ? new Date(a.completed_at).getTime() : 0;
    const bDate = b.completed_at ? new Date(b.completed_at).getTime() : 0;
    return bDate - aDate;
  });

  const activeGoals = sortedGoals.filter((g) => g.status === 'ACTIVE');
  const resolvedGoals = sortedGoals.filter((g) => g.status !== 'ACTIVE');

  return (
    <ScrollArea className="h-80">
      <div className="space-y-4 pr-4">
        {/* Active Goals Section */}
        {activeGoals.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-muted-foreground">
              Active Goals ({activeGoals.length})
            </h4>
            <div className="space-y-2">
              {activeGoals.map((goal) => (
                <GoalItem key={goal.goal_id} goal={goal} />
              ))}
            </div>
          </div>
        )}

        {/* Resolved Goals Section */}
        {resolvedGoals.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-muted-foreground">
              Resolved ({resolvedGoals.length})
            </h4>
            <div className="space-y-2">
              {resolvedGoals.map((goal) => (
                <GoalItem key={goal.goal_id} goal={goal} />
              ))}
            </div>
          </div>
        )}
      </div>
    </ScrollArea>
  );
}
