/**
 * WorldTimeline Component (SIM-007)
 *
 * Displays historical events in a vertical timeline format with
 * filtering capabilities. Follows MemoryTimeline pattern for styling.
 *
 * Features:
 * - Vertical timeline with date grouping
 * - Filter controls for event_type and impact_scope
 * - Expandable descriptions (max 200 chars with expand link)
 * - Accessible with ARIA roles and keyboard navigation
 */
import { useState, useMemo } from 'react';
import { History, Filter, X } from 'lucide-react';
import { Badge } from '@/shared/components/ui/Badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/shared/components/ui/Skeleton';
import { useWorldEvents } from '@/lib/api/eventsApi';
import type { HistoryEventResponse, EventFilterParams } from '@/types/schemas';

type Props = {
  worldId: string | undefined;
  filters?: EventFilterParams;
};

// Impact scope badge colors
const IMPACT_SCOPE_COLORS: Record<string, string> = {
  local: 'bg-zinc-500/20 text-zinc-700 dark:text-zinc-300',
  regional: 'bg-blue-500/20 text-blue-700 dark:text-blue-300',
  global: 'bg-purple-500/20 text-purple-700 dark:text-purple-300',
};

// Event type badge colors (subset of common types)
const EVENT_TYPE_COLORS: Record<string, string> = {
  war: 'bg-red-500/20 text-red-700 dark:text-red-300',
  battle: 'bg-red-500/20 text-red-700 dark:text-red-300',
  treaty: 'bg-green-500/20 text-green-700 dark:text-green-300',
  discovery: 'bg-amber-500/20 text-amber-700 dark:text-amber-300',
  trade: 'bg-emerald-500/20 text-emerald-700 dark:text-emerald-300',
  political: 'bg-indigo-500/20 text-indigo-700 dark:text-indigo-300',
  natural: 'bg-orange-500/20 text-orange-700 dark:text-orange-300',
  death: 'bg-gray-500/20 text-gray-700 dark:text-gray-300',
  birth: 'bg-pink-500/20 text-pink-700 dark:text-pink-300',
  marriage: 'bg-rose-500/20 text-rose-700 dark:text-rose-300',
};

const MAX_DESCRIPTION_LENGTH = 200;

type EventCardProps = {
  event: HistoryEventResponse;
};

function EventCard({ event }: EventCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const shouldTruncate = event.description.length > MAX_DESCRIPTION_LENGTH;
  const displayDescription =
    shouldTruncate && !isExpanded
      ? event.description.slice(0, MAX_DESCRIPTION_LENGTH) + '...'
      : event.description;

  const typeColorClass =
    EVENT_TYPE_COLORS[event.event_type.toLowerCase()] ||
    'bg-slate-500/20 text-slate-700 dark:text-slate-300';

  const impactColorClass =
    IMPACT_SCOPE_COLORS[event.impact_scope?.toLowerCase() || 'local'];

  return (
    <article
      className="relative rounded-lg border border-border bg-card p-4 transition-colors hover:border-border/80"
      aria-labelledby={`event-title-${event.id}`}
    >
      <div className="space-y-3">
        {/* Header: Date and badges */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <History className="h-3 w-3" aria-hidden="true" />
            <span>{event.date_description}</span>
          </div>
          <div className="flex items-center gap-1">
            {/* Event type badge */}
            <Badge variant="outline" className={typeColorClass}>
              {event.event_type}
            </Badge>
            {/* Impact scope badge */}
            {event.impact_scope && (
              <Badge
                variant="outline"
                className={impactColorClass}
                aria-label={`Impact: ${event.impact_scope}`}
              >
                {event.impact_scope}
              </Badge>
            )}
          </div>
        </div>

        {/* Title */}
        <h3
          id={`event-title-${event.id}`}
          className="text-sm font-medium leading-tight"
        >
          {event.name}
        </h3>

        {/* Description with expand/collapse */}
        <div className="text-sm leading-relaxed text-muted-foreground">
          {displayDescription}
          {shouldTruncate && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="ml-1 text-primary underline-offset-2 hover:underline"
              aria-expanded={isExpanded}
              aria-label={isExpanded ? 'Show less' : 'Show more'}
            >
              {isExpanded ? 'Show less' : 'Show more'}
            </button>
          )}
        </div>

        {/* Key figures */}
        {event.key_figures.length > 0 && (
          <div className="flex flex-wrap items-center gap-1 text-xs">
            <span className="text-muted-foreground">Key figures:</span>
            {event.key_figures.slice(0, 3).map((figure, idx) => (
              <Badge key={idx} variant="secondary" className="text-xs">
                {figure}
              </Badge>
            ))}
            {event.key_figures.length > 3 && (
              <span className="text-muted-foreground">
                +{event.key_figures.length - 3} more
              </span>
            )}
          </div>
        )}
      </div>
    </article>
  );
}

type FilterControlsProps = {
  filters: EventFilterParams;
  onFiltersChange: (filters: EventFilterParams) => void;
  onClear: () => void;
};

