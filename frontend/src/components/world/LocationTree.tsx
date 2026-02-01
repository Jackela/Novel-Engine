/**
 * LocationTree - Recursive tree view for location hierarchy navigation
 *
 * Why: Provides a file-explorer style interface for navigating hierarchical
 * world locations (Continent > Region > City > Building). Uses shadcn/ui
 * Collapsible for expand/collapse and lucide-react icons for location types.
 */
import { useCallback, useMemo, useState } from 'react';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  ChevronRight,
  Globe,
  Map,
  Flag,
  MapPin,
  Building2,
  Home,
  Tent,
  Castle,
  Skull,
  Church,
  TreePine,
  Mountain,
  Waves,
  Droplets,
  Sun,
  CloudRain,
  LandPlot,
  Palmtree,
  Warehouse,
  Landmark,
  Building,
  Anchor,
  Rocket,
  Moon,
  Sparkles,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { WorldLocation, LocationType } from '@/types/schemas';

/**
 * Map LocationType to appropriate lucide-react icon.
 * Why: Visual icons help users quickly identify location types in the tree.
 */
const LOCATION_ICONS: Record<LocationType, LucideIcon> = {
  continent: Globe,
  region: Map,
  country: Flag,
  province: MapPin,
  city: Building2,
  town: Home,
  village: Tent,
  fortress: Castle,
  castle: Castle,
  dungeon: Skull,
  temple: Church,
  forest: TreePine,
  mountain: Mountain,
  ocean: Waves,
  river: Droplets,
  desert: Sun,
  swamp: CloudRain,
  plains: LandPlot,
  island: Palmtree,
  cave: Warehouse,
  ruins: Landmark,
  landmark: Landmark,
  capital: Building,
  port: Anchor,
  space_station: Rocket,
  planet: Moon,
  dimension: Sparkles,
};

/**
 * Get the icon component for a location type.
 * Falls back to MapPin if type is unknown.
 */
function getLocationIcon(locationType: string): LucideIcon {
  return LOCATION_ICONS[locationType as LocationType] || MapPin;
}

/**
 * Build a tree structure from flat location array.
 * Why: API returns flat array with parent_id references; we need nested structure
 * for recursive rendering.
 */
interface LocationNode extends WorldLocation {
  children: LocationNode[];
}

function buildLocationTree(locations: WorldLocation[]): LocationNode[] {
  // Use object map for faster lookups without Map constructor issues
  const locationMap: Record<string, LocationNode> = {};
  const rootNodes: LocationNode[] = [];

  // First pass: create node objects with empty children arrays
  for (const location of locations) {
    locationMap[location.id] = { ...location, children: [] };
  }

  // Second pass: build parent-child relationships
  for (const location of locations) {
    const node = locationMap[location.id];
    if (!node) continue;

    const parentId = location.parent_location_id;
    if (parentId) {
      const parent = locationMap[parentId];
      if (parent) {
        parent.children.push(node);
        continue;
      }
    }
    // No parent or parent not found = root node
    rootNodes.push(node);
  }

  return rootNodes;
}

export interface LocationTreeItemProps {
  /** The location node to render */
  node: LocationNode;
  /** Current depth level (for indentation) */
  depth?: number | undefined;
  /** Currently selected location ID */
  selectedId: string | null | undefined;
  /** Callback when a location is selected */
  onSelect: ((locationId: string) => void) | undefined;
  /** Set of expanded node IDs */
  expandedIds: Set<string>;
  /** Toggle expansion state of a node */
  onToggleExpand: (locationId: string) => void;
}

/**
 * LocationTreeItem - Recursive component for a single tree node.
 */
