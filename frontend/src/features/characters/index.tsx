import React, { useMemo, useState } from 'react';
import {
  Box,
  Grid,
  Typography,
  Button,
  Card,
  CardContent,
  CardActions,
  Avatar,
  Chip,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Fab,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
  Person as PersonIcon,
  Upload as UploadIcon,
} from '@mui/icons-material';
import { useQuery } from 'react-query';
import api from '@/services/api';
import { queryKeys } from '@/services/queries';
import CharacterCreationDialog from './CharacterCreationDialog';
import CharacterDetailsDialog from './CharacterDetailsDialog';
import type { Character } from '@/types';
import { useDeleteCharacter } from '@/hooks/useCharacters';

interface CharacterCardProps {
  characterName: string;
  onView: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

const getDisplayName = (characterName: string) =>
  characterName
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');

const buildEditInitialData = (characterDetails?: Character | null) => {
  if (!characterDetails) return undefined;
  return {
    name: characterDetails.name,
    faction: characterDetails.faction,
    role: characterDetails.role,
    description: characterDetails.description,
    stats: characterDetails.stats,
    equipment: characterDetails.equipment.map(({ id: _id, ...rest }) => rest),
    relationships: characterDetails.relationships.map(({ targetCharacterId: _targetCharacterId, ...rest }) => rest),
  };
};

const CharacterStudioHeader: React.FC<{ onCreate: () => void }> = ({ onCreate }) => (
  <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
    <Box>
      <Typography variant="h3" component="h1" sx={{ mb: 1, fontWeight: 700 }}>
        Character Studio
      </Typography>
      <Typography variant="h6" color="text.secondary" sx={{ mb: 2 }}>
        Create and manage your story characters with AI-enhanced profiles
      </Typography>
      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <Button
          variant="contained"
          size="large"
          startIcon={<AddIcon />}
          onClick={onCreate}
          sx={{ fontWeight: 600 }}
        >
          Create Character
        </Button>
        <Button variant="outlined" size="large" startIcon={<UploadIcon />} sx={{ fontWeight: 600 }}>
          Import Character
        </Button>
      </Box>
    </Box>
  </Box>
);

const CharacterLoadingState: React.FC = () => (
  <Box sx={{ textAlign: 'center', py: 8 }}>
    <Typography variant="h6" color="text.secondary">
      Loading characters...
    </Typography>
  </Box>
);

const CharacterErrorState: React.FC<{ errorMessage: string; onRetry: () => void }> = ({
  errorMessage,
  onRetry,
}) => (
  <Card sx={{ p: 4, textAlign: 'center', bgcolor: 'action.hover' }}>
    <Typography variant="h5" sx={{ mb: 1, fontWeight: 600 }}>
      Failed to load characters
    </Typography>
    <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
      {errorMessage || 'Please try again.'}
    </Typography>
    <Button variant="contained" onClick={onRetry} sx={{ fontWeight: 600 }}>
      Retry
    </Button>
  </Card>
);

const CharacterEmptyState: React.FC<{ onCreate: () => void }> = ({ onCreate }) => (
  <Card sx={{ p: 6, textAlign: 'center', bgcolor: 'action.hover' }}>
    <PersonIcon sx={{ fontSize: 72, color: 'text.secondary', mb: 3 }} />
    <Typography variant="h4" color="text.secondary" sx={{ mb: 2, fontWeight: 600 }}>
      No Characters Yet
    </Typography>
    <Typography variant="body1" color="text.secondary" sx={{ mb: 4, maxWidth: 500, mx: 'auto' }}>
      Start building your cast of characters. Each character can have detailed backgrounds,
      relationships, and unique personalities that drive compelling story interactions.
    </Typography>
    <Button
      variant="contained"
      size="large"
      startIcon={<AddIcon />}
      onClick={onCreate}
      sx={{ fontWeight: 600 }}
    >
      Create Your First Character
    </Button>
  </Card>
);

const CharacterGrid: React.FC<{
  characterNames: string[];
  onView: (name: string) => void;
  onEdit: (name: string) => void;
  onDelete: (name: string) => void;
}> = ({ characterNames, onView, onEdit, onDelete }) => (
  <Grid container spacing={3}>
    {characterNames.map((characterName) => (
      <Grid item xs={12} sm={6} md={4} lg={3} key={characterName}>
        <CharacterCard
          characterName={characterName}
          onView={() => onView(characterName)}
          onEdit={() => onEdit(characterName)}
          onDelete={() => onDelete(characterName)}
        />
      </Grid>
    ))}
  </Grid>
);

const CharacterFab: React.FC<{ onCreate: () => void }> = ({ onCreate }) => (
  <Fab
    color="primary"
    aria-label="add character"
    onClick={onCreate}
    sx={{
      position: 'fixed',
      bottom: 24,
      right: 24,
      display: { xs: 'flex', sm: 'none' },
    }}
  >
    <AddIcon />
  </Fab>
);

const DeleteCharacterDialog: React.FC<{
  open: boolean;
  pendingDelete: string | null;
  onClose: () => void;
  onConfirm: () => void;
  isLoading: boolean;
  errorMessage?: string;
}> = ({ open, pendingDelete, onClose, onConfirm, isLoading, errorMessage }) => (
  <Dialog open={open} onClose={onClose} aria-labelledby="confirm-delete-character-title">
    <DialogTitle id="confirm-delete-character-title">Delete character?</DialogTitle>
    <DialogContent>
      <Typography variant="body2" color="text.secondary">
        This will permanently delete <strong>{pendingDelete || 'this character'}</strong> from your
        current workspace.
      </Typography>
      {errorMessage && (
        <Typography variant="body2" color="error" sx={{ mt: 2 }}>
          {errorMessage}
        </Typography>
      )}
    </DialogContent>
    <DialogActions>
      <Button onClick={onClose} disabled={isLoading}>
        Cancel
      </Button>
      <Button onClick={onConfirm} color="error" variant="contained" disabled={isLoading}>
        {isLoading ? 'Deleting…' : 'Delete'}
      </Button>
    </DialogActions>
  </Dialog>
);

const useCharacterCardData = (characterName: string) => {
  const [imageError, setImageError] = useState(false);
  const { data: response, isLoading } = useQuery(
    ['character-card', characterName],
    () => api.getCharacter(characterName),
    {
      staleTime: 5 * 60 * 1000,
      retry: 1,
    }
  );

  const characterData = response?.data;
  const displayData = {
    faction: characterData?.faction || 'Unknown',
    role: characterData?.role || 'Character',
    stats: characterData?.stats || { strength: 0, intelligence: 0, charisma: 0 },
    displayName: characterData?.name || getDisplayName(characterName),
  };

  return {
    imageError,
    setImageError,
    isLoading,
    displayData,
  };
};

const CharacterCardHeader: React.FC<{
  characterName: string;
  displayName: string;
  faction: string;
  isLoading: boolean;
  imageError: boolean;
  onImageError: () => void;
}> = ({ characterName, displayName, faction, isLoading, imageError, onImageError }) => (
  <Box sx={{ textAlign: 'center', mb: 2 }}>
    <Avatar
      sx={{
        width: 80,
        height: 80,
        mx: 'auto',
        mb: 1,
        bgcolor: 'primary.main',
        fontSize: '2rem',
        fontWeight: 700,
      }}
      src={imageError ? undefined : `/characters/${characterName}/avatar.jpg`}
      onError={onImageError}
    >
      {characterName.charAt(0).toUpperCase()}
    </Avatar>
    <Typography variant="h6" component="div" sx={{ fontWeight: 600, mb: 0.5 }}>
      {isLoading ? characterName : displayName}
    </Typography>
    <Chip
      label={isLoading ? 'Loading...' : faction}
      size="small"
      sx={{ bgcolor: 'primary.main', color: 'primary.contrastText', fontWeight: 600 }}
    />
  </Box>
);

const CharacterCardStats: React.FC<{
  role: string;
  stats: { strength: number; intelligence: number; charisma: number };
  isLoading: boolean;
}> = ({ role, stats, isLoading }) => (
  <Box sx={{ mb: 2 }}>
    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
      <strong>Role:</strong> {isLoading ? '...' : role}
    </Typography>
    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
      <Chip label={`STR ${stats.strength}`} size="small" variant="outlined" disabled={isLoading} />
      <Chip label={`INT ${stats.intelligence}`} size="small" variant="outlined" disabled={isLoading} />
      <Chip label={`CHA ${stats.charisma}`} size="small" variant="outlined" disabled={isLoading} />
    </Box>
  </Box>
);

const CharacterCardActions: React.FC<{
  onView: () => void;
  onEdit: () => void;
  onDelete: () => void;
}> = ({ onView, onEdit, onDelete }) => (
  <CardActions sx={{ justifyContent: 'space-between', px: 2, pb: 2 }}>
    <Button size="small" startIcon={<ViewIcon />} onClick={onView} sx={{ fontWeight: 600 }}>
      View
    </Button>
    <Box>
      <Tooltip title="Edit Character">
        <IconButton size="small" onClick={onEdit}>
          <EditIcon />
        </IconButton>
      </Tooltip>
      <Tooltip title="Delete Character">
        <IconButton size="small" onClick={onDelete} color="error">
          <DeleteIcon />
        </IconButton>
      </Tooltip>
    </Box>
  </CardActions>
);

const CharacterCard: React.FC<CharacterCardProps> = ({
  characterName,
  onView,
  onEdit,
  onDelete,
}) => {
  const { imageError, setImageError, isLoading, displayData } = useCharacterCardData(characterName);

  return (
    <Card
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        transition: 'all 0.2s ease-in-out',
        '&:hover': {
          transform: 'translateY(-4px)',
          boxShadow: (theme) => theme.shadows[8],
        },
      }}
    >
      <CardContent sx={{ flexGrow: 1, pb: 1 }}>
        <CharacterCardHeader
          characterName={characterName}
          displayName={displayData.displayName}
          faction={displayData.faction}
          isLoading={isLoading}
          imageError={imageError}
          onImageError={() => setImageError(true)}
        />
        <CharacterCardStats role={displayData.role} stats={displayData.stats} isLoading={isLoading} />
      </CardContent>
      <CharacterCardActions onView={onView} onEdit={onEdit} onDelete={onDelete} />
    </Card>
  );
};

