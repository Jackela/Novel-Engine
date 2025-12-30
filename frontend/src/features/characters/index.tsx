import React, { useState } from 'react';
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

const CharacterStudio: React.FC = () => {
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<string | null>(null);
  const [selectedCharacter, setSelectedCharacter] = useState<string | null>(null);

  const deleteCharacter = useDeleteCharacter();

  // Fetch characters list
  const { data: characterSummaries, isLoading, isError: isCharactersError, error: charactersError, refetch } = useQuery(
    queryKeys.characters,
    api.getCharacters
  );

  const characterNames = (characterSummaries ?? []).map((summary) => summary.id);

  // Fetch detailed character data when needed
  const { data: characterDetails } = useQuery(
    queryKeys.characterDetails(selectedCharacter || ''),
    () => selectedCharacter ? api.getCharacter(selectedCharacter) : null,
    {
      enabled: !!selectedCharacter,
    }
  );

  const editInitialData = React.useMemo(() => {
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
  }, [characterDetails]);

  const handleViewCharacter = (characterName: string) => {
    setSelectedCharacter(characterName);
    setDetailsDialogOpen(true);
  };

  const handleEditCharacter = (characterName: string) => {
    setSelectedCharacter(characterName);
    setEditDialogOpen(true);
  };

  const handleRequestDeleteCharacter = (characterName: string) => {
    setPendingDelete(characterName);
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!pendingDelete) return;
    try {
      await deleteCharacter.mutateAsync(pendingDelete);
      setDeleteDialogOpen(false);
      setPendingDelete(null);
      if (selectedCharacter === pendingDelete) {
        setSelectedCharacter(null);
        setDetailsDialogOpen(false);
        setEditDialogOpen(false);
      }
    } catch {
      // Error handled by mutation state
    }
  };

  const handleCharacterCreated = () => {
    refetch(); // Refresh the characters list
    setCreateDialogOpen(false);
  };

  // Removed unused getFactionColor; colors sourced from tokens/theme directly in components

  return (
    <Box sx={{ maxWidth: 1400, mx: 'auto' }}>
      {/* Header */}
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
              onClick={() => setCreateDialogOpen(true)}
              sx={{ fontWeight: 600 }}
            >
              Create Character
            </Button>
            <Button
              variant="outlined"
              size="large"
              startIcon={<UploadIcon />}
              sx={{ fontWeight: 600 }}
            >
              Import Character
            </Button>
          </Box>
        </Box>
      </Box>

      {/* Character Grid */}
      {isLoading ? (
        <Box sx={{ textAlign: 'center', py: 8 }}>
          <Typography variant="h6" color="text.secondary">
            Loading characters...
          </Typography>
        </Box>
      ) : isCharactersError ? (
        <Card sx={{ p: 4, textAlign: 'center', bgcolor: 'action.hover' }}>
          <Typography variant="h5" sx={{ mb: 1, fontWeight: 600 }}>
            Failed to load characters
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            {(charactersError as Error | undefined)?.message || 'Please try again.'}
          </Typography>
          <Button variant="contained" onClick={() => refetch()} sx={{ fontWeight: 600 }}>
            Retry
          </Button>
        </Card>
      ) : characterNames.length > 0 ? (
        <Grid container spacing={3}>
          {characterNames.map((characterName) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={characterName}>
              <CharacterCard
                characterName={characterName}
                onView={() => handleViewCharacter(characterName)}
                onEdit={() => handleEditCharacter(characterName)}
                onDelete={() => handleRequestDeleteCharacter(characterName)}
              />
            </Grid>
          ))}
        </Grid>
      ) : (
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
            onClick={() => setCreateDialogOpen(true)}
            sx={{ fontWeight: 600 }}
          >
            Create Your First Character
          </Button>
        </Card>
      )}

      {/* Floating Action Button for mobile */}
      <Fab
        color="primary"
        aria-label="add character"
        onClick={() => setCreateDialogOpen(true)}
        sx={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          display: { xs: 'flex', sm: 'none' },
        }}
      >
        <AddIcon />
      </Fab>

      {/* Character Creation Dialog */}
      <CharacterCreationDialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        onCharacterCreated={handleCharacterCreated}
      />

      {/* Character Edit Dialog */}
      <CharacterCreationDialog
        open={editDialogOpen}
        onClose={() => setEditDialogOpen(false)}
        onCharacterCreated={() => {
          refetch();
          setEditDialogOpen(false);
        }}
        mode="edit"
        characterId={selectedCharacter ?? undefined}
        initialData={editInitialData}
      />

      {/* Character Details Dialog */}
      <CharacterDetailsDialog
        open={detailsDialogOpen}
        onClose={() => {
          setDetailsDialogOpen(false);
          setSelectedCharacter(null);
        }}
        character={characterDetails}
        characterName={selectedCharacter}
        onEdit={() => {
          if (!selectedCharacter) return;
          setDetailsDialogOpen(false);
          setEditDialogOpen(true);
        }}
        onDelete={() => {
          if (!selectedCharacter) return;
          setDetailsDialogOpen(false);
          handleRequestDeleteCharacter(selectedCharacter);
        }}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        aria-labelledby="confirm-delete-character-title"
      >
        <DialogTitle id="confirm-delete-character-title">Delete character?</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            This will permanently delete <strong>{pendingDelete || 'this character'}</strong> from your current workspace.
          </Typography>
          {deleteCharacter.isError && (
            <Typography variant="body2" color="error" sx={{ mt: 2 }}>
              {(deleteCharacter.error as Error | undefined)?.message || 'Failed to delete character'}
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)} disabled={deleteCharacter.isLoading}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirmDelete}
            color="error"
            variant="contained"
            disabled={deleteCharacter.isLoading}
          >
            {deleteCharacter.isLoading ? 'Deleting…' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

// Character Card Component
interface CharacterCardProps {
  characterName: string;
  onView: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

const CharacterCard: React.FC<CharacterCardProps> = ({
  characterName,
  onView,
  onEdit,
  onDelete,
}) => {
  const [imageError, setImageError] = useState(false);

  // Fetch real character data from API
  const { data: response, isLoading: isLoadingDetails } = useQuery(
    ['character-card', characterName],
    () => api.getCharacter(characterName),
    {
      staleTime: 5 * 60 * 1000, // Cache for 5 minutes
      retry: 1,
    }
  );

  const characterData = response?.data;

  // Use real data from API, with sensible defaults
  const displayData = {
    faction: characterData?.faction || 'Unknown',
    role: characterData?.role || 'Character',
    stats: characterData?.stats || { strength: 0, intelligence: 0, charisma: 0 },
    displayName: characterData?.name || characterName.split('_').map(word =>
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' '),
  };

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
        {/* Character Avatar */}
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
            onError={() => setImageError(true)}
          >
            {characterName.charAt(0).toUpperCase()}
          </Avatar>
          <Typography variant="h6" component="div" sx={{ fontWeight: 600, mb: 0.5 }}>
            {isLoadingDetails ? characterName : displayData.displayName}
          </Typography>
          <Chip
            label={isLoadingDetails ? 'Loading...' : displayData.faction}
            size="small"
            sx={{
              bgcolor: 'primary.main',
              color: 'primary.contrastText',
              fontWeight: 600,
            }}
          />
        </Box>

        {/* Character Info */}
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            <strong>Role:</strong> {isLoadingDetails ? '...' : displayData.role}
          </Typography>

          {/* Quick Stats */}
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Chip
              label={`STR ${displayData.stats.strength}`}
              size="small"
              variant="outlined"
              disabled={isLoadingDetails}
            />
            <Chip
              label={`INT ${displayData.stats.intelligence}`}
              size="small"
              variant="outlined"
              disabled={isLoadingDetails}
            />
            <Chip
              label={`CHA ${displayData.stats.charisma}`}
              size="small"
              variant="outlined"
              disabled={isLoadingDetails}
            />
          </Box>
        </Box>
      </CardContent>

      <CardActions sx={{ justifyContent: 'space-between', px: 2, pb: 2 }}>
        <Button
          size="small"
          startIcon={<ViewIcon />}
          onClick={onView}
          sx={{ fontWeight: 600 }}
        >
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
    </Card>
  );
};

export default CharacterStudio;
