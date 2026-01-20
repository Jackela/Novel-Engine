/**
 * CharactersPage - Characters management page
 */
import { useState } from 'react';
import { CharacterGrid } from './components/CharacterGrid';
import { CharacterForm } from './components/CharacterForm';
import { useCharacters, useCreateCharacter, useUpdateCharacter, useDeleteCharacter } from './api/characterApi';
import { Card, CardHeader, CardTitle, CardContent } from '@/shared/components/ui';
import { ErrorState } from '@/shared/components/feedback';
import type { Character, CreateCharacterInput } from '@/shared/types/character';

export default function CharactersPage() {
  const [selectedCharacter, setSelectedCharacter] = useState<Character | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);

  const { data: characters = [], isLoading, error } = useCharacters();
  const createMutation = useCreateCharacter();
  const updateMutation = useUpdateCharacter();
  const deleteMutation = useDeleteCharacter();

  const handleCreate = () => {
    setSelectedCharacter(null);
    setIsFormOpen(true);
  };

  const handleEdit = (character: Character) => {
    setSelectedCharacter(character);
    setIsFormOpen(true);
  };

  const handleDelete = async (id: string) => {
    if (window.confirm('Are you sure you want to delete this character?')) {
      await deleteMutation.mutateAsync(id);
    }
  };

  const handleSubmit = async (data: CreateCharacterInput) => {
    if (selectedCharacter) {
      await updateMutation.mutateAsync({ ...data, id: selectedCharacter.id });
    } else {
      await createMutation.mutateAsync(data);
    }
    setIsFormOpen(false);
    setSelectedCharacter(null);
  };

  if (error) {
    return (
      <ErrorState
        title="Failed to load characters"
        message={error.message}
        onRetry={() => window.location.reload()}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Characters</h1>
        <p className="text-muted-foreground">
          Manage your story characters and their relationships
        </p>
      </div>

      {/* Form or Grid */}
      {isFormOpen ? (
        <Card>
          <CardHeader>
            <CardTitle>
              {selectedCharacter ? 'Edit Character' : 'Create Character'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <CharacterForm
              character={selectedCharacter ?? undefined}
              onSubmit={handleSubmit}
              onCancel={() => {
                setIsFormOpen(false);
                setSelectedCharacter(null);
              }}
              isLoading={createMutation.isPending || updateMutation.isPending}
            />
          </CardContent>
        </Card>
      ) : (
        <CharacterGrid
          characters={characters}
          isLoading={isLoading}
          onCreateNew={handleCreate}
          onEdit={handleEdit}
          onDelete={handleDelete}
        />
      )}
    </div>
  );
}
