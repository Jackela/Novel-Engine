import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import {
  Box,
  Chip,
  Stack,
  Typography,
  Avatar,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  useTheme,
} from '@mui/material';
import { styled, alpha } from '@mui/material/styles';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LocationOn as LocationIcon,
  Person as PersonIcon,
  Timeline as ActivityIcon,
} from '@mui/icons-material';
import GridTile from '../layout/GridTile';
import { useDashboardCharactersDataset, type DashboardCharacter } from '../../hooks/useDashboardCharactersDataset';

const MapContainer = styled(Box)(({ theme }) => ({
  width: '100%',
  height: '100%',
  position: 'relative',
  borderRadius: theme.shape.borderRadius,
  overflow: 'hidden',
  background: 'linear-gradient(135deg, var(--color-bg-primary) 0%, var(--color-bg-tertiary) 100%)',
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

const LocationMarker = styled(motion.button, {
  shouldForwardProp: (prop: PropertyKey) => !['active', 'activitylevel'].includes(String(prop)),
})<{ active?: boolean; activitylevel?: string }>(({ theme, active, activitylevel }) => ({
  position: 'relative',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  gap: theme.spacing(1),
  borderRadius: theme.shape.borderRadius,
  padding: theme.spacing(2),
  cursor: 'pointer',
  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
  border: active ? `2px solid ${theme.palette.primary.main}` : `1px solid ${theme.palette.divider}`,
  backgroundColor: active ? alpha(theme.palette.primary.main, 0.15) : theme.palette.background.paper,
  textAlign: 'left',
  '&:hover': {
    background: active ? alpha(theme.palette.primary.main, 0.3) : 'var(--color-bg-tertiary)',
    borderColor: theme.palette.primary.main,
    transform: 'scale(1.05)',
    boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)',
  },
  '&:focus-visible': {
    outline: `2px solid ${theme.palette.info.main}`,
    outlineOffset: 2,
  },
  '&:focus:not(:focus-visible)': {
    outline: 'none',
  },
  '&::before': {
    content: '""',
    position: 'absolute',
    top: 8,
    right: 8,
    width: 8,
    height: 8,
    borderRadius: '50%',
    backgroundColor:
      activitylevel === 'high'
        ? theme.palette.success.main
        : activitylevel === 'medium'
          ? theme.palette.warning.main
          : theme.palette.text.secondary,
    animation: activitylevel === 'high' ? 'pulse 2s infinite' : 'none',
  },
  '@keyframes pulse': {
    '0%, 100%': { opacity: 1 },
    '50%': { opacity: 0.5 },
  },
}));

const CharacterAvatar = styled(Avatar, {
  shouldForwardProp: (prop: PropertyKey) => prop !== 'active',
})<{ active?: boolean }>(({ theme, active }) => ({
  width: 24,
  height: 24,
  fontSize: '0.7rem',
  border: active ? `2px solid ${theme.palette.success.main}` : 'none',
}));

interface Character extends DashboardCharacter {
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

const LOCATION_TEMPLATES: Omit<WorldLocation, 'characters'>[] = [
  {
    id: 'crystal-city',
    name: 'Crystal City',
    gridPosition: { x: 2, y: 1 },
    activity: 'high',
    type: 'city',
  },
  {
    id: 'merchant-quarter',
    name: 'Merchant Quarter',
    gridPosition: { x: 3, y: 2 },
    activity: 'medium',
    type: 'city',
  },
  {
    id: 'ancient-ruins',
    name: 'Ancient Ruins',
    gridPosition: { x: 5, y: 1 },
    activity: 'low',
    type: 'landmark',
  },
  {
    id: 'shadow-forest',
    name: 'Shadow Forest',
    gridPosition: { x: 1, y: 3 },
    activity: 'medium',
    type: 'wilderness',
  },
];

interface WorldStateMapProps {
  loading?: boolean;
  error?: boolean;
}

const WorldStateMap: React.FC<WorldStateMapProps> = ({ loading, error }) => {
  const theme = useTheme();
  const { characters, loading: charactersLoading, error: charactersError, source } = useDashboardCharactersDataset();
  const [selectedLocation, setSelectedLocation] = useState<string | null>(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const markerRefs = useRef<Array<HTMLButtonElement | null>>([]);

  useEffect(() => {
    const interval = setInterval(() => {
      setLastUpdate(new Date());
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const locations: WorldLocation[] = useMemo(() => {
    const templateCount = LOCATION_TEMPLATES.length;
    return LOCATION_TEMPLATES.map((location, locationIndex) => {
      const assigned = characters
        .filter((_, idx) => idx % templateCount === locationIndex)
        .map((character) => ({
          ...character,
          initials: getInitials(character.name),
        }));
      const activity = assigned.some((char) => char.status === 'active')
        ? 'high'
        : assigned.some((char) => char.status === 'inactive')
          ? 'medium'
          : location.activity;
      return {
        ...location,
        activity,
        characters: assigned,
      };
    });
  }, [characters]);

  useEffect(() => {
    if (!locations.length) {
      return;
    }
    if (!selectedLocation || !locations.some((loc) => loc.id === selectedLocation)) {
      setSelectedLocation(locations[0].id);
      setActiveIndex(0);
    }
  }, [locations, selectedLocation]);

  useEffect(() => {
    const node = markerRefs.current[activeIndex];
    if (node && document.activeElement !== node) {
      node.focus();
    }
  }, [activeIndex]);

  const getActivityColor = (activity: string) => {
    switch (activity) {
      case 'high':
        return theme.palette.success.main;
      case 'medium':
        return theme.palette.warning.main;
      case 'low':
      default:
        return theme.palette.text.secondary;
    }
  };

  const totalCharacters = characters.length;
  const activeCharacters = useMemo(
    () => characters.filter((character) => character.status === 'active').length,
    [characters]
  );

  const handleMoveFocus = useCallback(
    (direction: 1 | -1) => {
      setActiveIndex((prev) => {
        const next = (prev + direction + locations.length) % locations.length;
        return next;
      });
    },
    [locations.length]
  );

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent, index: number, locationId: string) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        setSelectedLocation(locationId);
      }

      if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
        event.preventDefault();
        handleMoveFocus(1);
      }

      if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
        event.preventDefault();
        handleMoveFocus(-1);
      }
    },
    [handleMoveFocus]
  );

  const combinedLoading = loading || charactersLoading;
  const combinedError = error || charactersError;
  const hasAssignedCharacters = locations.some((location) => location.characters.length > 0);
  const shouldShowError = Boolean(combinedError) && !hasAssignedCharacters;

  return (
    <GridTile
      title="World State Map"
      data-testid="world-state-map"
      position={{
        desktop: { column: 'span 2', height: 'clamp(320px, 45vh, 420px)' },
        tablet: { column: 'span 2', height: '360px' },
        mobile: { column: 'span 1', height: '240px' },
      }}
      loading={combinedLoading}
      error={shouldShowError}
    >
      <MapContainer>
        <StatsOverlay>
          <Chip
            icon={<PersonIcon />}
            label={`${totalCharacters} Characters`}
            size="small"
            sx={{
              backgroundColor: (theme) => theme.palette.background.paper,
              color: (theme) => theme.palette.text.primary,
              border: (theme) => `1px solid ${theme.palette.divider}`,
              '& .MuiChip-icon': { color: (theme) => theme.palette.primary.main },
            }}
          />
          <Chip
            icon={<ActivityIcon />}
            label={`${activeCharacters} Active`}
            size="small"
            sx={{
              backgroundColor: (theme) => alpha(theme.palette.success.main, 0.15),
              color: (theme) => alpha(theme.palette.success.main, 0.85),
              border: (theme) => `1px solid ${theme.palette.success.main}`,
              '& .MuiChip-icon': { color: (theme) => theme.palette.success.main },
            }}
          />
          <Chip
            label={source === 'api' ? 'API feed' : 'Demo data'}
            size="small"
            color={source === 'api' ? 'success' : 'default'}
            sx={{
              fontWeight: 600,
              height: 20,
            }}
          />
        </StatsOverlay>

        <MapGrid>
          {locations.map((location, index) => {
            const isSelected = selectedLocation === location.id;
            const characterNames = location.characters.map((character) => character.name).join(', ');
            const accessibleLabel = characterNames
              ? `${location.name} – ${characterNames}`
              : `${location.name} – No assigned characters yet`;

            return (
              <LocationMarker
                key={location.id}
                active={isSelected}
                activitylevel={location.activity}
                data-activity={location.activity}
                data-location={location.id}
                role="button"
                type="button"
                aria-pressed={isSelected}
                aria-expanded={isSelected}
                aria-controls={`location-details-${location.id}`}
                aria-label={accessibleLabel}
                tabIndex={activeIndex === index ? 0 : -1}
                ref={(node: HTMLButtonElement | null) => {
                  markerRefs.current[index] = node;
                }}
                style={{
                  gridColumnStart: location.gridPosition.x,
                  gridRowStart: location.gridPosition.y,
                }}
                onClick={() => setSelectedLocation(location.id)}
                onFocus={() => setActiveIndex(index)}
                onKeyDown={(event) => handleKeyDown(event, index, location.id)}
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
                      color: (theme) => theme.palette.text.primary,
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
                        border: (theme) => `2px solid ${theme.palette.background.default}`,
                      }}
                    >
                      {character.initials}
                    </CharacterAvatar>
                  ))}
                  {location.characters.length > 3 && (
                    <CharacterAvatar
                      sx={{
                        backgroundColor: (theme) => theme.palette.background.paper,
                        border: (theme) => `2px solid ${theme.palette.background.default}`,
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
                          borderTop: (theme) => `1px solid ${theme.palette.divider}`,
                          width: '100%',
                        }}
                        id={`location-details-${location.id}`}
                      >
                        <List dense disablePadding>
                          {location.characters.map((character) => (
                            <ListItem key={character.id} disablePadding sx={{ mb: 0.5 }}>
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
                                secondary={`${character.role} • ${character.trust}% trust`}
                                primaryTypographyProps={{
                                  variant: 'caption',
                                  sx: { color: (theme) => theme.palette.text.secondary, fontSize: '0.7rem' },
                                }}
                                secondaryTypographyProps={{
                                  variant: 'caption',
                                  sx: { color: 'text.disabled', fontSize: '0.65rem' },
                                }}
                              />
                            </ListItem>
                          ))}
                          {location.characters.length === 0 && (
                            <ListItem disablePadding>
                              <ListItemText
                                primary="No characters assigned"
                                primaryTypographyProps={{
                                  variant: 'caption',
                                  sx: { color: 'text.disabled', fontSize: '0.7rem' },
                                }}
                              />
                            </ListItem>
                          )}
                        </List>
                      </Box>
                    </motion.div>
                  )}
                </AnimatePresence>
              </LocationMarker>
            );
          })}
        </MapGrid>

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

function getInitials(name: string) {
  const segments = name.split(' ').filter(Boolean);
  if (!segments.length) {
    return 'NA';
  }
  if (segments.length === 1) {
    return segments[0].slice(0, 2).toUpperCase();
  }
  return `${segments[0][0]}${segments[segments.length - 1][0]}`.toUpperCase();
}
