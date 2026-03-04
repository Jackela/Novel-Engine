/**
 * WorldTimeline Component (W5 Events and Rumors / SIM-007)
 *
 * Displays historical events in a vertical chronological timeline format.
 * Events are sorted by date (newest first) and presented as expandable cards
 * with significance-based visual styling.
 *
 * Features:
 * - Vertical chronological list (newest first)
 * - Event cards with name, date_description, event_type badge
 * - Expandable details: description, involved factions/locations
 * - Significance-based color coding (4-tier system)
 * - Impact scope indicators
 * - Loading skeleton state
 * - Empty and error states
 * - Accessible with ARIA roles and keyboard navigation
 */
import React, { useState, useMemo, useCallback } from 'react';
import { History, ChevronDown, ChevronUp, AlertCircle } from 'lucide-react';
import { Badge } from '@/shared/components/ui/Badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/shared/components/ui/Skeleton';
import { useWorldEvents } from '@/lib/api/eventsApi';
import type { HistoryEventResponse } from '@/types/schemas';
import { EventCardDetails } from './EventCardDetails';

type Props = {
  worldId: string;
};

// Significance levels for styling
// Based on significance field (minor, moderate, major, epochal)
type SignificanceLevel = 'minor' | 'moderate' | 'major' | 'epochal';

interface SignificanceConfig {
  borderClass: string;
  badgeClass: string;
  indicatorClass: string;
  label: string;
}

// Significance-based styling (left border accent + badge)
const SIGNIFICANCE_STYLES: Record<SignificanceLevel, SignificanceConfig> = {
  minor: {
    borderClass: 'border-l-4 border-l-gray-400',
    badgeClass: 'bg-gray-500/20 text-gray-700 dark:text-gray-300',
    indicatorClass: 'bg-gray-400',
    label: 'Minor',
  },
  moderate: {
    borderClass: 'border-l-4 border-l-blue-400',
    badgeClass: 'bg-blue-500/20 text-blue-700 dark:text-blue-300',
    indicatorClass: 'bg-blue-400',
    label: 'Moderate',
  },
  major: {
    borderClass: 'border-l-4 border-l-amber-400',
    badgeClass: 'bg-amber-500/20 text-amber-700 dark:text-amber-300',
    indicatorClass: 'bg-amber-400',
    label: 'Major',
  },
  epochal: {
    borderClass: 'border-l-4 border-l-purple-500',
    badgeClass: 'bg-purple-500/20 text-purple-700 dark:text-purple-300',
    indicatorClass: 'bg-purple-500',
    label: 'Epochal',
  },
};

// Event type badge colors
const EVENT_TYPE_COLORS: Record<string, string> = {
  war: 'bg-red-500/20 text-red-700 dark:text-red-300 border-red-500/30',
  battle: 'bg-red-500/20 text-red-700 dark:text-red-300 border-red-500/30',
  treaty: 'bg-green-500/20 text-green-700 dark:text-green-300 border-green-500/30',
  discovery: 'bg-amber-500/20 text-amber-700 dark:text-amber-300 border-amber-500/30',
  trade: 'bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border-emerald-500/30',
  political: 'bg-indigo-500/20 text-indigo-700 dark:text-indigo-300 border-indigo-500/30',
  natural: 'bg-cyan-500/20 text-cyan-700 dark:text-cyan-300 border-cyan-500/30',
  death: 'bg-slate-500/20 text-slate-700 dark:text-slate-300 border-slate-500/30',
  birth: 'bg-pink-500/20 text-pink-700 dark:text-pink-300 border-pink-500/30',
  marriage: 'bg-rose-500/20 text-rose-700 dark:text-rose-300 border-rose-500/30',
  revolution: 'bg-orange-500/20 text-orange-700 dark:text-orange-300 border-orange-500/30',
  catastrophe: 'bg-red-600/20 text-red-800 dark:text-red-200 border-red-600/30',
  miracle: 'bg-yellow-500/20 text-yellow-700 dark:text-yellow-300 border-yellow-500/30',
  coronation: 'bg-violet-500/20 text-violet-700 dark:text-violet-300 border-violet-500/30',
  invasion: 'bg-red-500/20 text-red-700 dark:text-red-300 border-red-500/30',
  plague: 'bg-green-800/20 text-green-800 dark:text-green-200 border-green-800/30',
  festival: 'bg-fuchsia-500/20 text-fuchsia-700 dark:text-fuchsia-300 border-fuchsia-500/30',
};

