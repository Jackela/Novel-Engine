/**
 * DraggableCharacterItem - A draggable character item for the sidebar.
 *
 * Why: Enables drag-and-drop insertion of character mentions into the
 * Tiptap editor. Uses dnd-kit for consistent drag behavior with the
 * existing sidebar scene reordering functionality.
 */
import { useCallback } from 'react';
import { useDraggable } from '@dnd-kit/core';
import { User, GripVertical } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { CharacterSummary } from '@/shared/types/character';

/**
 * Data transferred during character drag operations.
 */
export interface CharacterDragData {
  type: 'character';
  characterId: string;
  characterName: string;
}

interface DraggableCharacterItemProps {
  character: CharacterSummary;
  isSelected: boolean;
  onSelect: (id: string) => void;
}

/**
 * DraggableCharacterItem renders a character list item that can be
 * dragged into the editor to insert an @mention.
 */
export function DraggableCharacterItem({
  character,
  isSelected,
  onSelect,
}: DraggableCharacterItemProps) {
  const dragData: CharacterDragData = {
    type: 'character',
    characterId: character.id,
    characterName: character.name,
  };

  const { attributes, listeners, setNodeRef, isDragging, transform } = useDraggable({
    id: `character-drag-${character.id}`,
    data: dragData,
  });

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

  const style = transform
    ? {
        transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
      }
    : undefined;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'group flex cursor-pointer items-center gap-1 rounded-md px-2 py-1.5 text-sm',
        'transition-colors hover:bg-accent hover:text-accent-foreground',
        isSelected && 'bg-accent font-medium text-accent-foreground',
        isDragging && 'z-50 opacity-50 shadow-lg'
      )}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
      data-testid={`draggable-character-${character.id}`}
    >
      {/* Drag handle - always visible to indicate draggability */}
      <div
        {...attributes}
        {...listeners}
        className="flex h-5 w-4 cursor-grab items-center justify-center text-muted-foreground opacity-40 transition-opacity hover:opacity-100"
        aria-label={`Drag ${character.name} to editor`}
      >
        <GripVertical className="h-3.5 w-3.5" />
      </div>

      {/* Avatar placeholder */}
      <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-muted">
        <User className="h-3.5 w-3.5 text-muted-foreground" />
      </div>

      {/* Character name */}
      <span className="truncate">{character.name}</span>

      {/* Archetype badge */}
      {character.archetype && (
        <span className="ml-auto shrink-0 text-xs text-muted-foreground">
          {character.archetype}
        </span>
      )}
    </div>
  );
}

/**
 * CharacterDragOverlay - Visual preview shown while dragging a character.
 */
export function CharacterDragOverlay({ name }: { name: string }) {
  return (
    <div className="flex items-center gap-2 rounded-md border border-primary bg-background px-3 py-2 shadow-lg">
      <User className="h-4 w-4 text-primary" />
      <span className="text-sm font-medium">@{name}</span>
    </div>
  );
}

export default DraggableCharacterItem;
