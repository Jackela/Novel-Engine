/**
 * WorldSidebarTab - Sidebar tab for world entities (characters, locations)
 *
 * Why: Provides quick access to world entities within the narrative editor,
 * allowing writers to reference characters and locations without leaving
 * their current editing context. Supports dragging characters into the
 * editor to insert @mentions.
 *
 * CHAR-037: Added sort/filter functionality for character list.
 * - Sort by: Name (A-Z), Faction, Role (archetype)
 */
import { useState, useCallback, useMemo } from 'react';
import { Users, MapPin, Globe, ChevronRight, ArrowUpDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/Select';
import { LocationTree } from '@/components/world/LocationTree';
import { DraggableCharacterItem } from '@/components/editor/DraggableCharacterItem';
import type { CharacterSummary } from '@/shared/types/character';
import type { WorldLocation } from '@/types/schemas';

/** Available sort options for the character list */
type CharacterSortOption = 'name' | 'faction' | 'role';

/** Compare two characters by faction (with faction first, then alphabetically) */
function compareByFaction(a: CharacterSummary, b: CharacterSummary): number {
  if (a.faction_id && !b.faction_id) return -1;
  if (!a.faction_id && b.faction_id) return 1;
  if (a.faction_id && b.faction_id) {
    const factionCompare = a.faction_id.localeCompare(b.faction_id);
    if (factionCompare !== 0) return factionCompare;
  }
  return a.name.localeCompare(b.name);
}

/** Compare two characters by role/archetype (with role first, then alphabetically) */
function compareByRole(a: CharacterSummary, b: CharacterSummary): number {
  const aRole = a.archetype ?? '';
  const bRole = b.archetype ?? '';
  if (aRole && !bRole) return -1;
  if (!aRole && bRole) return 1;
  const roleCompare = aRole.localeCompare(bRole);
  if (roleCompare !== 0) return roleCompare;
  return a.name.localeCompare(b.name);
}

/** Sort characters based on selected option */
function sortCharacters(
  characters: CharacterSummary[],
  sortBy: CharacterSortOption
): CharacterSummary[] {
  return [...characters].sort((a, b) => {
    switch (sortBy) {
      case 'name':
        return a.name.localeCompare(b.name);
      case 'faction':
        return compareByFaction(a, b);
      case 'role':
        return compareByRole(a, b);
      default:
        return 0;
    }
  });
}


/**
 * Collapsible section wrapper for sidebar sections.
 */
interface SidebarSectionProps {
  title: string;
  icon: React.ReactNode;
  count: number;
  defaultExpanded?: boolean;
  children: React.ReactNode;
}

function SidebarSection({
  title,
  icon,
  count,
  defaultExpanded = true,
  children,
}: SidebarSectionProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
      <CollapsibleTrigger className="flex w-full items-center gap-2 px-2 py-1.5 text-sm font-medium hover:bg-accent hover:text-accent-foreground rounded-md">
        <ChevronRight
          className={cn(
            'h-4 w-4 shrink-0 text-muted-foreground transition-transform',
            isExpanded && 'rotate-90'
          )}
        />
        {icon}
        <span>{title}</span>
        <span className="ml-auto text-xs text-muted-foreground">{count}</span>
      </CollapsibleTrigger>
      <CollapsibleContent className="pl-4">{children}</CollapsibleContent>
    </Collapsible>
  );
}

/** Loading state display */
function LoadingState({ className }: { className?: string | undefined }) {
  return (
    <div className={cn('flex flex-col items-center justify-center p-6', className)}>
      <Globe className="h-8 w-8 animate-pulse text-muted-foreground" />
      <p className="mt-2 text-sm text-muted-foreground">Loading world data...</p>
    </div>
  );
}

/** Empty state display */
function EmptyState({ className }: { className?: string | undefined }) {
  return (
    <div className={cn('flex flex-col items-center justify-center p-6 text-center', className)}>
      <Globe className="h-8 w-8 text-muted-foreground opacity-50" />
      <p className="mt-2 text-sm font-medium text-muted-foreground">No world data</p>
      <p className="text-xs text-muted-foreground">
        Create characters and locations to see them here
      </p>
    </div>
  );
}

/** Characters section content with sort/filter controls */
interface CharactersSectionProps {
  characters: CharacterSummary[];
  selectedCharacterId: string | null | undefined;
  onCharacterSelect: (id: string) => void;
}

