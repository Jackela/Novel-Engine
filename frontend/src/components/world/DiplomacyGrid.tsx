/**
 * DiplomacyGrid - 2D grid visualization of faction relationships (PREP-012)
 *
 * Why: Provides a matrix-style view of diplomatic relationships between factions,
 * allowing users to quickly understand the geopolitical landscape.
 *
 * Color mapping:
 * - ALLIED: green
 * - FRIENDLY: lime
 * - NEUTRAL: yellow
 * - COLD: orange
 * - HOSTILE: red
 * - AT_WAR: dark-red
 */
import React, { useMemo, useState, useCallback } from 'react';
import { cn } from '@/lib/utils';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { useDiplomacyDetail, type PactSummary } from '@/lib/api/worldStateApi';

/**
 * Map diplomatic status to HSL color values.
 * PREP-012: Color mapping as specified in acceptance criteria.
 */
const STATUS_COLORS: Record<string, string> = {
  allied: 'hsl(142, 76%, 36%)', // green
  friendly: 'hsl(84, 81%, 44%)', // lime
  neutral: 'hsl(48, 96%, 53%)', // yellow
  cold: 'hsl(27, 96%, 53%)', // orange
  hostile: 'hsl(0, 84%, 50%)', // red
  at_war: 'hsl(0, 72%, 35%)', // dark-red
  war: 'hsl(0, 72%, 35%)', // dark-red (alternative key)
  '-': 'hsl(0, 0%, 90%)', // self/neutral gray
};

/**
 * Get background color for a diplomatic status.
 */
function getStatusColor(status: string): string {
  const normalizedStatus = status.toLowerCase().replace(' ', '_');
  return STATUS_COLORS[normalizedStatus] ?? 'hsl(48, 96%, 53%)'; // default to neutral yellow
}

/**
 * Get text color for a diplomatic status (for readability).
 */
function getStatusTextColor(status: string): string {
  const normalizedStatus = status.toLowerCase().replace(' ', '_');
  // Dark text for light backgrounds, light text for dark backgrounds
  const darkTextStatuses = ['allied', 'friendly', 'neutral', 'cold', '-'];
  return darkTextStatuses.includes(normalizedStatus)
    ? 'hsl(0, 0%, 10%)'
    : 'hsl(0, 0%, 100%)';
}

/**
 * Format diplomatic status for display.
 */
