/**
 * FactionIntelPanel - Display and manage faction AI-generated intents
 *
 * This component provides an interface for viewing and interacting with
 * AI-generated faction intents. It follows WCAG 2.1 AA guidelines for
 * accessibility.
 *
 * Features:
 * - Faction selector dropdown
 * - Generate Intents action button
 * - Intent cards with color-coded action types
 * - History accordion for past intents
 * - Loading and error states
 *
 * @module features/world/components/FactionIntelPanel
 */

import * as React from 'react';
import { ChevronDown, Loader2, RefreshCw, Target, Sword, Package, Bomb, Shield, Check } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';

import { cn } from '@/lib/utils';
import { useFactionIntel, useFactionIntents } from '../api/factionIntelApi';
import type { FactionIntentResponse, ActionType, IntentStatus, GenerateIntentsRequest } from '@/types/schemas';

// === Constants ===

/** Color mapping for action types per REQ-UI-002 */
const ACTION_TYPE_CONFIG: Record<
  ActionType,
  { color: string; bgColor: string; icon: React.ElementType; label: string }
> = {
  EXPAND: {
    color: 'text-green-600',
    bgColor: 'bg-green-100 dark:bg-green-900/30',
    icon: Target,
    label: 'Expand',
  },
  ATTACK: {
    color: 'text-red-600',
    bgColor: 'bg-red-100 dark:bg-red-900/30',
    icon: Sword,
    label: 'Attack',
  },
  TRADE: {
    color: 'text-blue-600',
    bgColor: 'bg-blue-100 dark:bg-blue-900/30',
    icon: Package,
    label: 'Trade',
  },
  SABOTAGE: {
    color: 'text-purple-600',
    bgColor: 'bg-purple-100 dark:bg-purple-900/30',
    icon: Bomb,
    label: 'Sabotage',
  },
  STABILIZE: {
    color: 'text-gray-600',
    bgColor: 'bg-gray-100 dark:bg-gray-900/30',
    icon: Shield,
    label: 'Stabilize',
  },
};

/** Status badge styles */
const STATUS_STYLES: Record<IntentStatus, { variant: 'default' | 'secondary' | 'outline' | 'destructive'; label: string }> = {
  PROPOSED: { variant: 'secondary', label: 'Proposed' },
  SELECTED: { variant: 'default', label: 'Selected' },
  EXECUTED: { variant: 'outline', label: 'Executed' },
  REJECTED: { variant: 'destructive', label: 'Rejected' },
};

/** Priority badge colors */
const PRIORITY_COLORS: Record<number, string> = {
  1: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200',
  2: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-200',
  3: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200',
};

// === Props ===

export interface FactionIntelPanelProps {
  /** Available factions to select from */
  factions: Array<{ id: string; name: string }>;
  /** Initially selected faction ID */
  defaultFactionId?: string;
  /** Callback when an intent is selected */
  onIntentSelect?: (intent: FactionIntentResponse) => void;
  /** Optional className for styling */
  className?: string;
}

// === Sub-components ===

/**
 * IntentCard - Display a single faction intent
 */
interface IntentCardProps {
  intent: FactionIntentResponse;
  onSelect?: () => void;
  isSelecting?: boolean;
}

