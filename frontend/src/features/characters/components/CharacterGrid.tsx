/**
 * CharacterGrid - Grid display of characters
 */
import { Plus, Search } from 'lucide-react';
import { useState } from 'react';
import { Button, Input } from '@/shared/components/ui';
import { LoadingSpinner, EmptyState } from '@/shared/components/feedback';
import { CharacterCard } from './CharacterCard';
import type { CharacterSummary } from '@/shared/types/character';

interface CharacterGridProps {
  characters: CharacterSummary[];
  isLoading?: boolean;
  onCreateNew?: () => void;
  onEdit?: (character: CharacterSummary) => void;
  onDelete?: (id: string) => void;
  onSelect?: (character: CharacterSummary) => void;
  selectedId?: string;
}

export function CharacterGrid({
  characters,
  isLoading = false,
  onCreateNew,
  onEdit,
  onDelete,
  onSelect,
  selectedId,
}: CharacterGridProps) {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredCharacters = characters.filter(
    (char) =>
      char.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      char.status.toLowerCase().includes(searchQuery.toLowerCase()) ||
      char.type.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (isLoading) {
    return <LoadingSpinner fullScreen text="Loading characters..." />;
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative max-w-sm flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search characters..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        {onCreateNew && (
          <Button onClick={onCreateNew}>
            <Plus className="mr-2 h-4 w-4" />
            New Character
          </Button>
        )}
      </div>

      {/* Grid or Empty State */}
      {filteredCharacters.length === 0 ? (
        <EmptyState
          title={searchQuery ? 'No matches found' : 'No characters yet'}
          description={
            searchQuery
              ? 'Try adjusting your search terms'
              : 'Create your first character to get started'
          }
          {...(!searchQuery && onCreateNew
            ? { action: { label: 'Create Character', onClick: onCreateNew } }
            : {})}
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filteredCharacters.map((character) => (
            <CharacterCard
              key={character.id}
              character={character}
              {...(onEdit ? { onEdit } : {})}
              {...(onDelete ? { onDelete } : {})}
              {...(onSelect ? { onSelect } : {})}
              selected={character.id === selectedId}
            />
          ))}
        </div>
      )}
    </div>
  );
}