const useCharacterStudioState = () => {
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<string | null>(null);
  const [selectedCharacter, setSelectedCharacter] = useState<string | null>(null);

  const openCreateDialog = () => setCreateDialogOpen(true);
  const closeCreateDialog = () => setCreateDialogOpen(false);
  const openDetailsDialog = () => setDetailsDialogOpen(true);
  const closeDetailsDialog = () => setDetailsDialogOpen(false);
  const openEditDialog = () => setEditDialogOpen(true);
  const closeEditDialog = () => setEditDialogOpen(false);
  const openDeleteDialog = () => setDeleteDialogOpen(true);
  const closeDeleteDialog = () => setDeleteDialogOpen(false);

  return {
    createDialogOpen,
    detailsDialogOpen,
    editDialogOpen,
    deleteDialogOpen,
    pendingDelete,
    selectedCharacter,
    setPendingDelete,
    setSelectedCharacter,
    openCreateDialog,
    closeCreateDialog,
    openDetailsDialog,
    closeDetailsDialog,
    openEditDialog,
    closeEditDialog,
    openDeleteDialog,
    closeDeleteDialog,
  };
};

const useCharacterStudioQueries = (selectedCharacter: string | null) => {
  const charactersQuery = useQuery(queryKeys.characters, () => api.getCharacters());
  const characterDetailsQuery = useQuery(
    queryKeys.characterDetails(selectedCharacter || ''),
    () => (selectedCharacter ? api.getCharacter(selectedCharacter) : null),
    {
      enabled: !!selectedCharacter,
    }
  );

  const characters = charactersQuery.data?.data?.characters ?? [];
  const characterNames = characters.map((summary) => summary.id);
  const characterDetails = characterDetailsQuery.data?.data ?? null;
  const editInitialData = useMemo(
    () => buildEditInitialData(characterDetails),
    [characterDetails]
  );

  return {
    characterNames,
    editInitialData,
    characterSummaries: charactersQuery.data,
    characterDetails,
    isLoading: charactersQuery.isLoading,
    isError: charactersQuery.isError,
    error: charactersQuery.error as Error | undefined,
    refetch: charactersQuery.refetch,
  };
};

