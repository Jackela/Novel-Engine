/**
 * PlotlineFilter - Dropdown to filter Weaver canvas by plotline (DIR-051)
 *
 * Why: Allows users to focus on a single narrative thread at a time by filtering
 * the Weaver canvas to show only scenes belonging to the selected plotline.
 */
import { useEffect } from 'react';
import { Filter, X } from 'lucide-react';
import { usePlotlines } from '@/features/director';
import { useWeaverFilteredPlotlineId, useWeaverSetFilteredPlotlineId } from '../store/weaverStore';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

/**
 * PlotlineFilter component
 *
 * - Shows dropdown of all plotlines
 * - When filtering: dims scenes not in the plotline (opacity 30%)
 * - Clear filter button resets the view
 * - Keyboard shortcut: Ctrl+L to toggle filter menu
 */
export function PlotlineFilter() {
  const { data: plotlines, isLoading } = usePlotlines();
  const filteredPlotlineId = useWeaverFilteredPlotlineId();
  const setFilteredPlotlineId = useWeaverSetFilteredPlotlineId();

  const handleClearFilter = () => {
    setFilteredPlotlineId(null);
  };

  // Keyboard shortcut: Ctrl+L to focus the filter dropdown
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'l') {
        e.preventDefault();
        // Focus the select trigger
        const selectTrigger = document.querySelector(
          '[data-testid="plotline-filter-select"]'
        ) as HTMLElement;
        selectTrigger?.focus();
        selectTrigger?.click();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const selectedPlotline = plotlines?.plotlines.find((p) => p.id === filteredPlotlineId);

  return (
    <div className="flex items-center gap-2">
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex items-center gap-1">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <Select
                value={filteredPlotlineId ?? 'all'}
                onValueChange={(value) => setFilteredPlotlineId(value === 'all' ? null : value)}
                data-testid="plotline-filter-select"
              >
                <SelectTrigger className="w-[180px]" aria-label="Filter by plotline">
                  <SelectValue placeholder="All Plotlines" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Plotlines</SelectItem>
                  {isLoading ? (
                    <SelectItem value="loading" disabled>
                      Loading...
                    </SelectItem>
                  ) : (
                    plotlines?.plotlines.map((plotline) => (
                      <SelectItem key={plotline.id} value={plotline.id}>
                        <div className="flex items-center gap-2">
                          <div
                            className="h-3 w-3 rounded-full"
                            style={{ backgroundColor: plotline.color }}
                          />
                          <span>{plotline.name}</span>
                        </div>
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <p>Filter by plotline (Ctrl+L)</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      {filteredPlotlineId && (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleClearFilter}
                aria-label="Clear filter"
              >
                <X className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Clear filter</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}

      {selectedPlotline && (
        <div
          className="flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium"
          style={{
            backgroundColor: `${selectedPlotline.color}20`,
            color: selectedPlotline.color,
            border: `1px solid ${selectedPlotline.color}40`,
          }}
        >
          <div
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: selectedPlotline.color }}
          />
          <span>{selectedPlotline.name}</span>
        </div>
      )}
    </div>
  );
}
