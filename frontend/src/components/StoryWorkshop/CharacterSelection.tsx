import React, { useState, useMemo } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  CardActionArea,
  Typography,
  Avatar,
  Chip,
  TextField,
  InputAdornment,
  Alert,
  Skeleton,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  FormControlLabel,
} from '@mui/material';
import {
  Search as SearchIcon,
  Person as PersonIcon,
  Check as CheckIcon,
} from '@mui/icons-material';

interface Props {
  characters: string[];
  selectedCharacters: string[];
  onSelectionChange: (characters: string[]) => void;
  isLoading: boolean;
}

interface CharacterCardProps {
  characterName: string;
  isSelected: boolean;
  onClick: () => void;
}

const CharacterCard: React.FC<CharacterCardProps> = ({
  characterName,
  isSelected,
  onClick,
}) => {
  // Mock character data - in a real app, this would come from character details
  const mockData = {
    faction: characterName.includes('bastion_guardian') ? 'Bastion Cohort' : 
             characterName.includes('freewind_raider') ? 'Freewind Collective' : 
             characterName.includes('entropy_adept') ? 'Entropy Cult' : 'Alliance Network',
    role: characterName.includes('bastion_guardian') ? 'Sentinel' : 
          characterName.includes('freewind_raider') ? 'Collective Captain' : 
          characterName.includes('entropy_adept') ? 'Entropy Paladin' : 'Character',
  };

  const getFactionColor = (faction: string) => {
    const colors: Record<string, string> = {
      'Alliance Network': '#4169E1',
      'Entropy Cult': '#DC143C',
      'Freewind Collective': '#228B22',
      'Bastion Cohort': '#8B4513',
      'Other': '#696969',
    };
    return colors[faction] || '#696969';
  };

  const displayName = characterName
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');

  return (
    <Card
      sx={{
        position: 'relative',
        transition: 'all 0.2s ease-in-out',
        border: isSelected ? 2 : 1,
        borderColor: isSelected ? 'primary.main' : 'divider',
        bgcolor: isSelected ? 'action.selected' : 'background.paper',
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: (theme) => theme.shadows[4],
        },
      }}
    >
      <CardActionArea onClick={onClick} sx={{ p: 2 }}>
        <Box sx={{ position: 'relative' }}>
          {/* Selection Indicator */}
          {isSelected && (
            <Box
              sx={{
                position: 'absolute',
                top: -8,
                right: -8,
                zIndex: 1,
                bgcolor: 'primary.main',
                borderRadius: '50%',
                width: 24,
                height: 24,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: 2,
              }}
            >
              <CheckIcon sx={{ fontSize: 16, color: 'white' }} />
            </Box>
          )}

          <CardContent sx={{ textAlign: 'center', p: 0 }}>
            {/* Character Avatar */}
            <Avatar
              sx={{
                width: 64,
                height: 64,
                mx: 'auto',
                mb: 2,
                bgcolor: getFactionColor(mockData.faction),
                fontSize: '1.5rem',
                fontWeight: 700,
                border: isSelected ? 3 : 0,
                borderColor: 'primary.main',
              }}
            >
              {characterName.charAt(0).toUpperCase()}
            </Avatar>

            {/* Character Info */}
            <Typography variant="h6" component="div" sx={{ fontWeight: 600, mb: 1 }}>
              {displayName}
            </Typography>
            
            <Box sx={{ display: 'flex', justifyContent: 'center', gap: 0.5, mb: 1 }}>
              <Chip
                label={mockData.faction}
                size="small"
                sx={{
                  bgcolor: getFactionColor(mockData.faction),
                  color: 'white',
                  fontWeight: 600,
                  fontSize: '0.75rem',
                }}
              />
            </Box>
            
            <Typography variant="body2" color="text.secondary">
              {mockData.role}
            </Typography>
          </CardContent>
        </Box>
      </CardActionArea>
    </Card>
  );
};

const CharacterSelectionSkeleton: React.FC = () => (
  <Grid container spacing={2}>
    {Array.from({ length: 6 }).map((_, index) => (
      <Grid item xs={6} sm={4} md={3} key={index}>
        <Card>
          <CardContent sx={{ textAlign: 'center' }}>
            <Skeleton variant="circular" width={64} height={64} sx={{ mx: 'auto', mb: 2 }} />
            <Skeleton variant="text" width="80%" height={32} sx={{ mx: 'auto', mb: 1 }} />
            <Skeleton variant="rectangular" width={80} height={20} sx={{ mx: 'auto', mb: 1 }} />
            <Skeleton variant="text" width="60%" height={20} sx={{ mx: 'auto' }} />
          </CardContent>
        </Card>
      </Grid>
    ))}
  </Grid>
);