function FilterControls({ filters, onFiltersChange, onClear }: FilterControlsProps) {
  const hasActiveFilters = filters.event_type || filters.impact_scope;

  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* Event type filter */}
      <div className="flex items-center gap-1">
        <label
          htmlFor="event-type-filter"
          className="text-xs text-muted-foreground"
        >
          Type:
        </label>
        <Select
          value={filters.event_type || 'all'}
          onValueChange={(value) =>
            onFiltersChange({
              ...filters,
              event_type: value === 'all' ? undefined : value,
              page: 1,
            })
          }
        >
          <SelectTrigger
            id="event-type-filter"
            className="h-7 w-32 text-xs"
            aria-label="Filter by event type"
          >
            <SelectValue placeholder="All types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All types</SelectItem>
            <SelectItem value="war">War</SelectItem>
            <SelectItem value="battle">Battle</SelectItem>
            <SelectItem value="treaty">Treaty</SelectItem>
            <SelectItem value="discovery">Discovery</SelectItem>
            <SelectItem value="trade">Trade</SelectItem>
            <SelectItem value="political">Political</SelectItem>
            <SelectItem value="natural">Natural</SelectItem>
            <SelectItem value="death">Death</SelectItem>
            <SelectItem value="birth">Birth</SelectItem>
            <SelectItem value="marriage">Marriage</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Impact scope filter */}
      <div className="flex items-center gap-1">
        <label
          htmlFor="impact-scope-filter"
          className="text-xs text-muted-foreground"
        >
          Scope:
        </label>
        <Select
          value={filters.impact_scope || 'all'}
          onValueChange={(value) =>
            onFiltersChange({
              ...filters,
              impact_scope: value === 'all' ? undefined : value,
              page: 1,
            })
          }
        >
          <SelectTrigger
            id="impact-scope-filter"
            className="h-7 w-32 text-xs"
            aria-label="Filter by impact scope"
          >
            <SelectValue placeholder="All scopes" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All scopes</SelectItem>
            <SelectItem value="local">Local</SelectItem>
            <SelectItem value="regional">Regional</SelectItem>
            <SelectItem value="global">Global</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Clear filters button */}
      {hasActiveFilters && (
        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-2 text-xs"
          onClick={onClear}
          aria-label="Clear all filters"
        >
          <X className="mr-1 h-3 w-3" />
          Clear
        </Button>
      )}
    </div>
  );
}

function TimelineSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="rounded-lg border border-border p-4">
          <div className="flex items-center justify-between">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-5 w-16" />
          </div>
          <Skeleton className="mt-3 h-4 w-3/4" />
          <Skeleton className="mt-2 h-12 w-full" />
        </div>
      ))}
    </div>
  );
}

export default function WorldTimeline({ worldId, filters: externalFilters }: Props) {
  const [internalFilters, setInternalFilters] = useState<EventFilterParams>({
    page: 1,
    page_size: 20,
    ...externalFilters,
  });

  // Merge external and internal filters
  const activeFilters = {
    ...internalFilters,
    ...externalFilters,
  };

  const { data, isLoading, isError, refetch } = useWorldEvents(worldId, activeFilters);

  const events = useMemo(() => data?.events ?? [], [data]);

  const handleFiltersChange = (newFilters: EventFilterParams) => {
    setInternalFilters(newFilters);
  };

  const handleClearFilters = () => {
    setInternalFilters({
      page: 1,
      page_size: 20,
    });
  };

  // Empty state
  if (!isLoading && !isError && events.length === 0) {
    return (
      <Card data-testid="world-timeline" data-state="empty">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <History className="h-5 w-5" aria-hidden="true" />
            Historical Events
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
            <History className="mb-2 h-8 w-8 opacity-50" aria-hidden="true" />
            <p className="text-sm">No events yet.</p>
            <p className="mt-1 text-xs">
              Events will appear as the simulation progresses.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Error state
  if (isError) {
    return (
      <Card data-testid="world-timeline" data-state="error">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <History className="h-5 w-5" aria-hidden="true" />
            Historical Events
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-destructive">
            <History className="mb-2 h-8 w-8 opacity-50" aria-hidden="true" />
            <p className="text-sm">Failed to load events.</p>
            <Button
              variant="outline"
              size="sm"
              className="mt-3"
              onClick={() => refetch()}
              aria-label="Retry loading events"
            >
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid="world-timeline" data-state={isLoading ? 'loading' : 'success'}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <History className="h-5 w-5" aria-hidden="true" />
            Historical Events
          </CardTitle>
          {data && (
            <span className="text-sm text-muted-foreground">
              {data.total_count} {data.total_count === 1 ? 'event' : 'events'}
            </span>
          )}
        </div>
        {/* Filter controls */}
        <div className="mt-2 flex items-center gap-2">
          <Filter
            className="h-4 w-4 text-muted-foreground"
            aria-hidden="true"
          />
          <FilterControls
            filters={activeFilters}
            onFiltersChange={handleFiltersChange}
            onClear={handleClearFilters}
          />
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <TimelineSkeleton />
        ) : (
          <ScrollArea className="h-[400px] pr-4">
            <div
              className="space-y-3"
              role="feed"
              aria-label="Historical events timeline"
            >
              {events.map((event) => (
                <EventCard key={event.id} event={event} />
              ))}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}
