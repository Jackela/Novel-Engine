/**
 * LocationTree - Recursive tree view for location hierarchy navigation
 *
 * Why: Provides a file-explorer style interface for navigating hierarchical
 * world locations (Continent > Region > City > Building). Uses shadcn/ui
 * Collapsible for expand/collapse and lucide-react icons for location types.
 *
 * SIM-023: Now supports displaying characters at each location with avatar display,
 * filter toggle, and CharacterDetailDialog for viewing character details.
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
  UserX,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { WorldLocation, LocationType, CharacterSummary } from '@/types/schemas';
import { Avatar, AvatarFallback, AvatarImage } from '@/shared/components/ui/Avatar';
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
import { Button } from '@/components/ui/button';

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
 * Get initials from a character name for avatar fallback.
 */
function getInitials(name: string): string {
  return name
    .split(' ')
    .map((word) => word[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
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

/**
 * CharacterAvatarGroup - Display a group of character avatars under a location.
 * Shows max 5 visible avatars with "+N more" overflow indicator.
 * Status indicator ring: green=alive, gray=deceased (SIM-023).
 */
interface CharacterAvatarGroupProps {
  characters: CharacterSummary[];
  onCharacterClick: (character: CharacterSummary) => void;
  maxVisible?: number;
}

function CharacterAvatarGroup({
  characters,
  onCharacterClick,
  maxVisible = 5,
}: CharacterAvatarGroupProps) {
  const visibleCharacters = characters.slice(0, maxVisible);
  const overflowCount = characters.length - maxVisible;

  return (
    <TooltipProvider>
      <div
        className="flex flex-wrap items-center gap-1 pl-6 pt-1"
        role="group"
        aria-label={`${characters.length} character${characters.length !== 1 ? 's' : ''} at this location`}
      >
        {visibleCharacters.map((character) => {
          // SIM-019: Status indicator ring - green for alive, gray for deceased
          const statusRingClass = character.is_deceased
            ? 'ring-gray-400'
            : 'ring-green-500';
          const ariaStatusText = character.is_deceased ? 'deceased' : 'alive';

          return (
            <Tooltip key={character.id}>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onCharacterClick(character);
                  }}
                  className="focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1 rounded-full"
                  aria-label={`${character.name}, ${ariaStatusText}`}
                >
                  <Avatar
                    size="sm"
                    className={cn(
                      'ring-2 ring-offset-1 hover:ring-primary transition-shadow',
                      statusRingClass
                    )}
                  >
                    <AvatarImage src={character.appearance ?? undefined} alt={character.name} />
                    <AvatarFallback>{getInitials(character.name)}</AvatarFallback>
                  </Avatar>
                </button>
              </TooltipTrigger>
              <TooltipContent side="top">
                <p className="font-medium">{character.name}</p>
                <p className="text-xs text-muted-foreground">
                  {character.is_deceased ? 'Deceased' : character.status}
                </p>
              </TooltipContent>
            </Tooltip>
          );
        })}
        {overflowCount > 0 && (
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-xs font-medium text-muted-foreground">
                +{overflowCount}
              </span>
            </TooltipTrigger>
            <TooltipContent side="top">
              <p>{overflowCount} more character{overflowCount !== 1 ? 's' : ''}</p>
            </TooltipContent>
          </Tooltip>
        )}
      </div>
    </TooltipProvider>
  );
}

/**
 * CharacterDetailDialog - Minimal dialog showing character details.
 */
interface CharacterDetailDialogProps {
  character: CharacterSummary | null;
  open: boolean;
  onClose: () => void;
}

function CharacterDetailDialog({ character, open, onClose }: CharacterDetailDialogProps) {
  if (!character) return null;

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-w-md" aria-modal="true">
        <DialogHeader>
          <DialogTitle>{character.name}</DialogTitle>
          <DialogDescription>Character details</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 text-sm">
          <div className="flex items-center gap-3">
            <Avatar size="lg">
              <AvatarImage src={character.appearance ?? undefined} alt={character.name} />
              <AvatarFallback>{getInitials(character.name)}</AvatarFallback>
            </Avatar>
            <div>
              <p className="font-medium">{character.name}</p>
              <p className="text-muted-foreground">{character.status}</p>
            </div>
          </div>

          {character.archetype && (
            <div>
              <span className="text-muted-foreground">Archetype: </span>
              <span className="font-medium">{character.archetype}</span>
            </div>
          )}

          {character.traits && character.traits.length > 0 && (
            <div>
              <span className="text-muted-foreground">Traits: </span>
              <span>{character.traits.join(', ')}</span>
            </div>
          )}

          <div>
            <span className="text-muted-foreground">Type: </span>
            <span>{character.type}</span>
          </div>

          {character.faction_id && (
            <div>
              <span className="text-muted-foreground">Faction: </span>
              <span>{character.faction_id}</span>
            </div>
          )}
        </div>
        <div className="flex justify-end">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
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
  /** Characters at this location (SIM-023) */
  charactersAtLocation?: CharacterSummary[];
  /** Whether to show characters (SIM-023) */
  showCharacters?: boolean;
  /** Callback when character is clicked (SIM-023) */
  onCharacterClick?: ((character: CharacterSummary) => void) | undefined;
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
  charactersAtLocation = [],
  showCharacters = false,
  onCharacterClick,
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
          isSelected && 'bg-accent font-medium text-accent-foreground'
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

      {/* Character avatars under this location (SIM-023) */}
      {showCharacters && charactersAtLocation.length > 0 && (
        <div style={{ paddingLeft: `${depth * 12 + 8}px` }}>
          <CharacterAvatarGroup
            characters={charactersAtLocation}
            onCharacterClick={onCharacterClick ?? (() => {})}
          />
        </div>
      )}

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
              charactersAtLocation={charactersAtLocation}
              showCharacters={showCharacters}
              onCharacterClick={onCharacterClick}
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
  /** Characters to display at locations (SIM-023) */
  characters?: CharacterSummary[];
  /** Whether to show characters (SIM-023) */
  showCharacters?: boolean;
  /** Callback when character is clicked (SIM-023) */
  onCharacterClick?: ((character: CharacterSummary) => void) | undefined;
}

/**
 * Build a map of location ID to characters at that location.
 * Characters without a valid location go to "unknown" category.
 */
function buildLocationCharacterMap(
  characters: CharacterSummary[],
  locations: WorldLocation[]
): Record<string, CharacterSummary[]> {
  const locationIds = new Set(locations.map((loc) => loc.id));
  const map: Record<string, CharacterSummary[]> = {};

  for (const character of characters) {
    // SIM-020: Use current_location_id to determine character location
    const locationId = character.current_location_id ?? null;

    if (locationId && locationIds.has(locationId)) {
      const existing = map[locationId] ?? [];
      existing.push(character);
      map[locationId] = existing;
    }
    // Characters without valid location will be shown in "Unknown Location" section
  }

  return map;
}

/**
 * Get characters without a valid location.
 */
function getCharactersWithoutLocation(
  characters: CharacterSummary[],
  locations: WorldLocation[]
): CharacterSummary[] {
  const locationIds = new Set(locations.map((loc) => loc.id));
  return characters.filter((char) => {
    // SIM-020: Use current_location_id to determine character location
    const locationId = char.current_location_id ?? null;
    return !locationId || !locationIds.has(locationId);
  });
}

/**
 * LocationTree renders a file-explorer style tree view for location hierarchy.
 *
 * Why: Writers need to navigate complex world hierarchies (e.g., Kingdom > Province
 * > City > District > Building). A tree view provides intuitive spatial navigation.
 *
 * SIM-023: Now supports displaying characters at each location with toggle filter.
 *
 * @example
 * ```tsx
 * <LocationTree
 *   locations={locations}
 *   selectedId={selectedLocationId}
 *   onSelect={(id) => setSelectedLocationId(id)}
 *   characters={characters}
 *   showCharacters={showCharacters}
 *   onCharacterClick={(char) => openCharacterDialog(char)}
 * />
 * ```
 */
export function LocationTree({
  locations,
  className,
  selectedId,
  onSelect,
  defaultExpandedIds = [],
  characters = [],
  showCharacters = false,
  onCharacterClick,
}: LocationTreeProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(
    () => new Set(defaultExpandedIds)
  );
  const [selectedCharacter, setSelectedCharacter] = useState<CharacterSummary | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  // Build tree structure from flat array
  const tree = useMemo(() => buildLocationTree(locations), [locations]);

  // Build location to characters map
  const locationCharacterMap = useMemo(
    () => buildLocationCharacterMap(characters, locations),
    [characters, locations]
  );

  // Get characters without valid location
  const orphanedCharacters = useMemo(
    () => getCharactersWithoutLocation(characters, locations),
    [characters, locations]
  );

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

  // Handle character click
  const handleCharacterClick = useCallback((character: CharacterSummary) => {
    setSelectedCharacter(character);
    setDialogOpen(true);
    onCharacterClick?.(character);
  }, [onCharacterClick]);

  if (locations.length === 0) {
    return (
      <div
        className={cn(
          'flex flex-col items-center justify-center p-6 text-center text-muted-foreground',
          className
        )}
        role="tree"
        aria-label="World locations and characters"
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
      aria-label="World locations and characters"
    >
      {tree.map((node) => (
        <LocationTreeItem
          key={node.id}
          node={node}
          selectedId={selectedId}
          onSelect={onSelect}
          expandedIds={expandedIds}
          onToggleExpand={handleToggleExpand}
          charactersAtLocation={locationCharacterMap[node.id] ?? []}
          showCharacters={showCharacters}
          onCharacterClick={handleCharacterClick}
        />
      ))}

      {/* Unknown Location section for characters without valid location */}
      {showCharacters && orphanedCharacters.length > 0 && (
        <div className="mt-4 border-t pt-2">
          <div className="flex items-center gap-2 px-2 py-1.5 text-sm text-muted-foreground">
            <UserX className="h-4 w-4" />
            <span>Unknown Location</span>
            <span className="text-xs">({orphanedCharacters.length})</span>
          </div>
          <div className="pl-2">
            <CharacterAvatarGroup
              characters={orphanedCharacters}
              onCharacterClick={handleCharacterClick}
            />
          </div>
        </div>
      )}

      {/* Character detail dialog */}
      <CharacterDetailDialog
        character={selectedCharacter}
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
      />
    </div>
  );
}

export default LocationTree;
