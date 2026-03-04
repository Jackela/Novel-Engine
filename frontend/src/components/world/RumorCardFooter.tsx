/**
 * RumorCardFooter Component
 *
 * Displays the footer section of a rumor card with days circulating
 * and origin type indicator.
 * Extracted from TavernBoard to reduce JSX nesting depth.
 */
import { Clock } from 'lucide-react';
import { Badge } from '@/shared/components/ui/Badge';
import type { RumorResponse } from '@/types/schemas';

interface RumorCardFooterProps {
  rumor: RumorResponse;
}

export function RumorCardFooter({ rumor }: RumorCardFooterProps) {
  const daysCirculating = calculateDaysCirculating(rumor);
  const originLabel = getOriginLabel(rumor.origin_type);

  return (
    <div className="flex items-center justify-between gap-2 pt-2 border-t border-border/50">
      <CirculatingIndicator days={daysCirculating} />
      <OriginBadge label={originLabel} />
    </div>
  );
}

/**
 * Calculate days circulating from rumor data.
 */
function calculateDaysCirculating(rumor: RumorResponse): number {
  if (!rumor.created_date) return 0;
  // Simplified: use spread_count as proxy for circulation time
  // In a real implementation, compare with current world date
  return rumor.spread_count > 0 ? Math.max(1, rumor.spread_count) : 0;
}

/**
 * Get human-readable origin label from origin type.
 */
function getOriginLabel(originType: string): string {
  switch (originType) {
    case 'player':
      return 'From Traveler';
    case 'npc':
      return 'From Locals';
    case 'event':
      return 'From Events';
    default:
      return 'Unknown Source';
  }
}

/**
 * Days circulating indicator component.
 */
function CirculatingIndicator({ days }: { days: number }) {
  const label =
    days === 0 ? 'Just posted' : `${days} day${days === 1 ? '' : 's'} circulating`;

  return (
    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
      <Clock className="h-3.5 w-3.5" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

/**
 * Origin type badge component.
 */
function OriginBadge({ label }: { label: string }) {
  return (
    <Badge variant="secondary" className="text-xs px-1.5 py-0.5">
      {label}
    </Badge>
  );
}
