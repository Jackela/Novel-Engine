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
import api from '../../services/api';
import CharacterCreationDialog from './CharacterCreationDialog';
import CharacterDetailsDialog from './CharacterDetailsDialog';
import { Character } from '../../types';

const CharacterStudio: React.FC = () => {
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [selectedCharacter, setSelectedCharacter] = useState<string | null>(null);

  // Fetch characters list
  const { data: characterNames, isLoading, refetch } = useQuery(
    'characters',
    api.getCharacters
  );

  // Fetch detailed character data when needed
  const { data: characterDetails } = useQuery(
    ['character-details', selectedCharacter],
    () => selectedCharacter ? api.getCharacterDetails(selectedCharacter) : null,
    {
      enabled: !!selectedCharacter,
    }
  );

  const handleViewCharacter = (characterName: string) => {
    setSelectedCharacter(characterName);
    setDetailsDialogOpen(true);
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
      ) : characterNames && characterNames.length > 0 ? (
        <Grid container spacing={3}>
          {characterNames.map((characterName) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={characterName}>
              <CharacterCard
                characterName={characterName}
                onView={() => handleViewCharacter(characterName)}
                onEdit={() => {
                  setSelectedCharacter(characterName);
                  // Future: Open edit dialog
                }}
                onDelete={() => {
                  // Future: Implement delete functionality
                }}
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

      {/* Character Details Dialog */}
      <CharacterDetailsDialog
        open={detailsDialogOpen}
        onClose={() => {
          setDetailsDialogOpen(false);
          setSelectedCharacter(null);
        }}
        character={characterDetails}
        characterName={selectedCharacter}
      />
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

  // Mock data - in real app, this would come from character details
  const mockData = {
    faction: characterName.includes('bastion_guardian') ? 'Bastion Cohort' : 
             characterName.includes('freewind_raider') ? 'Freewind Collective' : 'Alliance Network',
    role: characterName.includes('bastion_guardian') ? 'Sentinel' : 
          characterName.includes('freewind_raider') ? 'Collective Captain' : 'Character',
    stats: { strength: 7, intelligence: 6, charisma: 5 },
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
            {characterName.split('_').map(word => 
              word.charAt(0).toUpperCase() + word.slice(1)
            ).join(' ')}
          </Typography>
          <Chip
            label={mockData.faction}
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
            <strong>Role:</strong> {mockData.role}
          </Typography>
          
          {/* Quick Stats */}
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Chip label={`STR ${mockData.stats.strength}`} size="small" variant="outlined" />
            <Chip label={`INT ${mockData.stats.intelligence}`} size="small" variant="outlined" />
            <Chip label={`CHA ${mockData.stats.charisma}`} size="small" variant="outlined" />
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
