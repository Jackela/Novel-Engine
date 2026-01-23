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
import { Card, CardHeader, CardTitle, CardContent } from '@/shared/components/ui';
import { ErrorState } from '@/shared/components/feedback';
import type {
  CreateCharacterInput,
  CharacterSummary,
  CharacterDetail,
} from '@/shared/types/character';

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
      {isFormOpen ? (
        <CharacterFormPanel
          selectedCharacter={selectedCharacter}
          selectedDetail={selectedDetail}
          isLoading={createMutation.isPending || updateMutation.isPending}
          onSubmit={handleSubmit}
          onCancel={() => {
            setIsFormOpen(false);
            setSelectedCharacter(null);
          }}
        />
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

type CharacterFormPanelProps = {
  selectedCharacter: CharacterSummary | null;
  selectedDetail?: CharacterDetail;
  isLoading: boolean;
  onSubmit: (data: CreateCharacterInput) => void;
  onCancel: () => void;
};

function CharacterFormPanel({
  selectedCharacter,
  selectedDetail,
  isLoading,
  onSubmit,
  onCancel,
}: CharacterFormPanelProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {selectedCharacter ? 'Edit Character' : 'Create Character'}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <CharacterForm
          {...(selectedDetail ? { character: selectedDetail } : {})}
          onSubmit={onSubmit}
          onCancel={onCancel}
          isLoading={isLoading}
        />
      </CardContent>
    </Card>
  );
}