function CharactersSection({
  characters,
  selectedCharacterId,
  onCharacterSelect,
}: CharactersSectionProps) {
  const [sortBy, setSortBy] = useState<CharacterSortOption>('name');
  const [isExpanded, setIsExpanded] = useState(true);

  // Sort characters based on selected option
  const sortedCharacters = useMemo(
    () => sortCharacters(characters, sortBy),
    [characters, sortBy]
  );

  // Show all characters when sorted, otherwise limit to 5
  const displayedCharacters = sortedCharacters;
  const characterCount = characters.length;

  return (
    <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
      <div className="flex items-center gap-2 px-2 py-1.5">
        <CollapsibleTrigger className="flex flex-1 items-center gap-2 text-sm font-medium hover:text-accent-foreground rounded-md">
          <ChevronRight
            className={cn(
              'h-4 w-4 shrink-0 text-muted-foreground transition-transform',
              isExpanded && 'rotate-90'
            )}
          />
          <Users className="h-4 w-4 shrink-0 text-muted-foreground" />
          <span>Characters</span>
          <span className="text-xs text-muted-foreground">({characterCount})</span>
        </CollapsibleTrigger>
        {/* Sort dropdown - only show when expanded and has characters */}
        {isExpanded && characterCount > 1 && (
          <Select value={sortBy} onValueChange={(val) => setSortBy(val as CharacterSortOption)}>
            <SelectTrigger
              className="h-6 w-auto min-w-[70px] gap-1 px-2 text-xs"
              onClick={(e) => e.stopPropagation()}
            >
              <ArrowUpDown className="h-3 w-3" />
              <SelectValue placeholder="Sort" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="name">Name</SelectItem>
              <SelectItem value="faction">Faction</SelectItem>
              <SelectItem value="role">Role</SelectItem>
            </SelectContent>
          </Select>
        )}
      </div>
      <CollapsibleContent className="pl-4">
        <ScrollArea className="max-h-[300px]">
          <div className="mt-1 space-y-0.5 pr-2">
            {displayedCharacters.map((character) => (
              <DraggableCharacterItem
                key={character.id}
                character={character}
                isSelected={character.id === selectedCharacterId}
                onSelect={onCharacterSelect}
              />
            ))}
            {characterCount === 0 && (
              <p className="px-2 py-1 text-xs text-muted-foreground italic">
                No characters found
              </p>
            )}
          </div>
        </ScrollArea>
      </CollapsibleContent>
    </Collapsible>
  );
}

/** Locations section content */
interface LocationsSectionProps {
  locations: WorldLocation[];
  selectedLocationId: string | null | undefined;
  onLocationSelect: (id: string) => void;
}

function LocationsSection({
  locations,
  selectedLocationId,
  onLocationSelect,
}: LocationsSectionProps) {
  return (
    <SidebarSection
      title="Locations"
      icon={<MapPin className="h-4 w-4 shrink-0 text-muted-foreground" />}
      count={locations.length}
      defaultExpanded={false}
    >
      <div className="mt-1">
        <LocationTree
          locations={locations}
          selectedId={selectedLocationId ?? null}
          onSelect={onLocationSelect}
          defaultExpandedIds={[]}
        />
      </div>
    </SidebarSection>
  );
}

export interface WorldSidebarTabProps {
  /** Characters to display (top 5 shown) */
  characters: CharacterSummary[];
  /** Locations to display */
  locations: WorldLocation[];
  /** Whether data is still loading */
  isLoading: boolean;
  /** Selected character ID */
  selectedCharacterId?: string | null;
  /** Selected location ID */
  selectedLocationId?: string | null;
  /** Called when a character is selected */
  onCharacterSelect?: (characterId: string) => void;
  /** Called when a location is selected */
  onLocationSelect?: (locationId: string) => void;
  /** Additional CSS classes */
  className?: string;
}

/**
 * WorldSidebarTab displays a compact view of world entities for the narrative sidebar.
 */
export function WorldSidebarTab({
  characters,
  locations,
  isLoading,
  selectedCharacterId,
  selectedLocationId,
  onCharacterSelect,
  onLocationSelect,
  className,
}: WorldSidebarTabProps) {
  const handleCharacterSelect = useCallback(
    (id: string) => onCharacterSelect?.(id),
    [onCharacterSelect]
  );

  const handleLocationSelect = useCallback(
    (id: string) => onLocationSelect?.(id),
    [onLocationSelect]
  );

  if (isLoading) return <LoadingState className={className} />;
  if (characters.length === 0 && locations.length === 0) {
    return <EmptyState className={className} />;
  }

  return (
    <ScrollArea className={cn('flex-1', className)}>
      <div className="space-y-4 p-2">
        <CharactersSection
          characters={characters}
          selectedCharacterId={selectedCharacterId}
          onCharacterSelect={handleCharacterSelect}
        />
        <LocationsSection
          locations={locations}
          selectedLocationId={selectedLocationId}
          onLocationSelect={handleLocationSelect}
        />
      </div>
    </ScrollArea>
  );
}

export default WorldSidebarTab;
