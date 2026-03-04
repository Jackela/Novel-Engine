/**
 * InvolvedLocationsList Component
 *
 * Displays a list of involved locations as badges.
 * Extracted from WorldTimeline to reduce JSX nesting depth.
 */
import { MapPin } from 'lucide-react';
import { Badge } from '@/shared/components/ui/Badge';

interface InvolvedLocationsListProps {
  locationIds: string[];
}

function formatEntityId(id: string): string {
  return id.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export function InvolvedLocationsList({ locationIds }: InvolvedLocationsListProps) {
  return (
    <div className="flex items-start gap-2 text-xs">
      <MapPin className="h-3.5 w-3.5 text-muted-foreground mt-0.5" aria-hidden="true" />
      <div>
        <span className="text-muted-foreground">Locations:</span>
        <LocationsBadges locationIds={locationIds} />
      </div>
    </div>
  );
}

/**
 * Internal component for location badges to keep nesting shallow.
 */
function LocationsBadges({ locationIds }: { locationIds: string[] }) {
  return (
    <div className="flex flex-wrap gap-1 mt-1">
      {locationIds.map((locationId, idx) => (
        <Badge key={idx} variant="secondary" className="text-xs">
          {formatEntityId(locationId)}
        </Badge>
      ))}
    </div>
  );
}