const MAX_DESCRIPTION_LENGTH = 200;

/**
 * Parse significance level from event significance string.
 */
function getSignificanceLevel(significance: string): SignificanceLevel {
  const normalized = significance.toLowerCase().trim();
  if (normalized.includes('epochal') || normalized.includes('world')) return 'epochal';
  if (normalized.includes('major') || normalized.includes('great')) return 'major';
  if (normalized.includes('moderate') || normalized.includes('significant')) return 'moderate';
  return 'minor';
}

/**
 * Individual event card component.
 */
interface EventCardProps {
  event: HistoryEventResponse;
  isExpanded: boolean;
  onToggleExpand: () => void;
}

const EventCard = React.memo(function EventCard({
  event,
  isExpanded,
  onToggleExpand,
}: EventCardProps) {
  // Get significance-based styling
  const significanceLevel = getSignificanceLevel(event.significance);
  const significanceStyle = SIGNIFICANCE_STYLES[significanceLevel];

  // Event type styling
  const typeColorClass =
    EVENT_TYPE_COLORS[event.event_type.toLowerCase()] ||
    'bg-slate-500/20 text-slate-700 dark:text-slate-300 border-slate-500/30';

  // Content truncation
  const shouldTruncate = event.description.length > MAX_DESCRIPTION_LENGTH;
  const displayDescription = useMemo(
    () =>
      shouldTruncate && !isExpanded
        ? event.description.slice(0, MAX_DESCRIPTION_LENGTH) + '...'
        : event.description,
    [shouldTruncate, isExpanded, event.description]
  );



  return (
    <article
      className={`relative rounded-lg border border-border bg-card p-4 transition-all hover:shadow-sm ${significanceStyle.borderClass}`}
      aria-labelledby={`event-title-${event.id}`}
    >
      {/* Significance indicator dot */}
      <div
        className={`absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 rounded-r ${significanceStyle.indicatorClass}`}
        aria-hidden="true"
      />

      <div className="space-y-3 pl-2">
        {/* Header: Date and badges */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <History className="h-3.5 w-3.5" aria-hidden="true" />
            <span className="font-medium">{event.date_description}</span>
          </div>
          <div className="flex items-center gap-1.5 flex-wrap justify-end">
            {/* Event type badge */}
            <Badge variant="outline" className={`text-xs ${typeColorClass}`}>
              {event.event_type}
            </Badge>
            {/* Significance badge */}
            <Badge variant="outline" className={`text-xs ${significanceStyle.badgeClass}`}>
              {significanceStyle.label}
            </Badge>
          </div>
        </div>

        {/* Title */}
        <h3
          id={`event-title-${event.id}`}
          className="text-sm font-semibold leading-tight text-foreground"
        >
          {event.name}
        </h3>

        {/* Description with expand/collapse */}
        <div className="text-sm leading-relaxed text-muted-foreground">
          {displayDescription}
          {shouldTruncate && (
            <button
              onClick={onToggleExpand}
              className="inline-flex items-center gap-1 ml-1 text-xs text-primary hover:underline focus:outline-none focus:ring-2 focus:ring-primary/20 rounded px-1 -ml-1"
              aria-expanded={isExpanded}
              aria-label={isExpanded ? 'Show less' : 'Show more'}
            >
              {isExpanded ? (
                <>
                  <ChevronUp className="h-3 w-3" aria-hidden="true" />
                  Show less
                </>
              ) : (
                <>
                  <ChevronDown className="h-3 w-3" aria-hidden="true" />
                  Show more
                </>
              )}
            </button>
          )}
        </div>

        {/* Expanded details: Involved factions/locations */}
        <EventCardDetails event={event} isExpanded={isExpanded} />

        {/* Key figures (always visible if present) */}
        {event.key_figures && event.key_figures.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 text-xs pt-2 border-t border-border/30">
            <span className="text-muted-foreground">Key figures:</span>
            {event.key_figures.slice(0, 3).map((figure, idx) => (
              <Badge key={idx} variant="outline" className="text-xs">
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
});

/**
 * Loading skeleton for the timeline.
 */
function TimelineSkeleton() {
  return (
    <div className="space-y-4" role="status" aria-label="Loading events">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="rounded-lg border border-border bg-card p-4 space-y-3 border-l-4 border-l-gray-300"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Skeleton className="h-3.5 w-3.5" />
              <Skeleton className="h-4 w-24" />
            </div>
            <div className="flex gap-1.5">
              <Skeleton className="h-5 w-16" />
              <Skeleton className="h-5 w-14" />
            </div>
          </div>
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-2/3" />
        </div>
      ))}
    </div>
  );
}

/**
 * Empty state for when no events are available.
 */
function EmptyState() {
  return (
    <div
      className="flex flex-col items-center justify-center py-12 text-center px-4"
      role="status"
      aria-label="No events available"
    >
      <div className="rounded-full bg-muted p-4 mb-4">
        <History className="h-8 w-8 text-muted-foreground/60" aria-hidden="true" />
      </div>
      <p className="text-sm font-medium text-muted-foreground">No events yet.</p>
      <p className="mt-1 text-xs text-muted-foreground/70">
        Historical events will appear here as your world develops.
      </p>
    </div>
  );
}

/**
 * Error state with retry option.
 */
function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div
      className="flex flex-col items-center justify-center py-12 text-center px-4"
      role="alert"
      aria-label="Error loading events"
    >
      <div className="rounded-full bg-destructive/10 p-4 mb-4">
        <AlertCircle className="h-8 w-8 text-destructive" aria-hidden="true" />
      </div>
      <p className="text-sm font-medium text-destructive">Failed to load events</p>
      <p className="mt-1 text-xs text-muted-foreground mb-4">
        Something went wrong while fetching the timeline.
      </p>
      <Button variant="outline" size="sm" onClick={onRetry} aria-label="Retry loading events">
        Try again
      </Button>
    </div>
  );
}

/**
 * Main WorldTimeline component.
 */
export const WorldTimeline = React.memo(function WorldTimeline({ worldId }: Props) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const { data, isLoading, isError, refetch } = useWorldEvents(worldId, {
    page: 1,
    page_size: 50,
  });

  // Sort events by date (newest first)
  // Uses structured_date if available, otherwise falls back to string comparison
  const events = useMemo(() => {
    if (!data?.events) return [];
    return [...data.events].sort((a, b) => {
      // Try to use structured_date for sorting
      if (a.structured_date && b.structured_date) {
        const dateA =
          a.structured_date.year * 10000 +
          a.structured_date.month * 100 +
          a.structured_date.day;
        const dateB =
          b.structured_date.year * 10000 +
          b.structured_date.month * 100 +
          b.structured_date.day;
        return dateB - dateA; // Newest first
      }
      // Fall back to string comparison of date_description
      return b.date_description.localeCompare(a.date_description);
    });
  }, [data?.events]);

  // Toggle expand/collapse for an event
  const handleToggleExpand = useCallback((eventId: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(eventId)) {
        next.delete(eventId);
      } else {
        next.add(eventId);
      }
      return next;
    });
  }, []);

  const handleRetry = useCallback(() => {
    refetch();
  }, [refetch]);

  return (
    <Card className="h-full" data-testid="world-timeline">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-4">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <History className="h-5 w-5" aria-hidden="true" />
            World Timeline
          </CardTitle>
          {events.length > 0 && (
            <span className="text-xs text-muted-foreground">
              {events.length} {events.length === 1 ? 'event' : 'events'}
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <TimelineSkeleton />
        ) : isError ? (
          <ErrorState onRetry={handleRetry} />
        ) : events.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="space-y-4" role="list" aria-label="Historical events timeline">
            {events.map((event) => (
              <EventCard
                key={event.id}
                event={event}
                isExpanded={expandedIds.has(event.id)}
                onToggleExpand={() => handleToggleExpand(event.id)}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
});

export default WorldTimeline;
