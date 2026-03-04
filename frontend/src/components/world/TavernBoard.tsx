/**
 * TavernBoard Component (W5 Events and Rumors)
 *
 * Displays rumors for a specific location with truth value visual indicators.
 * The "tavern board" metaphor presents rumors as if they were posted on a
 * physical notice board in a tavern, with visual cues about their reliability.
 *
 * Features:
 * - Rumor cards with content preview and expand/collapse
 * - Truth value color coding (5-tier system)
 * - Days circulating indicator
 * - Sort options (recent, reliable, spread)
 * - Empty state with tavern-themed messaging
 * - Loading skeleton state
 * - Accessible with ARIA roles and keyboard navigation
 */
import React, { useState, useMemo, useCallback } from 'react';
import {
  MessageCircleWarning,
  TrendingUp,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/shared/components/ui/Skeleton';
import { useLocationRumors } from '@/lib/api/rumorApi';
import type { RumorResponse, RumorSortBy } from '@/types/schemas';
import { RumorVeracityBadge } from './RumorVeracityBadge';
import { RumorCardFooter } from './RumorCardFooter';

type Props = {
  worldId: string;
  locationId: string;
  maxItems?: number;
};

const MAX_CONTENT_LENGTH = 150;

/**
 * Rumor card header component with veracity badge and spread count.
 */
interface RumorCardHeaderProps {
  rumor: RumorResponse;
}

function RumorCardHeader({ rumor }: RumorCardHeaderProps) {
  return (
    <div className="flex items-start justify-between gap-2">
      <div className="flex items-center gap-2">
        <RumorVeracityBadge truthValue={rumor.truth_value} />
        <TruthPercentageIndicator truthValue={rumor.truth_value} />
      </div>
      <SpreadCountIndicator spreadCount={rumor.spread_count} />
    </div>
  );
}

/**
 * Truth percentage indicator component.
 */
function TruthPercentageIndicator({ truthValue }: { truthValue: number }) {
  return (
    <span
      className="text-xs text-muted-foreground"
      aria-label={`${truthValue}% true`}
    >
      {truthValue}%
    </span>
  );
}

/**
 * Spread count indicator component.
 */
function SpreadCountIndicator({ spreadCount }: { spreadCount: number }) {
  return (
    <div
      className="flex items-center gap-1 text-xs text-muted-foreground"
      aria-label={`Spread ${spreadCount} times`}
    >
      <TrendingUp className="h-3.5 w-3.5" aria-hidden="true" />
      <span>{spreadCount}</span>
    </div>
  );
}

/**
 * Individual rumor card component.
 */
interface RumorCardProps {
  rumor: RumorResponse;
  isExpanded: boolean;
  onToggleExpand: () => void;
}

const RumorCard = React.memo(function RumorCard({
  rumor,
  isExpanded,
  onToggleExpand,
}: RumorCardProps) {
  // Content truncation
  const shouldTruncate = rumor.content.length > MAX_CONTENT_LENGTH;
  const displayContent = useMemo(
    () =>
      shouldTruncate && !isExpanded
        ? rumor.content.slice(0, MAX_CONTENT_LENGTH) + '...'
        : rumor.content,
    [shouldTruncate, isExpanded, rumor.content]
  );

  return (
    <article
      className="rounded-lg border border-border bg-card p-4 transition-all hover:border-border/80 hover:shadow-sm"
      aria-labelledby={`rumor-title-${rumor.rumor_id}`}
    >
      <div className="space-y-3">
        {/* Header: Veracity badge and spread count */}
        <RumorCardHeader rumor={rumor} />

        {/* Content */}
        <div className="space-y-2">
          <p className="text-sm leading-relaxed text-foreground">{displayContent}</p>
          {shouldTruncate && (
            <button
              onClick={onToggleExpand}
              className="flex items-center gap-1 text-xs text-primary hover:underline focus:outline-none focus:ring-2 focus:ring-primary/20 rounded px-1 -ml-1"
              aria-expanded={isExpanded}
              aria-label={isExpanded ? 'Show less content' : 'Show more content'}
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

        {/* Footer: Origin and days circulating */}
        <RumorCardFooter rumor={rumor} />
      </div>
    </article>
  );
});

/**
 * Loading skeleton for the tavern board.
 */
function TavernBoardSkeleton() {
  return (
    <div className="space-y-4" role="status" aria-label="Loading rumors">
      {[1, 2, 3].map((i) => (
        <div key={i} className="rounded-lg border border-border bg-card p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Skeleton className="h-6 w-24" />
              <Skeleton className="h-4 w-10" />
            </div>
            <Skeleton className="h-4 w-16" />
          </div>
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
          <div className="flex items-center justify-between pt-2">
            <Skeleton className="h-3 w-28" />
            <Skeleton className="h-5 w-20" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Empty state for when no rumors are available.
 */
function EmptyState() {
  return (
    <div
      className="flex flex-col items-center justify-center py-12 text-center px-4"
      role="status"
      aria-label="No rumors available"
    >
      <div className="rounded-full bg-muted p-4 mb-4">
        <MessageCircleWarning
          className="h-8 w-8 text-muted-foreground/60"
          aria-hidden="true"
        />
      </div>
      <p className="text-sm font-medium text-muted-foreground">
        The tavern is quiet... no rumors here.
      </p>
      <p className="mt-1 text-xs text-muted-foreground/70">
        Check back later or visit another location.
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
      aria-label="Error loading rumors"
    >
      <div className="rounded-full bg-destructive/10 p-4 mb-4">
        <AlertTriangle className="h-8 w-8 text-destructive" aria-hidden="true" />
      </div>
      <p className="text-sm font-medium text-destructive">Failed to load rumors</p>
      <p className="mt-1 text-xs text-muted-foreground mb-4">
        Something went wrong while fetching the tavern board.
      </p>
      <Button variant="outline" size="sm" onClick={onRetry} aria-label="Retry loading rumors">
        Try again
      </Button>
    </div>
  );
}

/**
 * Main TavernBoard component.
 */
export const TavernBoard = React.memo(function TavernBoard({
  worldId,
  locationId,
  maxItems = 20,
}: Props) {
  const [sortBy, setSortBy] = useState<RumorSortBy>('recent');
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const { data, isLoading, isError, refetch } = useLocationRumors(
    worldId,
    locationId,
    sortBy,
    maxItems
  );

  const rumors = useMemo(() => data?.rumors ?? [], [data?.rumors]);

  // Reset expanded state when sort changes
  React.useEffect(() => {
    setExpandedIds(new Set());
  }, [sortBy, locationId]);

  // Toggle expand/collapse for a rumor
  const handleToggleExpand = useCallback((rumorId: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(rumorId)) {
        next.delete(rumorId);
      } else {
        next.add(rumorId);
      }
      return next;
    });
  }, []);

  const handleSortChange = useCallback((value: RumorSortBy) => {
    setSortBy(value);
  }, []);

  const handleRetry = useCallback(() => {
    refetch();
  }, [refetch]);

  return (
    <Card className="h-full" data-testid="tavern-board">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-4">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <MessageCircleWarning className="h-5 w-5" aria-hidden="true" />
            Tavern Board
          </CardTitle>
          {/* Sort dropdown */}
          <Select value={sortBy} onValueChange={handleSortChange}>
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
          <TavernBoardSkeleton />
        ) : isError ? (
          <ErrorState onRetry={handleRetry} />
        ) : rumors.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="space-y-4" role="list" aria-label="Tavern rumors">
            {rumors.map((rumor) => (
              <RumorCard
                key={rumor.rumor_id}
                rumor={rumor}
                isExpanded={expandedIds.has(rumor.rumor_id)}
                onToggleExpand={() => handleToggleExpand(rumor.rumor_id)}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
});

export default TavernBoard;
