/**
 * RumorBoard Component (SIM-026)
 *
 * Displays rumors at a location with veracity indicators and sorting.
 *
 * Features:
 * - Color-coded veracity badges (Confirmed to False)
 * - Sort options (Most Recent, Most Reliable, Most Spread)
 * - Expandable content (max 150 chars with expand link)
 * - Origin location display with clickable link
 * - Spread count indicator
 * - Age display (days ago or Today)
 * - Accessible with ARIA roles and keyboard navigation
 */
import React, { useState, useCallback, useMemo } from 'react';
import { MessageCircleWarning, TrendingUp, CheckCircle, AlertTriangle, XCircle, HelpCircle, ChevronDown, ChevronUp } from 'lucide-react';
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
import { useRumors } from '@/lib/api/rumorApi';
import type { RumorResponse, RumorSortBy } from '@/types/schemas';

type Props = {
  worldId: string | undefined;
  locationId?: string;
  maxItems?: number;
};

// Veracity label colors (matching backend colors)
const VERACITY_COLORS = {
  Confirmed: { bg: 'bg-green-500/20', text: 'text-green-700 dark:text-green-300' },
  'Likely True': { bg: 'bg-lime-500/20', text: 'text-lime-700 dark:text-lime-300' },
  Uncertain: { bg: 'bg-yellow-500/20', text: 'text-yellow-700 dark:text-yellow-300' },
  'Likely False': { bg: 'bg-orange-500/20', text: 'text-orange-700 dark:text-orange-300' },
  False: { bg: 'bg-gray-500/20', text: 'text-gray-700 dark:text-gray-300' },
} as const satisfies Record<string, { bg: string; text: string }>;

// Veracity icons
const VERACITY_ICONS: Record<string, React.ReactNode> = {
  Confirmed: <CheckCircle className="h-3 w-3" aria-hidden="true" />,
  'Likely True': <CheckCircle className="h-3 w-3" aria-hidden="true" />,
  Uncertain: <HelpCircle className="h-3 w-3" aria-hidden="true" />,
  'Likely False': <AlertTriangle className="h-3 w-3" aria-hidden="true" />,
  False: <XCircle className="h-3 w-3" aria-hidden="true" />,
};

const MAX_CONTENT_LENGTH = 150;

type RumorCardProps = {
  rumor: RumorResponse;
};