export default function CharacterSelection({
  characters,
  selectedCharacters,
  onSelectionChange,
  isLoading,
}: Props) {
  const [searchTerm, setSearchTerm] = useState('');
  const [factionFilter, setFactionFilter] = useState('');
  const [showOnlySelected, setShowOnlySelected] = useState(false);

  // Filter and search characters
  const filteredCharacters = useMemo(() => {
    let filtered = characters;

    // Apply search filter
    if (searchTerm) {
      filtered = filtered.filter(character =>
        character.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Apply faction filter
    if (factionFilter) {
      filtered = filtered.filter(character => {
        // Mock faction detection - in real app, this would come from character data
        const faction = character.includes('bastion_guardian') ? 'Bastion Cohort' : 
                       character.includes('freewind_raider') ? 'Freewind Collective' : 
                       character.includes('entropy_adept') ? 'Entropy Cult' : 'Alliance Network';
        return faction === factionFilter;
      });
    }

    // Apply selection filter
    if (showOnlySelected) {
      filtered = filtered.filter(character => selectedCharacters.includes(character));
    }

    return filtered;
  }, [characters, searchTerm, factionFilter, showOnlySelected, selectedCharacters]);

  // Available factions for filtering
  const availableFactions = useMemo(() => {
    const factions = new Set<string>();
    characters.forEach(character => {
      const faction = character.includes('bastion_guardian') ? 'Bastion Cohort' : 
                     character.includes('freewind_raider') ? 'Freewind Collective' : 
                     character.includes('entropy_adept') ? 'Entropy Cult' : 'Alliance Network';
      factions.add(faction);
    });
    return Array.from(factions).sort();
  }, [characters]);

  const handleCharacterToggle = (character: string) => {
    if (selectedCharacters.includes(character)) {
      // Remove character
      onSelectionChange(selectedCharacters.filter(c => c !== character));
    } else {
      // Add character (if under limit)
      if (selectedCharacters.length < 6) {
        onSelectionChange([...selectedCharacters, character]);
      }
    }
  };

  const canSelectMore = selectedCharacters.length < 6;
  const needsMoreCharacters = selectedCharacters.length < 2;

  if (isLoading) {
    return <CharacterSelectionSkeleton />;
  }

  return (
    <Box>
      {/* Filters and Search */}
      <Box sx={{ mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={6} md={4}>
            <TextField
              fullWidth
              size="small"
              placeholder="Search characters..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon color="action" />
                  </InputAdornment>
                ),
              }}
            />
          </Grid>
          
          <Grid item xs={12} sm={6} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Faction</InputLabel>
              <Select
                value={factionFilter}
                label="Faction"
                onChange={(e) => setFactionFilter(e.target.value)}
              >
                <MenuItem value="">All Factions</MenuItem>
                {availableFactions.map((faction) => (
                  <MenuItem key={faction} value={faction}>
                    {faction}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={showOnlySelected}
                  onChange={(e) => setShowOnlySelected(e.target.checked)}
                  size="small"
                />
              }
              label="Show only selected"
            />
          </Grid>

          <Grid item xs={12} sm={6} md={2}>
            <Typography variant="body2" color="text.secondary" align="right">
              {selectedCharacters.length}/6 selected
            </Typography>
          </Grid>
        </Grid>
      </Box>

      {/* Selection Feedback */}
      {needsMoreCharacters && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
            Select at least 2 characters
          </Typography>
          <Typography variant="body2">
            Stories need multiple characters to create interesting interactions and dialogue.
          </Typography>
        </Alert>
      )}

      {!canSelectMore && (
        <Alert severity="info" sx={{ mb: 3 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
            Maximum characters selected
          </Typography>
          <Typography variant="body2">
            You've selected the maximum of 6 characters. Deselect a character to choose a different one.
          </Typography>
        </Alert>
      )}

      {/* Character Grid */}
      {filteredCharacters.length > 0 ? (
        <Grid container spacing={2}>
          {filteredCharacters.map((character) => (
            <Grid item xs={6} sm={4} md={3} key={character}>
              <CharacterCard
                characterName={character}
                isSelected={selectedCharacters.includes(character)}
                onClick={() => handleCharacterToggle(character)}
              />
            </Grid>
          ))}
        </Grid>
      ) : (
        <Box sx={{ textAlign: 'center', py: 6 }}>
          <PersonIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
            No characters found
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {searchTerm || factionFilter || showOnlySelected
              ? 'Try adjusting your filters or search terms.'
              : 'Create some characters first to use in your stories.'}
          </Typography>
        </Box>
      )}
    </Box>
  );
}
