/**
 * CharactersPage - Characters management page
 */
import { useState } from 'react';
import { CharacterGrid } from './components/CharacterGrid';
import { CharacterForm } from './components/CharacterForm';
import CharacterDetailsDialog from './CharacterDetailsDialog';
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
  const [editingCharacter, setEditingCharacter] = useState<CharacterSummary | null>(
    null
  );
  const [detailsCharacter, setDetailsCharacter] = useState<CharacterSummary | null>(
    null
  );
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isDetailsOpen, setIsDetailsOpen] = useState(false);

  const { data: characters = [], isLoading, error } = useCharacters();
  const editingCharacterId = editingCharacter?.id ?? '';
  const detailsCharacterId = detailsCharacter?.id ?? '';
  const { data: editingDetail } = useCharacter(editingCharacterId);
  const { data: detailsDetail } = useCharacter(detailsCharacterId);
  const createMutation = useCreateCharacter();
  const updateMutation = useUpdateCharacter();
  const deleteMutation = useDeleteCharacter();

  const handleCreate = () => {
    setEditingCharacter(null);
    setIsFormOpen(true);
  };

  const handleEdit = (character: CharacterSummary) => {
    setEditingCharacter(character);
    setIsFormOpen(true);
  };

  const handleViewDetails = (character: CharacterSummary) => {
    setDetailsCharacter(character);
    setIsDetailsOpen(true);
  };

  const handleDelete = async (id: string) => {
    if (window.confirm('Are you sure you want to delete this character?')) {
      await deleteMutation.mutateAsync(id);
    }
  };

  const handleSubmit = async (data: CreateCharacterInput) => {
    if (editingCharacter) {
      const { agent_id: _agentId, ...payload } = data;
      await updateMutation.mutateAsync({ ...payload, id: editingCharacter.id });
    } else {
      await createMutation.mutateAsync(data);
    }
    setIsFormOpen(false);
    setEditingCharacter(null);
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
        onSelect={handleViewDetails}
        onDelete={handleDelete}
      />
      <Dialog
        open={isFormOpen}
        onOpenChange={(open) => {
          if (!open) {
            setIsFormOpen(false);
            setEditingCharacter(null);
          }
        }}
      >
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {editingCharacter ? 'Edit Character' : 'Create Character'}
            </DialogTitle>
          </DialogHeader>
          <CharacterForm
            {...(editingDetail ? { character: editingDetail } : {})}
            onSubmit={handleSubmit}
            onCancel={() => {
              setIsFormOpen(false);
              setEditingCharacter(null);
            }}
            isLoading={createMutation.isPending || updateMutation.isPending}
          />
        </DialogContent>
      </Dialog>
      <CharacterDetailsDialog
        open={isDetailsOpen && !!detailsDetail}
        onClose={() => {
          setIsDetailsOpen(false);
          setDetailsCharacter(null);
        }}
        character={detailsDetail ?? null}
      />
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
