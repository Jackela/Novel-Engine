/**
 * CharactersPage - Characters management page
 */
import { useState } from 'react';
import { CharacterGrid } from './components/CharacterGrid';
import { CharacterForm } from './components/CharacterForm';
import {
  useCharacters,
  useCharacter,
  useCreateCharacter,
  useUpdateCharacter,
  useDeleteCharacter,
} from './api/characterApi';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { ErrorState } from '@/shared/components/feedback';
import type { CreateCharacterInput, CharacterSummary } from '@/shared/types/character';

export default function CharactersPage() {
  const [selectedCharacter, setSelectedCharacter] = useState<CharacterSummary | null>(
    null
  );
  const [isFormOpen, setIsFormOpen] = useState(false);

  const { data: characters = [], isLoading, error } = useCharacters();
  const selectedCharacterId = selectedCharacter?.id ?? '';
  const { data: selectedDetail } = useCharacter(selectedCharacterId);
  const createMutation = useCreateCharacter();
  const updateMutation = useUpdateCharacter();
  const deleteMutation = useDeleteCharacter();

  const handleCreate = () => {
    setSelectedCharacter(null);
    setIsFormOpen(true);
  };

  const handleEdit = (character: CharacterSummary) => {
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
      const { agent_id: _agentId, ...payload } = data;
      await updateMutation.mutateAsync({ ...payload, id: selectedCharacter.id });
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
      <CharactersHeader />
      <CharacterGrid
        characters={characters}
        isLoading={isLoading}
        onCreateNew={handleCreate}
        onEdit={handleEdit}
        onSelect={handleEdit}
        onDelete={handleDelete}
      />
      <Dialog
        open={isFormOpen}
        onOpenChange={(open) => {
          if (!open) {
            setIsFormOpen(false);
            setSelectedCharacter(null);
          }
        }}
      >
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {selectedCharacter ? 'Edit Character' : 'Create Character'}
            </DialogTitle>
          </DialogHeader>
          <CharacterForm
            {...(selectedDetail ? { character: selectedDetail } : {})}
            onSubmit={handleSubmit}
            onCancel={() => {
              setIsFormOpen(false);
              setSelectedCharacter(null);
            }}
            isLoading={createMutation.isPending || updateMutation.isPending}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}

function CharactersHeader() {
  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight">Characters</h1>
      <p className="text-muted-foreground">
        Manage your story characters and their relationships
      </p>
    </div>
  );
}
