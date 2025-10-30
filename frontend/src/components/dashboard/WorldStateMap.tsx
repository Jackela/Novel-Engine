import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Chip, 
  Stack, 
  Typography, 
  Avatar,
  Badge,
  Collapse,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LocationOn as LocationIcon,
  Person as PersonIcon,
  Activity as ActivityIcon,
  Circle as PulseIcon,
} from '@mui/icons-material';
import GridTile from '../layout/GridTile';

const MapContainer = styled(Box)(({ theme }) => ({
  width: '100%',
  height: '100%',
  position: 'relative',
  borderRadius: theme.shape.borderRadius,
  overflow: 'hidden',
  background: 'linear-gradient(135deg, #0a0a0b 0%, #1a1a1d 100%)',
  padding: theme.spacing(2),
}));

const StatsOverlay = styled(Box)(({ theme }) => ({
  position: 'absolute',
  top: theme.spacing(1),
  left: theme.spacing(1),
  zIndex: 10,
  display: 'flex',
  gap: theme.spacing(1),
  flexWrap: 'wrap',
}));

const MapGrid = styled(Box)({
  position: 'relative',
  width: '100%',
  height: '100%',
  display: 'grid',
  gridTemplateColumns: 'repeat(6, 1fr)',
  gridTemplateRows: 'repeat(4, 1fr)',
  padding: '16px',
  gap: '8px',
});

const LocationMarker = styled(motion.div)<{ active?: boolean; activitylevel?: string }>(({ theme, active, activitylevel }) => ({
  position: 'relative',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  gap: theme.spacing(1),
  background: active 
    ? 'rgba(99, 102, 241, 0.2)' 
    : '#111113',
  border: active 
    ? `2px solid ${theme.palette.primary.main}` 
    : `1px solid #2a2a30`,
  borderRadius: theme.shape.borderRadius,
  padding: theme.spacing(2),
  cursor: 'pointer',
  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
  '&:hover': {
    background: active ? 'rgba(99, 102, 241, 0.3)' : '#1a1a1d',
    borderColor: '#6366f1',
    transform: 'scale(1.05)',
    boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)',
  },
  '&::before': {
    content: '""',
    position: 'absolute',
    top: 8,
    right: 8,
    width: 8,
    height: 8,
    borderRadius: '50%',
    backgroundColor: activitylevel === 'high' ? '#10b981' : activitylevel === 'medium' ? '#f59e0b' : '#808088',
    animation: activitylevel === 'high' ? 'pulse 2s infinite' : 'none',
  },
  '@keyframes pulse': {
    '0%, 100%': { opacity: 1 },
    '50%': { opacity: 0.5 },
  },
}));

const CharacterAvatar = styled(Avatar)<{ active?: boolean }>(({ theme, active }) => ({
  width: 24,
  height: 24,
  fontSize: '0.7rem',
  border: active ? `2px solid ${theme.palette.success.main}` : 'none',
}));

interface Character {
  id: string;
  name: string;
  initials: string;
}

interface WorldLocation {
  id: string;
  name: string;
  gridPosition: { x: number; y: number };
  characters: Character[];
  activity: 'high' | 'medium' | 'low';
  type: 'city' | 'dungeon' | 'wilderness' | 'landmark';
}

interface WorldStateMapProps {
  loading?: boolean;
  error?: boolean;
}