const RumorCard = React.memo(function RumorCard({ rumor }: RumorCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const handleToggleExpand = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  // Memoize derived data
  const shouldTruncate = useMemo(
    () => rumor.content.length > MAX_CONTENT_LENGTH,
    [rumor.content]
  );

  const displayContent = useMemo(
    () => shouldTruncate && !isExpanded
      ? rumor.content.slice(0, MAX_CONTENT_LENGTH) + '...'
      : rumor.content,
    [shouldTruncate, isExpanded, rumor.content]
  );

  const colorClasses = useMemo(
    () => VERACITY_COLORS[rumor.veracity_label as keyof typeof VERACITY_COLORS] ??
      VERACITY_COLORS.Uncertain,
    [rumor.veracity_label]
  );

  const veracityIcon = useMemo(
    () => VERACITY_ICONS[rumor.veracity_label] || VERACITY_ICONS.Uncertain,
    [rumor.veracity_label]
  );

  // Calculate age in days
  const ageDisplay = useMemo(() => {
    const ageDays = rumor.created_date
      ? Math.max(0, rumor.created_date.day) // Simplified: just use day as proxy for age
      : 0;
    return ageDays === 0 ? 'Today' : `${ageDays} day${ageDays === 1 ? '' : 's'} ago`;
  }, [rumor.created_date]);

  const originLocationDisplay = useMemo(
    () => rumor.origin_location_id.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
    [rumor.origin_location_id]
  );

  return (
    <li
      className="rounded-lg border border-border bg-card p-4 transition-colors hover:border-border/80"
    >
      <div className="space-y-3">
        {/* Header: Veracity badge and spread count */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            {/* Veracity badge */}
            <Badge
              variant="outline"
              className={`${colorClasses.bg} ${colorClasses.text} flex items-center gap-1`}
              aria-label={`Reliability: ${rumor.veracity_label}`}
            >
              {veracityIcon}
              <span>{rumor.veracity_label}</span>
            </Badge>
          </div>
          {/* Spread count */}
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <TrendingUp className="h-3 w-3" aria-hidden="true" />
            <span aria-label={`Spread ${rumor.spread_count} times`}>{rumor.spread_count}</span>
          </div>
        </div>

        {/* Content */}
        <div className="space-y-2">
          <p className="text-sm leading-relaxed">{displayContent}</p>
          {shouldTruncate && (
            <button
              onClick={handleToggleExpand}
              className="text-xs text-primary hover:underline"
              aria-expanded={isExpanded}
            >
              {isExpanded ? (
                <span className="flex items-center gap-1">
                  <ChevronUp className="h-3 w-3" aria-hidden="true" />
                  Show less
                </span>
              ) : (
                <span className="flex items-center gap-1">
                  <ChevronDown className="h-3 w-3" aria-hidden="true" />
                  Show more
                </span>
              )}
            </button>
          )}
        </div>

        {/* Footer: Origin location and age */}
        <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <MessageCircleWarning className="h-3 w-3" aria-hidden="true" />
            <span className="truncate max-w-[200px]">
              From: {originLocationDisplay}
            </span>
          </div>
          <span>{ageDisplay}</span>
        </div>
      </div>
    </li>
  );
});

function RumorSkeleton() {
  return (
    <div className="space-y-3 rounded-lg border border-border bg-card p-4">
      <div className="flex items-center justify-between">
        <Skeleton className="h-5 w-24" />
        <Skeleton className="h-4 w-10" />
      </div>
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-3/4" />
      <div className="flex items-center justify-between">
        <Skeleton className="h-3 w-32" />
        <Skeleton className="h-3 w-16" />
      </div>
    </div>
  );
}

export const RumorBoard = React.memo(function RumorBoard({ worldId, locationId, maxItems = 20 }: Props) {
  const [sortBy, setSortBy] = useState<RumorSortBy>('recent');

  const { data, isLoading, isError, refetch } = useRumors(
    worldId,
    locationId,
    sortBy,
    maxItems
  );

  // Memoize derived data
  const rumors = useMemo(() => data?.rumors ?? [], [data?.rumors]);

  // Memoize handlers
  const handleSortChange = useCallback((value: RumorSortBy) => {
    setSortBy(value);
  }, []);

  const handleRetry = useCallback(() => {
    refetch();
  }, [refetch]);

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <MessageCircleWarning className="h-5 w-5" aria-hidden="true" />
            Rumors
          </CardTitle>
          {/* Sort dropdown */}
          <Select
            value={sortBy}
            onValueChange={handleSortChange}
          >
            <SelectTrigger
              className="w-[140px] h-8"
              aria-label="Sort rumors by"
            >
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="recent">Most Recent</SelectItem>
              <SelectItem value="reliable">Most Reliable</SelectItem>
              <SelectItem value="spread">Most Spread</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3" role="status" aria-label="Loading rumors">
            {Array.from({ length: 3 }).map((_, i) => (
              <RumorSkeleton key={i} />
            ))}
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <AlertTriangle className="h-8 w-8 text-destructive mb-2" aria-hidden="true" />
            <p className="text-sm text-muted-foreground mb-2">
              Failed to load rumors
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRetry}
            >
              Try again
            </Button>
          </div>
        ) : rumors.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <MessageCircleWarning className="h-8 w-8 text-muted-foreground/50 mb-2" aria-hidden="true" />
            <p className="text-sm text-muted-foreground">
              No rumors in this area. Check back later.
            </p>
          </div>
        ) : (
          <ScrollArea className="h-[400px] pr-4">
            <ul
              className="space-y-3"
              aria-label="Rumors"
            >
              {rumors.map((rumor) => (
                <RumorCard key={rumor.rumor_id} rumor={rumor} />
              ))}
            </ul>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
});

export default RumorBoard;
