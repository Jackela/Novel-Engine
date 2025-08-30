import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Chip, 
  Stack, 
  Typography, 
  Avatar,
  Badge
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  LocationOn as LocationIcon,
  Person as PersonIcon,
  Star as ActivityIcon,
} from '@mui/icons-material';
import GridTile from '../layout/GridTile';

const MapContainer = styled(Box)({
  width: '100%',
  height: '100%',
  position: 'relative',
  borderRadius: '8px',
  overflow: 'hidden',
  background: 'linear-gradient(135deg, #1a1a1d 0%, color-mix(in srgb, #1a1a1d 70%, #6366f1) 100%)',
});

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

const LocationMarker = styled(Box)<{ active?: boolean }>(({ theme, active }) => ({
  position: 'relative',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: active 
    ? 'rgba(255, 255, 255, 0.2)' 
    : 'rgba(255, 255, 255, 0.1)',
  border: active 
    ? `2px solid ${theme.palette.primary.main}` 
    : `1px solid rgba(255, 255, 255, 0.2)`,
  borderRadius: '8px',
  cursor: 'pointer',
  transition: 'all 0.3s ease',
  '&:hover': {
    background: 'rgba(255, 255, 255, 0.3)',
    transform: 'scale(1.05)',
  },
}));

const CharacterAvatar = styled(Avatar)<{ active?: boolean }>(({ theme, active }) => ({
  width: 24,
  height: 24,
  fontSize: '0.7rem',
  border: active ? `2px solid ${theme.palette.success.main}` : 'none',
}));

interface WorldLocation {
  id: string;
  name: string;
  gridPosition: { x: number; y: number };
  characters: string[];
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
      characters: ['Aria Shadowbane'],
      activity: 'high',
      type: 'city'
    },
    {
      id: 'merchant-quarter',
      name: 'Merchant Quarter',
      gridPosition: { x: 3, y: 2 },
      characters: ['Merchant Aldric'],
      activity: 'medium',
      type: 'city'
    },
    {
      id: 'ancient-ruins',
      name: 'Ancient Ruins',
      gridPosition: { x: 5, y: 1 },
      characters: ['Elder Thorne'],
      activity: 'low',
      type: 'landmark'
    },
    {
      id: 'shadow-forest',
      name: 'Shadow Forest',
      gridPosition: { x: 1, y: 3 },
      characters: ['Captain Vex'],
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
    return locations.reduce((total, location) => total + location.characters.length, 0);
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
          {locations.map((location) => (
            <LocationMarker
              key={location.id}
              active={selectedLocation === location.id}
              style={{
                gridColumnStart: location.gridPosition.x,
                gridRowStart: location.gridPosition.y,
              }}
              onClick={() => setSelectedLocation(location.id)}
            >
              <Stack alignItems="center" spacing={0.5}>
                <Badge
                  badgeContent={location.characters.length}
                  color="primary"
                  sx={{ '& .MuiBadge-badge': { fontSize: '0.6rem', minWidth: '16px', height: '16px' } }}
                >
                  <LocationIcon
                    sx={{ 
                      color: getActivityColor(location.activity),
                      fontSize: '20px'
                    }}
                  />
                </Badge>
                <Typography 
                  variant="caption" 
                  sx={{ 
                    color: 'white', 
                    fontSize: '0.65rem',
                    textAlign: 'center',
                    lineHeight: 1,
                    opacity: selectedLocation === location.id ? 1 : 0.8
                  }}
                >
                  {location.name}
                </Typography>
                <Stack direction="row" spacing={0.25}>
                  {location.characters.slice(0, 2).map((character, index) => (
                    <CharacterAvatar
                      key={index}
                      active={selectedLocation === location.id}
                      sx={{ backgroundColor: getActivityColor(location.activity) }}
                    >
                      {character.charAt(0)}
                    </CharacterAvatar>
                  ))}
                </Stack>
              </Stack>
            </LocationMarker>
          ))}
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