function LocationTreeItem({
  node,
  depth = 0,
  selectedId,
  onSelect,
  expandedIds,
  onToggleExpand,
}: LocationTreeItemProps) {
  const hasChildren = node.children.length > 0;
  const isExpanded = expandedIds.has(node.id);
  const isSelected = selectedId === node.id;
  const Icon = getLocationIcon(node.location_type);

  const handleSelect = useCallback(() => {
    onSelect?.(node.id);
  }, [onSelect, node.id]);

  const handleToggle = useCallback(() => {
    if (hasChildren) {
      onToggleExpand(node.id);
    }
  }, [hasChildren, onToggleExpand, node.id]);

  // Prevent click propagation when toggling expand
  const handleChevronClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      handleToggle();
    },
    [handleToggle]
  );

  return (
    <Collapsible open={isExpanded} onOpenChange={handleToggle}>
      <div
        className={cn(
          'flex items-center gap-1 rounded-md px-2 py-1.5 text-sm transition-colors',
          'hover:bg-accent hover:text-accent-foreground',
          'cursor-pointer select-none',
          isSelected && 'bg-accent text-accent-foreground font-medium'
        )}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
        onClick={handleSelect}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleSelect();
          }
          if (e.key === 'ArrowRight' && hasChildren && !isExpanded) {
            e.preventDefault();
            handleToggle();
          }
          if (e.key === 'ArrowLeft' && hasChildren && isExpanded) {
            e.preventDefault();
            handleToggle();
          }
        }}
        role="treeitem"
        aria-selected={isSelected}
        aria-expanded={hasChildren ? isExpanded : undefined}
        tabIndex={0}
      >
        {/* Expand/collapse chevron or spacer */}
        {hasChildren ? (
          <CollapsibleTrigger asChild onClick={handleChevronClick}>
            <button
              type="button"
              className="flex h-4 w-4 shrink-0 items-center justify-center rounded hover:bg-muted"
              aria-label={isExpanded ? 'Collapse' : 'Expand'}
            >
              <ChevronRight
                className={cn(
                  'h-3.5 w-3.5 text-muted-foreground transition-transform',
                  isExpanded && 'rotate-90'
                )}
              />
            </button>
          </CollapsibleTrigger>
        ) : (
          <span className="w-4 shrink-0" />
        )}

        {/* Location type icon */}
        <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />

        {/* Location name */}
        <span className="truncate">{node.name}</span>

        {/* Child count badge */}
        {hasChildren && (
          <span className="ml-auto text-xs text-muted-foreground">
            {node.children.length}
          </span>
        )}
      </div>

      {/* Render children recursively */}
      {hasChildren && (
        <CollapsibleContent>
          {node.children.map((child) => (
            <LocationTreeItem
              key={child.id}
              node={child}
              depth={depth + 1}
              selectedId={selectedId}
              onSelect={onSelect}
              expandedIds={expandedIds}
              onToggleExpand={onToggleExpand}
            />
          ))}
        </CollapsibleContent>
      )}
    </Collapsible>
  );
}

export interface LocationTreeProps {
  /** Array of locations (flat structure with parent_id references) */
  locations: WorldLocation[];
  /** Optional CSS class name */
  className?: string;
  /** Currently selected location ID */
  selectedId?: string | null;
  /** Callback when a location is selected */
  onSelect?: (locationId: string) => void;
  /** IDs to expand by default */
  defaultExpandedIds?: string[];
}

/**
 * LocationTree renders a file-explorer style tree view for location hierarchy.
 *
 * Why: Writers need to navigate complex world hierarchies (e.g., Kingdom > Province
 * > City > District > Building). A tree view provides intuitive spatial navigation.
 *
 * @example
 * ```tsx
 * <LocationTree
 *   locations={locations}
 *   selectedId={selectedLocationId}
 *   onSelect={(id) => setSelectedLocationId(id)}
 * />
 * ```
 */
export function LocationTree({
  locations,
  className,
  selectedId,
  onSelect,
  defaultExpandedIds = [],
}: LocationTreeProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(
    () => new Set(defaultExpandedIds)
  );

  // Build tree structure from flat array
  const tree = useMemo(() => buildLocationTree(locations), [locations]);

  // Toggle expansion state
  const handleToggleExpand = useCallback((locationId: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(locationId)) {
        next.delete(locationId);
      } else {
        next.add(locationId);
      }
      return next;
    });
  }, []);

  if (locations.length === 0) {
    return (
      <div
        className={cn(
          'flex flex-col items-center justify-center p-6 text-center text-muted-foreground',
          className
        )}
        role="tree"
        aria-label="Location hierarchy"
      >
        <Globe className="mb-2 h-8 w-8 opacity-50" />
        <p className="text-sm font-medium">No locations yet</p>
        <p className="text-xs">Create locations to see them here</p>
      </div>
    );
  }

  return (
    <div
      className={cn('flex flex-col gap-0.5', className)}
      role="tree"
      aria-label="Location hierarchy"
    >
      {tree.map((node) => (
        <LocationTreeItem
          key={node.id}
          node={node}
          selectedId={selectedId}
          onSelect={onSelect}
          expandedIds={expandedIds}
          onToggleExpand={handleToggleExpand}
        />
      ))}
    </div>
  );
}

export default LocationTree;
