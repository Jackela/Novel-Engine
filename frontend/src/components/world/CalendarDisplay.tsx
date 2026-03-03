/**
 * CalendarDisplay Component (SIM-004)
 *
 * Displays the current world calendar with controls to advance time.
 * Provides accessible UI with loading, error, and success states.
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Clock, ChevronRight, AlertCircle, RefreshCw } from 'lucide-react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardDescription,
} from '@/shared/components/ui/Card';
import { Button } from '@/shared/components/ui';
import { useCalendar, useAdvanceCalendar } from '@/lib/api';

interface CalendarDisplayProps {
  /** The unique identifier for the world */
  worldId: string;
  /** Optional callback when calendar is advanced */
  onAdvance?: (days: number) => void;
}

/**
 * Calendar display component with advance controls.
 *
 * Features:
 * - Displays formatted date and era name
 * - Advance buttons for 1, 7, and 30 days
 * - Loading and error states
 * - Accessible with WCAG 2.1 AA compliance
 */
export const CalendarDisplay = React.memo(function CalendarDisplay({ worldId, onAdvance }: CalendarDisplayProps) {
  const [announcement, setAnnouncement] = useState<string>('');
  const [isAdvancingUi, setIsAdvancingUi] = useState(false);
  const {
    data: calendar,
    isLoading,
    isError,
    error,
    refetch,
  } = useCalendar(worldId);

  const advanceMutation = useAdvanceCalendar();

  const handleAdvance = useCallback(async (days: number) => {
    setIsAdvancingUi(true);
    try {
      await advanceMutation.mutateAsync({ worldId, days });
      setAnnouncement(`Time advanced by ${days} day${days > 1 ? 's' : ''}`);
      onAdvance?.(days);
    } catch {
      setAnnouncement('Failed to advance time');
    } finally {
      setIsAdvancingUi(false);
    }
  }, [worldId, onAdvance, advanceMutation]);

  // Memoize retry handler
  const handleRetry = useCallback(() => {
    refetch();
  }, [refetch]);

  // Memoize derived state
  const isAdvancing = useMemo(() =>
    isAdvancingUi || advanceMutation.isPending,
    [isAdvancingUi, advanceMutation.isPending]
  );

  // Memoize formatted date derivation
  const formattedDateWithoutEra = useMemo(() => {
    if (!calendar) return '';
    const eraSuffix = ` - ${calendar.era_name}`;
    return calendar.formatted_date.endsWith(eraSuffix)
      ? calendar.formatted_date.slice(0, -eraSuffix.length)
      : calendar.formatted_date;
  }, [calendar]);

  // Loading state with skeleton
  if (isLoading) {
    return (
      <Card data-testid="calendar-display" data-state="loading">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-primary" />
            World Time
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="animate-pulse space-y-2">
              <div className="h-8 w-24 rounded bg-muted mx-auto" />
              <div className="h-5 w-32 rounded bg-muted mx-auto" />
            </div>
            <div className="flex justify-center gap-2">
              <div className="h-9 w-20 rounded bg-muted" />
              <div className="h-9 w-20 rounded bg-muted" />
              <div className="h-9 w-20 rounded bg-muted" />
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Error state with retry button
  if (isError || !calendar) {
    return (
      <Card data-testid="calendar-display" data-state="error">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-primary" />
            World Time
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4 text-center">
            <div className="flex items-center justify-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              <p className="text-sm">
                {error?.message || 'Failed to load calendar'}
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRetry}
              aria-label="Retry loading calendar"
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid="calendar-display" data-state="success">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-primary" />
          World Time
        </CardTitle>
        <CardDescription>
          {calendar.era_name}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Date display with aria-live for announcements */}
          <div className="text-center">
            <p
              className="text-3xl font-bold"
              aria-live="polite"
              aria-atomic="true"
            >
              {formattedDateWithoutEra}
            </p>
          </div>

          {/* Advance buttons */}
          <div className="flex justify-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleAdvance(1)}
              disabled={isAdvancing}
              aria-label="Advance time by 1 day"
            >
              <ChevronRight className="mr-1 h-4 w-4" />
              1 Day
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleAdvance(7)}
              disabled={isAdvancing}
              aria-label="Advance time by 7 days"
            >
              <ChevronRight className="mr-1 h-4 w-4" />
              7 Days
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleAdvance(30)}
              disabled={isAdvancing}
              aria-label="Advance time by 30 days"
            >
              <ChevronRight className="mr-1 h-4 w-4" />
              30 Days
            </Button>
          </div>

          {/* Screen reader announcements */}
          <div className="sr-only" aria-live="polite" aria-atomic="true">
            {announcement}
          </div>
        </div>
      </CardContent>
    </Card>
  );
});

export default CalendarDisplay;