function formatStatus(status: string): string {
  if (status === '-') return '-';
  return status
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

/**
 * PactDetailDialog - Shows details of a diplomatic pact.
 */
interface PactDetailDialogProps {
  pact: PactSummary | null;
  open: boolean;
  onClose: () => void;
}

const PactDetailDialog = React.memo(function PactDetailDialog({ pact, open, onClose }: PactDetailDialogProps) {
  if (!pact) return null;

  const handleOpenChange = useCallback((next: boolean) => {
    if (!next) onClose();
  }, [onClose]);

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-md" aria-modal="true">
        <DialogHeader>
          <DialogTitle>Pact Details</DialogTitle>
          <DialogDescription>
            {pact.faction_a_id} ↔ {pact.faction_b_id}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Type</span>
            <Badge
              variant="outline"
              style={{
                backgroundColor: getStatusColor(pact.pact_type),
                color: getStatusTextColor(pact.pact_type),
              }}
            >
              {formatStatus(pact.pact_type)}
            </Badge>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Status</span>
            <Badge variant={pact.is_active ? 'default' : 'secondary'}>
              {pact.is_active ? 'Active' : 'Inactive'}
            </Badge>
          </div>

          {pact.signed_date && (
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Signed</span>
              <span>{pact.signed_date}</span>
            </div>
          )}

          {pact.expires_date && (
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Expires</span>
              <span>{pact.expires_date}</span>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
});

export interface DiplomacyGridProps {
  /** The world ID to fetch diplomacy data for */
  worldId: string;
  /** Optional CSS class name */
  className?: string;
  /** Optional faction name map for display (faction_id -> display name) */
  factionNames?: Record<string, string>;
}

/**
 * DiplomacyGrid renders a 2D matrix showing relationships between factions.
 *
 * PREP-012: Visualization of faction relationships in grid format.
 *
 * @example
 * ```tsx
 * function WorldDiplomacy({ worldId }: { worldId: string }) {
 *   return (
 *     <DiplomacyGrid
 *       worldId={worldId}
 *       factionNames={{ 'faction-1': 'Kingdom', 'faction-2': 'Empire' }}
 *     />
 *   );
 * }
 * ```
 */
export const DiplomacyGrid = React.memo(function DiplomacyGrid({
  worldId,
  className,
  factionNames = {},
}: DiplomacyGridProps) {
  const { data, isLoading, error } = useDiplomacyDetail(worldId);
  const [selectedPact, setSelectedPact] = useState<PactSummary | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  // Memoize getFactionName callback
  const getFactionName = useCallback((factionId: string): string => {
    return factionNames[factionId] ?? factionId;
  }, [factionNames]);

  // Find pact between two factions - memoized function
  const findPact = useMemo(() => {
    return (factionA: string, factionB: string): PactSummary | undefined => {
      if (!data?.active_pacts) return undefined;
      return data.active_pacts.find(
        (pact) =>
          (pact.faction_a_id === factionA && pact.faction_b_id === factionB) ||
          (pact.faction_a_id === factionB && pact.faction_b_id === factionA)
      );
    };
  }, [data?.active_pacts]);

  // Handle cell click - memoized
  const handleCellClick = useCallback((factionA: string, factionB: string) => {
    if (factionA === factionB) return; // Don't show dialog for self

    const pact = findPact(factionA, factionB);
    if (pact) {
      setSelectedPact(pact);
      setDialogOpen(true);
    }
  }, [findPact]);

  // Handle dialog close - memoized
  const handleDialogClose = useCallback(() => {
    setDialogOpen(false);
  }, []);

  // Loading state
  if (isLoading) {
    return (
      <div
        className={cn(
          'flex items-center justify-center p-8 text-muted-foreground',
          className
        )}
      >
        <p>Loading diplomacy data...</p>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        className={cn(
          'flex items-center justify-center p-8 text-destructive',
          className
        )}
      >
        <p>Failed to load diplomacy data</p>
      </div>
    );
  }

  // Empty state
  if (!data || !data.factions || data.factions.length === 0) {
    return (
      <div
        className={cn(
          'flex items-center justify-center p-8 text-muted-foreground',
          className
        )}
      >
        <p>No factions to display</p>
      </div>
    );
  }

  const { factions, matrix } = data;

  return (
    <TooltipProvider>
      <div className={cn('overflow-x-auto', className)}>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              {/* Empty corner cell */}
              <th className="h-12 w-24 min-w-24 border border-border bg-muted/50"></th>
              {/* Column headers */}
              {factions.map((factionId) => (
                <th
                  key={factionId}
                  className="h-12 min-w-16 border border-border bg-muted/50 px-2 text-center text-xs font-medium"
                >
                  <span className="block truncate" title={getFactionName(factionId)}>
                    {getFactionName(factionId)}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {factions.map((rowFactionId) => (
              <tr key={rowFactionId}>
                {/* Row header */}
                <td className="h-12 w-24 min-w-24 border border-border bg-muted/50 px-2 text-xs font-medium">
                  <span className="block truncate" title={getFactionName(rowFactionId)}>
                    {getFactionName(rowFactionId)}
                  </span>
                </td>
                {/* Matrix cells */}
                {factions.map((colFactionId) => {
                  const status = matrix[rowFactionId]?.[colFactionId] ?? 'neutral';
                  const isSelf = rowFactionId === colFactionId;
                  const pact = findPact(rowFactionId, colFactionId);
                  const hasPact = !!pact;

                  return (
                    <td
                      key={colFactionId}
                      className="relative h-12 min-w-16 border border-border p-0"
                    >
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <button
                            type="button"
                            className={cn(
                              'flex h-full w-full items-center justify-center text-xs font-medium transition-opacity',
                              'hover:opacity-80 focus:outline-none focus:ring-2 focus:ring-ring',
                              hasPact && 'cursor-pointer',
                              !hasPact && !isSelf && 'cursor-default'
                            )}
                            style={{
                              backgroundColor: getStatusColor(status),
                              color: getStatusTextColor(status),
                            }}
                            onClick={() => handleCellClick(rowFactionId, colFactionId)}
                            disabled={!hasPact}
                            aria-label={`${getFactionName(rowFactionId)} to ${getFactionName(colFactionId)}: ${formatStatus(status)}`}
                          >
                            {isSelf ? '-' : formatStatus(status).charAt(0)}
                            {hasPact && !isSelf && (
                              <span className="absolute bottom-0.5 right-0.5 h-1.5 w-1.5 rounded-full bg-white/80" />
                            )}
                          </button>
                        </TooltipTrigger>
                        <TooltipContent side="top" className="max-w-xs">
                          <p className="font-medium">
                            {getFactionName(rowFactionId)} ↔ {getFactionName(colFactionId)}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            Status: {formatStatus(status)}
                          </p>
                          {hasPact && (
                            <p className="text-xs text-primary">
                              Click to view pact details
                            </p>
                          )}
                        </TooltipContent>
                      </Tooltip>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>

        {/* Legend */}
        <div className="mt-4 flex flex-wrap gap-2">
          {Object.entries(STATUS_COLORS)
            .filter(([key]) => key !== '-')
            .map(([status, color]) => (
              <div key={status} className="flex items-center gap-1">
                <span
                  className="h-3 w-3 rounded-sm"
                  style={{ backgroundColor: color }}
                />
                <span className="text-xs text-muted-foreground">
                  {formatStatus(status)}
                </span>
              </div>
            ))}
          <div className="flex items-center gap-1">
            <span className="h-3 w-3 rounded-full bg-white/80" />
            <span className="text-xs text-muted-foreground">Has Pact</span>
          </div>
        </div>
      </div>

      {/* Pact detail dialog */}
      <PactDetailDialog
        pact={selectedPact}
        open={dialogOpen}
        onClose={handleDialogClose}
      />
    </TooltipProvider>
  );
});

export default DiplomacyGrid;