const createConfirmDeleteHandler = (params: {
  pendingDelete: string | null;
  deleteCharacter: ReturnType<typeof useDeleteCharacter>;
  selectedCharacter: string | null;
  closeDeleteDialog: () => void;
  clearSelection: () => void;
}) => async () => {
  if (!params.pendingDelete) return;
  try {
    await params.deleteCharacter.mutateAsync(params.pendingDelete);
    params.closeDeleteDialog();
    if (params.selectedCharacter === params.pendingDelete) {
      params.clearSelection();
    }
  } catch {
    // Error handled by mutation state
  }
};

const useCharacterStudioController = () => {
  const deleteCharacter = useDeleteCharacter();
  const dialogState = useCharacterStudioState();
  const queries = useCharacterStudioQueries(dialogState.selectedCharacter);

  const handleCharacterCreated = () => {
    queries.refetch();
    dialogState.closeCreateDialog();
  };

  const handleEditCompleted = () => {
    queries.refetch();
    dialogState.closeEditDialog();
  };

  const handleViewCharacter = (characterName: string) => {
    dialogState.setSelectedCharacter(characterName);
    dialogState.openDetailsDialog();
  };

  const handleEditCharacter = (characterName: string) => {
    dialogState.setSelectedCharacter(characterName);
    dialogState.openEditDialog();
  };

  const handleRequestDeleteCharacter = (characterName: string) => {
    dialogState.setPendingDelete(characterName);
    dialogState.openDeleteDialog();
  };

  const handleDetailsClose = () => {
    dialogState.closeDetailsDialog();
    dialogState.setSelectedCharacter(null);
  };

  const handleEditFromDetails = () => {
    if (!dialogState.selectedCharacter) return;
    dialogState.closeDetailsDialog();
    dialogState.openEditDialog();
  };

  const handleDeleteFromDetails = () => {
    if (!dialogState.selectedCharacter) return;
    dialogState.closeDetailsDialog();
    handleRequestDeleteCharacter(dialogState.selectedCharacter);
  };

  const handleConfirmDelete = createConfirmDeleteHandler({
    pendingDelete: dialogState.pendingDelete,
    deleteCharacter,
    selectedCharacter: dialogState.selectedCharacter,
    closeDeleteDialog: () => {
      dialogState.closeDeleteDialog();
      dialogState.setPendingDelete(null);
    },
    clearSelection: () => {
      dialogState.setSelectedCharacter(null);
      dialogState.closeDetailsDialog();
      dialogState.closeEditDialog();
    },
  });

  return {
    deleteCharacter,
    dialogState,
    queries,
    handleCharacterCreated,
    handleEditCompleted,
    handleViewCharacter,
    handleEditCharacter,
    handleRequestDeleteCharacter,
    handleDetailsClose,
    handleEditFromDetails,
    handleDeleteFromDetails,
    handleConfirmDelete,
  };
};

