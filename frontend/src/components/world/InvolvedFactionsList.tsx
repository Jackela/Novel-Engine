/**
 * InvolvedFactionsList Component
 *
 * Displays a list of involved factions as badges.
 * Extracted from WorldTimeline to reduce JSX nesting depth.
 */
import { Users } from 'lucide-react';
import { Badge } from '@/shared/components/ui/Badge';

interface InvolvedFactionsListProps {
  factionIds: string[];
}

function formatEntityId(id: string): string {
  return id.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export function InvolvedFactionsList({ factionIds }: InvolvedFactionsListProps) {
  return (
    <div className="flex items-start gap-2 text-xs">
      <Users className="h-3.5 w-3.5 text-muted-foreground mt-0.5" aria-hidden="true" />
      <div>
        <span className="text-muted-foreground">Involved factions:</span>
        <FactionsBadges factionIds={factionIds} />
      </div>
    </div>
  );
}

/**
 * Internal component for faction badges to keep nesting shallow.
 */
function FactionsBadges({ factionIds }: { factionIds: string[] }) {
  return (
    <div className="flex flex-wrap gap-1 mt-1">
      {factionIds.map((factionId, idx) => (
        <Badge key={idx} variant="secondary" className="text-xs">
          {formatEntityId(factionId)}
        </Badge>
      ))}
    </div>
  );
}
