/**
 * DiplomacyMatrix Component (SIM-011)
 *
 * Visual grid showing diplomatic relationships between all factions.
 * Features:
 * - Color-coded cells by relationship status
 * - Tooltip on hover showing faction names and status
 * - Click cell to edit relation via dialog
 * - Keyboard navigation with arrow keys
 * - Accessible with WCAG 2.1 AA compliance
 */
import { useState, useRef, useCallback, useMemo, Fragment, type KeyboardEvent } from 'react';
import { Users, AlertCircle, RefreshCw } from 'lucide-react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardDescription,
} from '@/shared/components/ui/Card';
import { Button } from '@/shared/components/ui';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/shared/components/ui/tooltip';
import { useDiplomacyMatrix, useSetRelation } from '@/lib/api';
import type { DiplomaticStatus } from '@/types/schemas';

interface DiplomacyMatrixProps {
  /** The unique identifier for the world */
  worldId: string;
}

/**
 * Color mapping for diplomatic statuses.
 * Uses HSL CSS variables from the design system.
 */
const STATUS_COLORS: Record<string, string> = {
  allied: 'hsl(var(--success))',
  friendly: 'hsl(var(--success))',
  neutral: 'hsl(var(--warning))',
  cold: 'hsl(var(--warning))',
  hostile: 'hsl(var(--destructive))',
  at_war: 'hsl(var(--destructive))',
  '-': 'hsl(var(--muted-foreground))', // Gray for self-relation
};

/**
 * Human-readable labels for diplomatic statuses.
 */
const STATUS_LABELS: Record<string, string> = {
  allied: 'Allied',
  friendly: 'Friendly',
  neutral: 'Neutral',
  cold: 'Cold',
  hostile: 'Hostile',
  at_war: 'At War',
  '-': '-',
};

/**
 * Diplomacy matrix grid component.
 *
 * Displays faction relationships in a color-coded grid where:
 * - Rows and columns are factions
 * - Cell color indicates relationship status
 * - Diagonal cells (self-relations) are gray with '-'
 */