function IntentCard({ intent, onSelect, isSelecting }: IntentCardProps) {
  const config = ACTION_TYPE_CONFIG[intent.action_type];
  const statusConfig = STATUS_STYLES[intent.status];
  const Icon = config.icon;
  const canSelect = intent.status === 'PROPOSED' && onSelect;

  return (
    <Card
      className={cn('transition-all', canSelect && 'hover:border-primary/50 cursor-pointer')}
      role="article"
      aria-labelledby={`intent-title-${intent.intent_id}`}
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-4">
          {/* Action Type Icon */}
          <div
            className={cn(
              'flex h-10 w-10 shrink-0 items-center justify-center rounded-lg',
              config.bgColor
            )}
            aria-label={`${config.label} action`}
          >
            <Icon className={cn('h-5 w-5', config.color)} aria-hidden="true" />
          </div>

          {/* Content */}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h4
                id={`intent-title-${intent.intent_id}`}
                className="text-sm font-medium truncate"
              >
                {config.label}
                {intent.target_name && (
                  <span className="text-muted-foreground font-normal">
                    {' '}
                    - {intent.target_name}
                  </span>
                )}
              </h4>
              {/* Priority Badge */}
              <Badge
                className={cn('text-xs', PRIORITY_COLORS[intent.priority])}
                aria-label={`Priority ${intent.priority}`}
              >
                P{intent.priority}
              </Badge>
            </div>

            {/* Rationale */}
            <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
              {intent.rationale}
            </p>

            {/* Footer with Status and Action */}
            <div className="mt-3 flex items-center justify-between">
              <Badge variant={statusConfig.variant} className="text-xs">
                {statusConfig.label}
              </Badge>

              {canSelect && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelect();
                  }}
                  disabled={isSelecting}
                  aria-label={`Select ${config.label} intent`}
                >
                  {isSelecting ? (
                    <>
                      <Loader2 className="mr-1 h-3 w-3 animate-spin" aria-hidden="true" />
                      Selecting...
                    </>
                  ) : (
                    <>
                      <Check className="mr-1 h-3 w-3" aria-hidden="true" />
                      Select
                    </>
                  )}
                </Button>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * LoadingSkeleton - Loading state placeholder
 */
function LoadingSkeleton() {
  return (
    <div
      className="flex items-center justify-center py-12"
      role="status"
      aria-live="polite"
      aria-label="Loading intents"
    >
      <div className="text-center">
        <Loader2 className="mx-auto h-8 w-8 animate-spin text-muted-foreground" aria-hidden="true" />
        <p className="mt-2 text-sm text-muted-foreground">
          Analyzing faction situation...
        </p>
      </div>
    </div>
  );
}

/**
 * ErrorDisplay - Error state with retry button
 */
interface ErrorDisplayProps {
  message: string;
  onRetry?: () => void;
  isRetrying?: boolean;
}

function ErrorDisplay({ message, onRetry, isRetrying }: ErrorDisplayProps) {
  return (
    <div
      className="rounded-lg border border-destructive/50 bg-destructive/10 p-4"
      role="alert"
      aria-live="assertive"
    >
      <div className="flex items-start gap-3">
        <div className="text-destructive">
          <svg
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium text-destructive">{message}</p>
          {onRetry && (
            <Button
              size="sm"
              variant="outline"
              className="mt-2"
              onClick={onRetry}
              disabled={isRetrying}
            >
              {isRetrying ? (
                <>
                  <Loader2 className="mr-1 h-3 w-3 animate-spin" aria-hidden="true" />
                  Retrying...
                </>
              ) : (
                <>
                  <RefreshCw className="mr-1 h-3 w-3" aria-hidden="true" />
                  Retry
                </>
              )}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * EmptyState - No intents available
 */
function EmptyState({ onGenerate }: { onGenerate?: () => void }) {
  return (
    <div className="rounded-lg border border-dashed py-12 text-center">
      <Shield className="mx-auto h-12 w-12 text-muted-foreground/50" aria-hidden="true" />
      <p className="mt-2 text-sm text-muted-foreground">
        No intents available for this faction.
      </p>
      {onGenerate && (
        <Button
          size="sm"
          variant="secondary"
          className="mt-4"
          onClick={onGenerate}
        >
          Generate Intents
        </Button>
      )}
    </div>
  );
}

// === Main Component ===

/**
 * FactionIntelPanel
 *
 * Displays AI-generated faction intents with generation, selection, and history capabilities.
 *
 * @example
 * ```tsx
 * <FactionIntelPanel
 *   factions={[
 *     { id: 'faction-1', name: 'North Kingdom' },
 *     { id: 'faction-2', name: 'Southern Empire' },
 *   ]}
 *   defaultFactionId="faction-1"
 *   onIntentSelect={(intent) => console.log('Selected:', intent)}
 * />
 * ```
 */
export function FactionIntelPanel({
  factions,
  defaultFactionId,
  onIntentSelect,
  className,
}: FactionIntelPanelProps) {
  // State
  const [selectedFactionId, setSelectedFactionId] = React.useState<string>(
    defaultFactionId || factions[0]?.id || ''
  );
  const [historyOpen, setHistoryOpen] = React.useState(false);

  // Hooks
  const {
    intents: proposedIntents,
    isLoading,
    isGenerating,
    isSelecting,
    error,
    generateIntents,
    selectIntent,
    refetch,
  } = useFactionIntel(selectedFactionId, 'PROPOSED');

  // Note: In a real implementation, you'd fetch history separately with status !== 'PROPOSED'
  // For now, we'll use a separate query for history
  const allIntentsQuery = useFactionIntents(selectedFactionId);

  // Filter historical intents (not PROPOSED)
  const historicalIntents: FactionIntentResponse[] = React.useMemo(() => {
    if (!allIntentsQuery.data?.intents) return [];
    return allIntentsQuery.data.intents.filter(
      (intent) => intent.status !== 'PROPOSED'
    );
  }, [allIntentsQuery.data?.intents]);

  // Handlers
  const handleGenerate = React.useCallback(() => {
    if (!selectedFactionId) return;
    const request: GenerateIntentsRequest = {
      faction_id: selectedFactionId,
      max_intents: 3,
    };
    generateIntents(request);
  }, [selectedFactionId, generateIntents]);

  const handleSelectIntent = React.useCallback(
    (intent: FactionIntentResponse) => {
      selectIntent({ factionId: intent.faction_id, intentId: intent.intent_id });
      // Call the callback - the mutation will handle invalidation
      onIntentSelect?.(intent);
    },
    [selectIntent, onIntentSelect]
  );

  // Announce new intents to screen readers
  const intentCount = proposedIntents?.intents.length ?? 0;
  React.useEffect(() => {
    if (intentCount > 0 && !isLoading) {
      // Create a live region announcement
      const announcement = document.createElement('div');
      announcement.setAttribute('role', 'status');
      announcement.setAttribute('aria-live', 'polite');
      announcement.setAttribute('aria-atomic', 'true');
      announcement.className = 'sr-only';
      announcement.textContent = `${intentCount} intent${intentCount === 1 ? '' : 's'} generated`;
      document.body.appendChild(announcement);
      setTimeout(() => announcement.remove(), 1000);
    }
  }, [intentCount, isLoading]);

  return (
    <Card className={cn('w-full', className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Target className="h-5 w-5" aria-hidden="true" />
          Faction Intel
        </CardTitle>
        <CardDescription>
          AI-generated strategic intents for faction decision-making
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Faction Selector */}
        <div className="flex items-end gap-4">
          <div className="flex-1">
            <label
              htmlFor="faction-select"
              className="mb-2 block text-sm font-medium"
            >
              Select Faction
            </label>
            <Select
              value={selectedFactionId}
              onValueChange={setSelectedFactionId}
            >
              <SelectTrigger id="faction-select">
                <SelectValue placeholder="Choose a faction" />
              </SelectTrigger>
              <SelectContent>
                {factions.map((faction) => (
                  <SelectItem key={faction.id} value={faction.id}>
                    {faction.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Button
            onClick={handleGenerate}
            disabled={!selectedFactionId || isGenerating}
            aria-busy={isGenerating}
          >
            {isGenerating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                Generating...
              </>
            ) : (
              <>
                <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
                Generate Intents
              </>
            )}
          </Button>
        </div>

        {/* Error State */}
        {error && (
          <ErrorDisplay
            message={error.message}
            onRetry={() => refetch()}
            isRetrying={isLoading}
          />
        )}

        {/* Loading State */}
        {isLoading && !proposedIntents && <LoadingSkeleton />}

        {/* Proposed Intents */}
        {!isLoading && !error && proposedIntents && (
          <section aria-label="Proposed intents">
            <h3 className="mb-3 text-sm font-medium text-muted-foreground">
              Proposed Actions ({intentCount})
            </h3>

            {intentCount === 0 ? (
              <EmptyState onGenerate={handleGenerate} />
            ) : (
              <div className="space-y-3">
                {proposedIntents.intents.map((intent) => (
                  <IntentCard
                    key={intent.intent_id}
                    intent={intent}
                    onSelect={() => handleSelectIntent(intent)}
                    isSelecting={isSelecting}
                  />
                ))}
              </div>
            )}
          </section>
        )}

        {/* History Accordion */}
        {historicalIntents.length > 0 && (
          <Collapsible open={historyOpen} onOpenChange={setHistoryOpen}>
            <CollapsibleTrigger asChild>
              <Button
                variant="ghost"
                className="w-full justify-between"
                aria-expanded={historyOpen}
                aria-controls="history-content"
              >
                <span className="flex items-center gap-2">
                  <span>History</span>
                  <Badge variant="secondary" className="text-xs">
                    {historicalIntents.length}
                  </Badge>
                </span>
                <ChevronDown
                  className={cn(
                    'h-4 w-4 transition-transform',
                    historyOpen && 'rotate-180'
                  )}
                  aria-hidden="true"
                />
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent id="history-content" className="mt-3 space-y-3">
              {historicalIntents.map((intent) => (
                <IntentCard key={intent.intent_id} intent={intent} />
              ))}
            </CollapsibleContent>
          </Collapsible>
        )}
      </CardContent>
    </Card>
  );
}

export default FactionIntelPanel;