const CharacterStudioView: React.FC<{
  characterNames: string[];
  isLoading: boolean;
  isError: boolean;
  errorMessage: string;
  onRetry: () => void;
  onCreate: () => void;
  onView: (name: string) => void;
  onEdit: (name: string) => void;
  onDelete: (name: string) => void;
}> = ({
  characterNames,
  isLoading,
  isError,
  errorMessage,
  onRetry,
  onCreate,
  onView,
  onEdit,
  onDelete,
}) => (
  <Box sx={{ maxWidth: 1400, mx: 'auto' }}>
    <CharacterStudioHeader onCreate={onCreate} />
    {isLoading ? (
      <CharacterLoadingState />
    ) : isError ? (
      <CharacterErrorState errorMessage={errorMessage} onRetry={onRetry} />
    ) : characterNames.length > 0 ? (
      <CharacterGrid
        characterNames={characterNames}
        onView={onView}
        onEdit={onEdit}
        onDelete={onDelete}
      />
    ) : (
      <CharacterEmptyState onCreate={onCreate} />
    )}
    <CharacterFab onCreate={onCreate} />
  </Box>
);

const CharacterStudioDialogs: React.FC<{
  createDialogOpen: boolean;
  editDialogOpen: boolean;
  detailsDialogOpen: boolean;
  deleteDialogOpen: boolean;
  pendingDelete: string | null;
  selectedCharacter: string | null;
  editInitialData: ReturnType<typeof buildEditInitialData>;
  characterDetails: Character | null;
  onCreateClose: () => void;
  onEditClose: () => void;
  onDetailsClose: () => void;
  onDeleteClose: () => void;
  onCharacterCreated: () => void;
  onEditCompleted: () => void;
  onEditFromDetails: () => void;
  onDeleteFromDetails: () => void;
  onConfirmDelete: () => void;
  deleteLoading: boolean;
  deleteError?: string;
}> = ({
  createDialogOpen,
  editDialogOpen,
  detailsDialogOpen,
  deleteDialogOpen,
  pendingDelete,
  selectedCharacter,
  editInitialData,
  characterDetails,
  onCreateClose,
  onEditClose,
  onDetailsClose,
  onDeleteClose,
  onCharacterCreated,
  onEditCompleted,
  onEditFromDetails,
  onDeleteFromDetails,
  onConfirmDelete,
  deleteLoading,
  deleteError,
}) => (
  <>
    <CharacterCreationDialog
      open={createDialogOpen}
      onClose={onCreateClose}
      onCharacterCreated={onCharacterCreated}
    />

    <CharacterCreationDialog
      open={editDialogOpen}
      onClose={onEditClose}
      onCharacterCreated={onEditCompleted}
      mode="edit"
      characterId={selectedCharacter ?? undefined}
      initialData={editInitialData}
    />

    <CharacterDetailsDialog
      open={detailsDialogOpen}
      onClose={onDetailsClose}
      character={characterDetails}
      characterName={selectedCharacter}
      onEdit={onEditFromDetails}
      onDelete={onDeleteFromDetails}
    />

    <DeleteCharacterDialog
      open={deleteDialogOpen}
      pendingDelete={pendingDelete}
      onClose={onDeleteClose}
      onConfirm={onConfirmDelete}
      isLoading={deleteLoading}
      errorMessage={deleteError}
    />
  </>
);

