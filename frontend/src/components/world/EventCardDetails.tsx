/**
 * EventCardDetails Component
 *
 * Displays expanded event details including involved factions and locations.
 * Extracted from WorldTimeline to reduce JSX nesting depth.
 */
import type { HistoryEventResponse } from '@/types/schemas';
import { InvolvedFactionsList } from './InvolvedFactionsList';
import { InvolvedLocationsList } from './InvolvedLocationsList';

interface EventCardDetailsProps {
  event: HistoryEventResponse;
  isExpanded: boolean;
}

export function EventCardDetails({ event, isExpanded }: EventCardDetailsProps) {
  const involvedFactions = event.faction_ids?.length || 0;
  const involvedLocations = event.location_ids?.length || 0;
  const hasInvolvedEntities = involvedFactions > 0 || involvedLocations > 0;

  if (!isExpanded || !hasInvolvedEntities) {
    return null;
  }

  return (
    <div className="pt-3 border-t border-border/50 space-y-2">
      {involvedFactions > 0 && event.faction_ids && (
        <InvolvedFactionsList factionIds={event.faction_ids} />
      )}
      {involvedLocations > 0 && event.location_ids && (
        <InvolvedLocationsList locationIds={event.location_ids} />
      )}
    </div>
  );
}
