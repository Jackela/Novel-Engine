/**
 * WorldSidebarTab - Sidebar tab for world entities (characters, locations)
 *
 * Why: Provides quick access to world entities within the narrative editor,
 * allowing writers to reference characters and locations without leaving
 * their current editing context.
 */
import { useState, useCallback } from 'react';
import { Users, MapPin, Globe, ChevronRight, User } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { LocationTree } from '@/components/world/LocationTree';
import type { CharacterSummary } from '@/shared/types/character';
import type { WorldLocation } from '@/types/schemas';

/**
 * Props for mini character item used in the sidebar.
 */
interface MiniCharacterItemProps {
  character: CharacterSummary;
  isSelected: boolean;
  onSelect: (id: string) => void;
}

/**
 * Compact character list item for sidebar display.
 */
function MiniCharacterItem({
  character,
  isSelected,
  onSelect,
}: MiniCharacterItemProps) {
  const handleClick = useCallback(() => {
    onSelect(character.id);
  }, [onSelect, character.id]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onSelect(character.id);
      }
    },
    [onSelect, character.id]
  );

  return (
    <div
      className={cn(
        'flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm',
        'transition-colors hover:bg-accent hover:text-accent-foreground',
        isSelected && 'bg-accent text-accent-foreground font-medium'
      )}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
    >
      <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-muted">
        <User className="h-3.5 w-3.5 text-muted-foreground" />
      </div>
      <span className="truncate">{character.name}</span>
      {character.archetype && (
        <span className="ml-auto shrink-0 text-xs text-muted-foreground">
          {character.archetype}
        </span>
      )}
    </div>
  );
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

/** Characters section content */
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
  const displayedCharacters = characters.slice(0, 5);
  const hasMoreCharacters = characters.length > 5;

  return (
    <SidebarSection
      title="Characters"
      icon={<Users className="h-4 w-4 shrink-0 text-muted-foreground" />}
      count={characters.length}
      defaultExpanded={true}
    >
      <div className="mt-1 space-y-0.5">
        {displayedCharacters.map((character) => (
          <MiniCharacterItem
            key={character.id}
            character={character}
            isSelected={character.id === selectedCharacterId}
            onSelect={onCharacterSelect}
          />
        ))}
        {hasMoreCharacters && (
          <p className="px-2 py-1 text-xs text-muted-foreground">
            +{characters.length - 5} more...
          </p>
        )}
      </div>
    </SidebarSection>
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