const CharacterStudio: React.FC = () => {
  const {
    deleteCharacter,
    dialogState,
    queries,
    handleCharacterCreated,
    handleEditCompleted,
    handleViewCharacter,
    handleEditCharacter,
    handleRequestDeleteCharacter,
    handleDetailsClose,
    handleEditFromDetails,
    handleDeleteFromDetails,
    handleConfirmDelete,
  } = useCharacterStudioController();

  return (
    <>
      <CharacterStudioView
        characterNames={queries.characterNames}
        isLoading={queries.isLoading}
        isError={queries.isError}
        errorMessage={queries.error?.message || 'Please try again.'}
        onRetry={queries.refetch}
        onCreate={dialogState.openCreateDialog}
        onView={handleViewCharacter}
        onEdit={handleEditCharacter}
        onDelete={handleRequestDeleteCharacter}
      />

      <CharacterStudioDialogs
        createDialogOpen={dialogState.createDialogOpen}
        editDialogOpen={dialogState.editDialogOpen}
        detailsDialogOpen={dialogState.detailsDialogOpen}
        deleteDialogOpen={dialogState.deleteDialogOpen}
        pendingDelete={dialogState.pendingDelete}
        selectedCharacter={dialogState.selectedCharacter}
        editInitialData={queries.editInitialData}
        characterDetails={queries.characterDetails}
        onCreateClose={dialogState.closeCreateDialog}
        onEditClose={dialogState.closeEditDialog}
        onDetailsClose={handleDetailsClose}
        onDeleteClose={dialogState.closeDeleteDialog}
        onCharacterCreated={handleCharacterCreated}
        onEditCompleted={handleEditCompleted}
        onEditFromDetails={handleEditFromDetails}
        onDeleteFromDetails={handleDeleteFromDetails}
        onConfirmDelete={handleConfirmDelete}
        deleteLoading={deleteCharacter.isLoading}
        deleteError={(deleteCharacter.error as Error | undefined)?.message}
      />
    </>
  );
};

export default CharacterStudio;
