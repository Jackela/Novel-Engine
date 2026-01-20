/**
 * CharacterGrid - Grid display of characters
 */
import { Plus, Search } from 'lucide-react';
import { useState } from 'react';
import { Button, Input } from '@/shared/components/ui';
import { LoadingSpinner, EmptyState } from '@/shared/components/feedback';
import { CharacterCard } from './CharacterCard';
import type { Character } from '@/shared/types/character';

interface CharacterGridProps {
  characters: Character[];
  isLoading?: boolean;
  onCreateNew?: () => void;
  onEdit?: (character: Character) => void;
  onDelete?: (id: string) => void;
  onSelect?: (character: Character) => void;
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
      char.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      char.traits.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  if (isLoading) {
    return <LoadingSpinner fullScreen text="Loading characters..." />;
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search characters..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        {onCreateNew && (
          <Button onClick={onCreateNew}>
            <Plus className="h-4 w-4 mr-2" />
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
          action={
            !searchQuery && onCreateNew
              ? { label: 'Create Character', onClick: onCreateNew }
              : undefined
          }
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredCharacters.map((character) => (
            <CharacterCard
              key={character.id}
              character={character}
              onEdit={onEdit}
              onDelete={onDelete}
              onSelect={onSelect}
              selected={character.id === selectedId}
            />
          ))}
        </div>
      )}
    </div>
  );
}