export function DiplomacyMatrix({ worldId }: DiplomacyMatrixProps) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedCell, setSelectedCell] = useState<{
    factionA: string;
    factionB: string;
    currentStatus: string;
  } | null>(null);
  const [focusedCell, setFocusedCell] = useState<{ row: number; col: number }>({
    row: 0,
    col: 0,
  });
  const [announceText, setAnnounceText] = useState<string>('');

  const gridRef = useRef<HTMLDivElement>(null);

  const {
    data: diplomacyData,
    isLoading,
    isError,
    error,
    refetch,
  } = useDiplomacyMatrix(worldId);

  const setRelationMutation = useSetRelation();

  const factions = useMemo(() => diplomacyData?.factions ?? [], [diplomacyData?.factions]);
  const matrix = useMemo(() => diplomacyData?.matrix ?? {}, [diplomacyData?.matrix]);

  /**
   * Get status label for display (capitalized).
   */
  const getStatusLabel = (status: string): string => {
    return STATUS_LABELS[status] ?? status;
  };

  /**
   * Get background color for a status.
   */
  const getStatusColor = (status: string): string => {
    return STATUS_COLORS[status] ?? 'hsl(var(--muted-foreground))';
  };

  /**
   * Handle cell click to open edit dialog.
   */
  const handleCellClick = useCallback((factionA: string, factionB: string) => {
    // Don't allow editing self-relations
    if (factionA === factionB) return;

    const currentStatus = matrix[factionA]?.[factionB] ?? 'neutral';
    setSelectedCell({ factionA, factionB, currentStatus });
    setDialogOpen(true);
  }, [matrix]);

  /**
   * Handle status change in dialog.
   */
  const handleStatusChange = (newStatus: string) => {
    if (!selectedCell) return;
    setSelectedCell({ ...selectedCell, currentStatus: newStatus });
  };

  /**
   * Save the relation change.
   */
  const handleSave = async () => {
    if (!selectedCell) return;

    try {
      await setRelationMutation.mutateAsync({
        worldId,
        factionA: selectedCell.factionA,
        factionB: selectedCell.factionB,
        status: selectedCell.currentStatus as DiplomaticStatus,
      });
      setAnnounceText(
        `Relation between ${selectedCell.factionA} and ${selectedCell.factionB} updated to ${getStatusLabel(selectedCell.currentStatus)}`
      );
      setDialogOpen(false);
      setSelectedCell(null);
    } catch {
      setAnnounceText('Failed to update relation');
    }
  };

  /**
   * Handle keyboard navigation in the grid.
   */
  const handleGridKeyDown = useCallback(
    (e: KeyboardEvent<HTMLDivElement>) => {
      if (factions.length === 0) return;

      let { row, col } = focusedCell;
      const maxRow = factions.length;
      const maxCol = factions.length;

      switch (e.key) {
        case 'ArrowRight':
          col = Math.min(col + 1, maxCol);
          break;
        case 'ArrowLeft':
          col = Math.max(col - 1, 0);
          break;
        case 'ArrowDown':
          row = Math.min(row + 1, maxRow);
          break;
        case 'ArrowUp':
          row = Math.max(row - 1, 0);
          break;
        case 'Enter':
        case ' ': {
          e.preventDefault();
          // Row 0 is header, col 0 is header
          if (row > 0 && col > 0) {
            const factionA = factions[row - 1];
            const factionB = factions[col - 1];
            if (factionA && factionB) {
              handleCellClick(factionA, factionB);
            }
          }
          return;
        }
        default:
          return;
      }

      e.preventDefault();
      setFocusedCell({ row, col });

      // Focus the cell button
      const cellId = `cell-${row}-${col}`;
      const cellElement = document.getElementById(cellId);
      cellElement?.focus();
    },
    [factions, focusedCell, handleCellClick]
  );

  // Loading state with skeleton grid
  if (isLoading) {
    // Create placeholder factions for skeleton
    const skeletonFactions = ['-', '-', '-', '-'];
    return (
      <Card data-testid="diplomacy-matrix" data-state="loading">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5 text-primary" />
            Diplomacy Matrix
          </CardTitle>
          <CardDescription>Loading faction relations...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <div className="grid gap-1" style={{ gridTemplateColumns: `repeat(${skeletonFactions.length + 1}, minmax(60px, 1fr))` }}>
              {/* Header row */}
              <div className="h-8" />
              {skeletonFactions.map((_, i) => (
                <div key={i} className="h-8 w-full animate-pulse rounded bg-muted" />
              ))}
              {/* Data rows */}
              {skeletonFactions.map((_, rowIdx) => (
                <>
                  <div key={`row-${rowIdx}`} className="h-10 w-full animate-pulse rounded bg-muted" />
                  {skeletonFactions.map((_, colIdx) => (
                    <div
                      key={`cell-${rowIdx}-${colIdx}`}
                      className="h-10 w-full animate-pulse rounded bg-muted"
                    />
                  ))}
                </>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Error state with retry button
  if (isError || !diplomacyData) {
    return (
      <Card data-testid="diplomacy-matrix" data-state="error">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5 text-primary" />
            Diplomacy Matrix
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4 text-center">
            <div className="flex items-center justify-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              <p className="text-sm">
                {error?.message || 'Failed to load diplomacy matrix'}
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              aria-label="Retry loading diplomacy matrix"
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Empty state
  if (factions.length === 0) {
    return (
      <Card data-testid="diplomacy-matrix" data-state="empty">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5 text-primary" />
            Diplomacy Matrix
          </CardTitle>
          <CardDescription>No factions registered</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-center text-sm text-muted-foreground">
            Factions will appear here once they are added to the world.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <TooltipProvider>
      <Card data-testid="diplomacy-matrix" data-state="success">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5 text-primary" />
            Diplomacy Matrix
          </CardTitle>
          <CardDescription>
            {factions.length} factions • Click cells to edit relations
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            ref={gridRef}
            role="grid"
            aria-label="Faction diplomacy matrix"
            tabIndex={0}
            className="overflow-x-auto focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 rounded"
            onKeyDown={handleGridKeyDown}
          >
            <div
              className="grid gap-1"
              style={{
                gridTemplateColumns: `repeat(${factions.length + 1}, minmax(60px, 1fr))`,
              }}
            >
              {/* Header row with faction names */}
              <div className="h-8" aria-hidden="true" />
              {factions.map((faction, colIdx) => (
                <div
                  key={`header-${faction}`}
                  id={`cell-0-${colIdx + 1}`}
                  role="columnheader"
                  className="flex h-8 items-center justify-center text-xs font-medium"
                  aria-label={faction}
                >
                  <span className="truncate">{faction}</span>
                </div>
              ))}

              {/* Data rows */}
              {factions.map((factionA, rowIdx) => (
                <Fragment key={`row-${factionA}`}>
                  {/* Row header */}
                  <div
                    id={`cell-${rowIdx + 1}-0`}
                    role="rowheader"
                    className="flex h-10 items-center justify-center text-xs font-medium"
                    aria-label={factionA}
                  >
                    <span className="truncate">{factionA}</span>
                  </div>

                  {/* Cells */}
                  {factions.map((factionB, colIdx) => {
                    const status = matrix[factionA]?.[factionB] ?? '-';
                    const isSelf = factionA === factionB;
                    const cellId = `cell-${rowIdx + 1}-${colIdx + 1}`;

                    const cell = (
                      <button
                        id={cellId}
                        role="gridcell"
                        tabIndex={focusedCell.row === rowIdx + 1 && focusedCell.col === colIdx + 1 ? 0 : -1}
                        disabled={isSelf}
                        onClick={() => handleCellClick(factionA, factionB)}
                        className={`h-10 w-full rounded text-xs font-medium transition-opacity ${
                          isSelf
                            ? 'cursor-default opacity-60'
                            : 'cursor-pointer hover:opacity-80 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1'
                        }`}
                        style={{ backgroundColor: getStatusColor(status) }}
                        aria-label={
                          isSelf
                            ? `${factionA} self`
                            : `Relation between ${factionA} and ${factionB}: ${getStatusLabel(status)}`
                        }
                      >
                        {isSelf ? '-' : ''}
                      </button>
                    );

                    // Wrap non-self cells in tooltip
                    if (!isSelf) {
                      return (
                        <Tooltip key={`cell-${factionA}-${factionB}`}>
                          <TooltipTrigger asChild>{cell}</TooltipTrigger>
                          <TooltipContent>
                            <p className="font-medium">
                              {factionA} ↔ {factionB}
                            </p>
                            <p className="text-xs opacity-80">
                              {getStatusLabel(status)}
                            </p>
                          </TooltipContent>
                        </Tooltip>
                      );
                    }

                    return (
                      <div key={`cell-${factionA}-${factionB}`}>{cell}</div>
                    );
                  })}
                </Fragment>
              ))}
            </div>
          </div>

          {/* Screen reader announcements */}
          <div className="sr-only" aria-live="polite" aria-atomic="true">
            {announceText}
          </div>
        </CardContent>

        {/* Edit Relation Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent
            className="sm:max-w-md"
            aria-modal="true"
            aria-describedby="dialog-description"
          >
            <DialogHeader>
              <DialogTitle>Edit Diplomatic Relation</DialogTitle>
              <DialogDescription id="dialog-description">
                Change the diplomatic status between two factions.
              </DialogDescription>
            </DialogHeader>

            {selectedCell && (
              <div className="space-y-4">
                {/* Faction A */}
                <div className="space-y-1">
                  <span className="text-sm font-medium">Faction A</span>
                  <p className="text-sm text-muted-foreground">
                    {selectedCell.factionA}
                  </p>
                </div>

                {/* Faction B */}
                <div className="space-y-1">
                  <span className="text-sm font-medium">Faction B</span>
                  <p className="text-sm text-muted-foreground">
                    {selectedCell.factionB}
                  </p>
                </div>

                {/* Current Status */}
                <div className="space-y-1">
                  <span className="text-sm font-medium">Current Status</span>
                  <div
                    className="inline-block rounded px-2 py-1 text-sm font-medium text-white"
                    style={{
                      backgroundColor: getStatusColor(selectedCell.currentStatus),
                    }}
                  >
                    {getStatusLabel(selectedCell.currentStatus)}
                  </div>
                </div>

                {/* Status Dropdown */}
                <div className="space-y-2">
                  <label
                    htmlFor="status-select"
                    className="text-sm font-medium"
                  >
                    New Status
                  </label>
                  <Select
                    value={selectedCell.currentStatus}
                    onValueChange={handleStatusChange}
                  >
                    <SelectTrigger id="status-select" className="w-full">
                      <SelectValue placeholder="Select status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="allied">Allied</SelectItem>
                      <SelectItem value="friendly">Friendly</SelectItem>
                      <SelectItem value="neutral">Neutral</SelectItem>
                      <SelectItem value="cold">Cold</SelectItem>
                      <SelectItem value="hostile">Hostile</SelectItem>
                      <SelectItem value="at_war">At War</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            )}

            <DialogFooter className="gap-2 sm:gap-0">
              <Button
                variant="outline"
                onClick={() => setDialogOpen(false)}
                disabled={setRelationMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                onClick={handleSave}
                disabled={setRelationMutation.isPending}
              >
                {setRelationMutation.isPending ? 'Saving...' : 'Save'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </Card>
    </TooltipProvider>
  );
}

export default DiplomacyMatrix;