const WorldStateMap: React.FC<WorldStateMapProps> = ({ loading, error }) => {
  const [locations] = useState<WorldLocation[]>([
    {
      id: 'crystal-city',
      name: 'Crystal City',
      gridPosition: { x: 2, y: 1 },
      characters: [
        { id: 'c1', name: 'Aria Shadowbane', initials: 'AS' },
        { id: 'c2', name: 'Zara Moonwhisper', initials: 'ZM' },
      ],
      activity: 'high',
      type: 'city'
    },
    {
      id: 'merchant-quarter',
      name: 'Merchant Quarter',
      gridPosition: { x: 3, y: 2 },
      characters: [
        { id: 'c3', name: 'Merchant Aldric', initials: 'MA' },
      ],
      activity: 'medium',
      type: 'city'
    },
    {
      id: 'ancient-ruins',
      name: 'Ancient Ruins',
      gridPosition: { x: 5, y: 1 },
      characters: [
        { id: 'c4', name: 'Elder Thorne', initials: 'ET' },
      ],
      activity: 'low',
      type: 'landmark'
    },
    {
      id: 'shadow-forest',
      name: 'Shadow Forest',
      gridPosition: { x: 1, y: 3 },
      characters: [
        { id: 'c5', name: 'Captain Vex', initials: 'CV' },
        { id: 'c6', name: 'Kael Stormrider', initials: 'KS' },
        { id: 'c7', name: 'Luna Nightshade', initials: 'LN' },
      ],
      activity: 'medium',
      type: 'wilderness'
    },
  ]);

  const [selectedLocation, setSelectedLocation] = useState<string | null>('crystal-city');
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Simulate periodic updates
  useEffect(() => {
    const interval = setInterval(() => {
      setLastUpdate(new Date());
    }, 10000); // Update every 10 seconds

    return () => clearInterval(interval);
  }, []);

  const getActivityColor = (activity: string) => {
    switch (activity) {
      case 'high':
        return '#10b981'; // Professional success green
      case 'medium':
        return '#f59e0b'; // Sophisticated amber
      case 'low':
        return '#808088'; // Tertiary text color
      default:
        return '#808088';
    }
  };

  const getTotalCharacters = () => {
    const uniqueCharacters = new Set(
      locations.flatMap(loc => loc.characters.map(c => c.id))
    );
    return uniqueCharacters.size;
  };

  const getActiveLocations = () => {
    return locations.filter(loc => loc.activity === 'high').length;
  };

  return (
    <GridTile
      title="World State Map"
      data-testid="world-state-map"
      position={{
        desktop: { column: '1 / 7', height: '320px' },
        tablet: { column: '1 / 6', height: '300px' },
        mobile: { height: '140px' },
      }}
      loading={loading}
      error={error}
    >
      <MapContainer>
        <StatsOverlay>
          <Chip
            icon={<PersonIcon />}
            label={`${getTotalCharacters()} Characters`}
            size="small"
            sx={{ 
              backgroundColor: '#2a2a30', 
              color: '#f0f0f2',
              border: '1px solid #3a3a42',
              '& .MuiChip-icon': { color: '#6366f1' }
            }}
          />
          <Chip
            icon={<ActivityIcon />}
            label={`${getActiveLocations()} Active`}
            size="small"
            sx={{ 
              backgroundColor: '#064e3b', 
              color: '#6ee7b7',
              border: '1px solid #065f46',
              '& .MuiChip-icon': { color: '#10b981' }
            }}
          />
        </StatsOverlay>

        <MapGrid>
          {locations.map((location) => {
            const isSelected = selectedLocation === location.id;
            
            return (
              <LocationMarker
                key={location.id}
                active={isSelected}
                activitylevel={location.activity}
                style={{
                  gridColumnStart: location.gridPosition.x,
                  gridRowStart: location.gridPosition.y,
                }}
                onClick={() => setSelectedLocation(isSelected ? null : location.id)}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.98 }}
                transition={{ duration: 0.3 }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                  <LocationIcon
                    sx={{ 
                      color: getActivityColor(location.activity),
                      fontSize: '20px',
                      flexShrink: 0,
                    }}
                  />
                  <Typography 
                    variant="caption" 
                    sx={{ 
                      color: '#f0f0f2', 
                      fontSize: '0.75rem',
                      fontWeight: isSelected ? 600 : 500,
                      flex: 1,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {location.name}
                  </Typography>
                </Box>

                <Stack direction="row" spacing={-0.5} sx={{ alignSelf: 'flex-start' }}>
                  {location.characters.slice(0, 3).map((character) => (
                    <CharacterAvatar
                      key={character.id}
                      active={isSelected}
                      sx={{ 
                        backgroundColor: getActivityColor(location.activity),
                        border: '2px solid #111113',
                      }}
                    >
                      {character.initials}
                    </CharacterAvatar>
                  ))}
                  {location.characters.length > 3 && (
                    <CharacterAvatar
                      sx={{ 
                        backgroundColor: '#2a2a30',
                        border: '2px solid #111113',
                      }}
                    >
                      <Typography variant="caption" sx={{ fontSize: '0.6rem' }}>
                        +{location.characters.length - 3}
                      </Typography>
                    </CharacterAvatar>
                  )}
                </Stack>

                <AnimatePresence>
                  {isSelected && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.2 }}
                      style={{ width: '100%', overflow: 'hidden' }}
                    >
                      <Box 
                        sx={{ 
                          mt: 1, 
                          pt: 1, 
                          borderTop: '1px solid #2a2a30',
                          width: '100%',
                        }}
                      >
                        <List dense disablePadding>
                          {location.characters.map((character) => (
                            <ListItem 
                              key={character.id} 
                              disablePadding
                              sx={{ mb: 0.5 }}
                            >
                              <ListItemAvatar sx={{ minWidth: 32 }}>
                                <Avatar 
                                  sx={{ 
                                    width: 24, 
                                    height: 24, 
                                    fontSize: '0.65rem',
                                    backgroundColor: getActivityColor(location.activity),
                                  }}
                                >
                                  {character.initials}
                                </Avatar>
                              </ListItemAvatar>
                              <ListItemText 
                                primary={character.name}
                                primaryTypographyProps={{
                                  variant: 'caption',
                                  sx: { color: '#b0b0b8', fontSize: '0.7rem' },
                                }}
                              />
                            </ListItem>
                          ))}
                        </List>
                      </Box>
                    </motion.div>
                  )}
                </AnimatePresence>
              </LocationMarker>
            );
          })}
        </MapGrid>

        {/* Status Information */}
        <Box
          sx={{
            position: 'absolute',
            bottom: 8,
            right: 8,
            color: 'rgba(255, 255, 255, 0.7)',
            fontSize: '0.65rem',
          }}
        >
          Last updated: {lastUpdate.toLocaleTimeString()}
        </Box>
      </MapContainer>
    </GridTile>
  );
};

export default WorldStateMap;