/**
 * CharacterMentionView - React component for rendering character mentions with hover cards.
 *
 * Why: Replaces the static HTML rendering of character mentions with a React component
 * that can display rich hover cards showing character details. Uses Tiptap's
 * NodeViewWrapper for proper integration with the editor.
 */
import { NodeViewWrapper, type NodeViewProps } from '@tiptap/react';
import { useQuery } from '@tanstack/react-query';
import { User } from 'lucide-react';

import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from '@/components/ui/hover-card';
import { Badge } from '@/components/ui/badge';
import { api } from '@/lib/api';
import { CharacterDetailSchema } from '@/types/schemas';

/**
 * Fetches character details for hover card display.
 *
 * Why: Separate fetch function allows TanStack Query to cache character data,
 * avoiding redundant API calls when hovering the same character multiple times.
 */
async function fetchCharacterForHover(characterId: string) {
  const data = await api.get<unknown>(`/characters/${characterId}`);
  return CharacterDetailSchema.parse(data);
}

/**
 * Truncates text to specified length with ellipsis.
 */
function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength).trim() + '...';
}

/**
 * Avatar placeholder component.
 *
 * Why: Provides consistent avatar styling without requiring external
 * avatar component library. Uses character initials as fallback.
 */
function AvatarPlaceholder({ name }: { name: string }) {
  const initials = name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
      {initials ? (
        <span className="text-lg font-semibold text-muted-foreground">{initials}</span>
      ) : (
        <User className="h-6 w-6 text-muted-foreground" />
      )}
    </div>
  );
}

/**
 * Character hover card content component.
 *
 * Why: Extracted to separate component to keep the main view component
 * focused on the mention rendering logic.
 */
function CharacterHoverContent({ characterId }: { characterId: string }) {
  const {
    data: character,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['characters', characterId, 'hover'],
    queryFn: () => fetchCharacterForHover(characterId),
    // Stale time of 5 minutes to reduce API calls
    staleTime: 5 * 60 * 1000,
    // Only fetch when character ID is valid
    enabled: !!characterId,
  });

  if (isLoading) {
    return (
      <div className="flex items-center gap-3">
        <div className="h-12 w-12 animate-pulse rounded-full bg-muted" />
        <div className="space-y-2">
          <div className="h-4 w-24 animate-pulse rounded bg-muted" />
          <div className="h-3 w-16 animate-pulse rounded bg-muted" />
        </div>
      </div>
    );
  }

  if (error || !character) {
    return (
      <div className="text-sm text-muted-foreground">
        Unable to load character details
      </div>
    );
  }

  // Extract description from background_summary or fallback to personality_traits
  const description =
    character.background_summary || character.personality_traits || '';
  const truncatedDescription = truncateText(description, 100);

  return (
    <div className="flex gap-3">
      <AvatarPlaceholder name={character.name} />
      <div className="flex-1 space-y-1">
        <div className="flex items-center gap-2">
          <span className="font-semibold">{character.name}</span>
          {character.current_status && (
            <Badge variant="outline" className="text-xs">
              {character.current_status}
            </Badge>
          )}
        </div>
        {truncatedDescription && (
          <p className="text-sm leading-snug text-muted-foreground">
            {truncatedDescription}
          </p>
        )}
      </div>
    </div>
  );
}

/**
 * CharacterMentionView - NodeView component for character mentions.
 *
 * Why: Using NodeViewWrapper with a React component allows us to integrate
 * interactive elements (like HoverCard) that wouldn't be possible with
 * plain HTML rendering. The hover card shows 300ms after hover starts
 * (Radix default) and hides immediately on mouse leave.
 */
export function CharacterMentionView({ node }: NodeViewProps) {
  const characterId = node.attrs['characterId'] as string;
  const characterName = node.attrs['characterName'] as string;

  return (
    <NodeViewWrapper as="span" className="inline">
      <HoverCard openDelay={300} closeDelay={0}>
        <HoverCardTrigger asChild>
          <span
            className="character-mention cursor-pointer"
            data-character-mention=""
            data-character-id={characterId}
            data-character-name={characterName}
          >
            @{characterName}
          </span>
        </HoverCardTrigger>
        <HoverCardContent side="top" align="start" sideOffset={8} className="w-80">
          <CharacterHoverContent characterId={characterId} />
        </HoverCardContent>
      </HoverCard>
    </NodeViewWrapper>
  );
}

export default CharacterMentionView;
