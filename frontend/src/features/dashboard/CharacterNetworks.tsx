import React, { useMemo, useRef, useState, useEffect, useCallback } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import List from '@mui/material/List';
import Avatar from '@mui/material/Avatar';
import LinearProgress from '@mui/material/LinearProgress';
import Fade from '@mui/material/Fade';
import useMediaQuery from '@mui/material/useMediaQuery';
import { styled, useTheme } from '@mui/material/styles';
import { motion } from 'framer-motion';
import PersonIcon from '@mui/icons-material/Person';
import GroupIcon from '@mui/icons-material/Groups';
import LinkIcon from '@mui/icons-material/Link';
import NetworkIcon from '@mui/icons-material/Diversity3';
import GridTile from '@/components/layout/GridTile';
import { useDashboardCharactersDataset } from '@/hooks/useDashboardCharactersDataset';

const NetworkContainer = styled(Box)(({ theme }) => ({
  width: '100%',
  height: '100%',
  position: 'relative',
  display: 'flex',
  flexDirection: 'column',
  [theme.breakpoints.down('md')]: {
    padding: theme.spacing(0.5),
  },
}));

const CharacterCard = styled(motion.button, {
  shouldForwardProp: (prop: PropertyKey) => prop !== 'status',
})<{ status: string }>(({ theme, status }) => ({
  display: 'flex',
  alignItems: 'center',
  width: '100%',
  padding: theme.spacing(1),
  borderRadius: theme.shape.borderRadius,
  backgroundColor: theme.palette.background.paper,
  border: `1px solid ${theme.palette.divider}`,
  marginBottom: theme.spacing(1),
  transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
  cursor: 'pointer',
  textAlign: 'left',
  '&:hover': {
    backgroundColor: 'var(--color-bg-tertiary)',
    borderColor:
      status === 'active'
        ? theme.palette.success.main
        : status === 'hostile'
          ? theme.palette.error.main
          : theme.palette.warning.main,
    transform: 'translateY(-2px)',
    boxShadow: `0 4px 8px ${status === 'active'
      ? 'rgba(16, 185, 129, 0.2)'
      : status === 'hostile'
        ? 'rgba(239, 68, 68, 0.2)'
        : 'rgba(245, 158, 11, 0.2)'
      }`,
  },
  '&:focus-visible': {
    outline: `2px solid ${theme.palette.info.main}`,
    outlineOffset: 2,
  },
  '&:focus:not(:focus-visible)': {
    outline: 'none',
  },
}));

const TrustProgress = styled(LinearProgress)<{ trustlevel: number }>(({ theme, trustlevel }) => ({
  height: 4,
  borderRadius: 2,
  backgroundColor: theme.palette.divider,
  '& .MuiLinearProgress-bar': {
    borderRadius: 2,
    backgroundColor:
      trustlevel >= 80
        ? theme.palette.success.main
        : trustlevel >= 60
          ? theme.palette.primary.main
          : trustlevel >= 40
            ? theme.palette.warning.main
            : theme.palette.error.main,
  },
}));

const StatusBadge = styled(Box, {
  shouldForwardProp: (prop: PropertyKey) => prop !== 'status',
})<{ status: string }>(({ theme, status }) => ({
  width: 8,
  height: 8,
  borderRadius: '50%',
  backgroundColor:
    status === 'active'
      ? theme.palette.success.main
      : status === 'hostile'
        ? theme.palette.error.main
        : theme.palette.warning.main,
  animation: status === 'active' ? 'pulse 2s infinite' : 'none',
  '@keyframes pulse': {
    '0%, 100%': { opacity: 1 },
    '50%': { opacity: 0.5 },
  },
}));

interface CharacterNetworksProps {
  loading?: boolean;
  error?: boolean;
}

const CharacterNetworks: React.FC<CharacterNetworksProps> = ({ loading, error }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { characters, loading: charactersLoading, error: charactersError, source } = useDashboardCharactersDataset();
  const [activeIndex, setActiveIndex] = useState(0);
  const [selectedCharacterId, setSelectedCharacterId] = useState<string | null>(null);
  const cardRefs = useRef<Array<HTMLButtonElement | null>>([]);

  const networkCharacters = useMemo(
    () =>
      characters.map((character, index) => ({
        ...character,
        roleLabel: character.role.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase()),
        connections: Math.max(2, (index % 5) + 2),
      })),
    [characters]
  );

  useEffect(() => {
    if (!networkCharacters.length) {
      return;
    }
    if (!selectedCharacterId || !networkCharacters.some((char) => char.id === selectedCharacterId)) {
      setSelectedCharacterId(networkCharacters[0].id);
      setActiveIndex(0);
    }
  }, [networkCharacters, selectedCharacterId]);

  useEffect(() => {
    const node = cardRefs.current[activeIndex];
    if (node && document.activeElement !== node) {
      node.focus();
    }
  }, [activeIndex]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return theme.palette.success.main;
      case 'hostile':
        return theme.palette.error.main;
      case 'inactive':
      default:
        return theme.palette.warning.main;
    }
  };

  const totalConnections = networkCharacters.reduce((sum, character) => sum + character.connections, 0);
  const activeCount = networkCharacters.filter((character) => character.status === 'active').length;
  const averageTrust = networkCharacters.length
    ? Math.round(networkCharacters.reduce((sum, character) => sum + character.trust, 0) / networkCharacters.length)
    : 0;

  const handleMoveFocus = useCallback(
    (direction: 1 | -1) => {
      if (!networkCharacters.length) {
        return;
      }
      setActiveIndex((prev) => {
        const next = (prev + direction + networkCharacters.length) % networkCharacters.length;
        return next;
      });
    },
    [networkCharacters.length]
  );

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent, index: number, characterId: string) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        setSelectedCharacterId((prev) => (prev === characterId ? null : characterId));
      }

      if (event.key === 'ArrowDown' || event.key === 'ArrowRight') {
        event.preventDefault();
        handleMoveFocus(1);
      }

      if (event.key === 'ArrowUp' || event.key === 'ArrowLeft') {
        event.preventDefault();
        handleMoveFocus(-1);
      }
    },
    [handleMoveFocus]
  );

  const combinedLoading = loading || charactersLoading;
  const combinedError = error || charactersError;
  const hasRenderableCharacters = networkCharacters.length > 0;
  const shouldShowError = Boolean(combinedError) && !hasRenderableCharacters;

  return (
    <GridTile
      title="Character Networks"
      data-testid="character-networks"
      data-role="character-networks"
      position={{
        desktop: { column: 'span 2', height: '320px' },
        tablet: { column: 'span 2', height: '300px' },
        mobile: { column: 'span 1', height: '220px' },
      }}
      loading={combinedLoading}
      error={shouldShowError}
    >
      <NetworkContainer>
        <Stack
          direction="row"
          spacing={1}
          justifyContent="center"
          sx={{ mb: 1.5, flexShrink: 0, flexWrap: 'wrap' }}
        >
          <Chip
            icon={<PersonIcon sx={{ fontSize: '16px' }} />}
            label={`${networkCharacters.length} Characters`}
            size="small"
            sx={{
              backgroundColor: (theme) => theme.palette.background.paper,
              borderColor: (theme) => theme.palette.divider,
              color: (theme) => theme.palette.text.secondary,
              fontSize: '0.7rem',
              height: '22px',
              '& .MuiChip-icon': { color: (theme) => theme.palette.primary.main },
            }}
          />
          <Chip
            icon={<LinkIcon sx={{ fontSize: '16px' }} />}
            label={`${totalConnections} Links`}
            size="small"
            sx={{
              backgroundColor: (theme) => theme.palette.background.paper,
              borderColor: (theme) => theme.palette.divider,
              color: (theme) => theme.palette.text.secondary,
              fontSize: '0.7rem',
              height: '22px',
              '& .MuiChip-icon': { color: (theme) => theme.palette.secondary.main },
            }}
          />
          <Chip
            icon={<GroupIcon sx={{ fontSize: '16px' }} />}
            label={`${activeCount} Active`}
            size="small"
            sx={{
              backgroundColor: 'rgba(0, 255, 157, 0.12)',
              borderColor: (theme) => theme.palette.success.main,
              color: 'rgba(0, 255, 157, 0.8)',
              fontSize: '0.7rem',
              height: '22px',
              '& .MuiChip-icon': { color: (theme) => theme.palette.success.main },
            }}
          />
          <Chip
            label={source === 'api' ? 'API feed' : 'Demo data'}
            size="small"
            color={source === 'api' ? 'success' : 'default'}
            sx={{
              fontSize: '0.7rem',
              height: '22px',
              fontWeight: 600,
            }}
          />
        </Stack>

        <Box sx={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
          <List dense sx={{ py: 0 }}>
            {networkCharacters.slice(0, isMobile ? 3 : 5).map((character, index) => (
              <Fade in key={character.id} timeout={300 + index * 100}>
                <CharacterCard
                  status={character.status}
                  data-character-id={character.id}
                  data-character-status={character.status}
                  data-character-name={character.name}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: index * 0.05 }}
                  whileHover={{ scale: 1.02 }}
                  data-testid="character-node"
                  role="button"
                  type="button"
                  aria-pressed={selectedCharacterId === character.id}
                  aria-controls={`character-detail-${character.id}`}
                  tabIndex={activeIndex === index ? 0 : -1}
                  ref={(node: HTMLButtonElement | null) => {
                    cardRefs.current[index] = node;
                  }}
                  onFocus={() => setActiveIndex(index)}
                  onKeyDown={(event) => handleKeyDown(event, index, character.id)}
                  onClick={() => setSelectedCharacterId((prev) => (prev === character.id ? null : character.id))}
                >
                  <Avatar
                    sx={{
                      width: isMobile ? 32 : 36,
                      height: isMobile ? 32 : 36,
                      backgroundColor: getStatusColor(character.status),
                      border: (theme) => `2px solid ${theme.palette.background.default}`,
                      mr: 1.5,
                      position: 'relative',
                    }}
                  >
                    <PersonIcon fontSize="small" />
                    <StatusBadge
                      status={character.status}
                      sx={{
                        position: 'absolute',
                        bottom: -2,
                        right: -2,
                        border: (theme) => `2px solid ${theme.palette.background.default}`,
                      }}
                    />
                  </Avatar>

                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Stack direction="row" alignItems="center" spacing={0.5} sx={{ mb: 0.25 }}>
                      <Typography
                        variant={isMobile ? 'caption' : 'body2'}
                        fontWeight={600}
                        noWrap
                        sx={{ color: 'var(--color-text-primary)' }}
                      >
                        {character.name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                        • {character.roleLabel}
                      </Typography>
                    </Stack>

                    <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
                      <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', minWidth: '50px' }}>
                        Trust: {character.trust}%
                      </Typography>
                      <TrustProgress
                        variant="determinate"
                        value={character.trust}
                        trustlevel={character.trust}
                        sx={{ flex: 1 }}
                        aria-label={`${character.name} trust level ${character.trust} percent`}
                        data-testid="character-trust-progress"
                      />
                    </Stack>

                    <Stack direction="row" alignItems="center" spacing={0.5}>
                      <LinkIcon sx={{ fontSize: '12px', color: 'secondary.main' }} data-testid="character-connection-icon" />
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ fontSize: '0.7rem' }}
                        data-testid="character-connection-count"
                      >
                        {character.connections} connections
                      </Typography>
                      <Chip
                        label={character.status}
                        size="small"
                        sx={{
                          height: '16px',
                          fontSize: '0.6rem',
                          ml: 'auto',
                          backgroundColor: 'rgba(0, 240, 255, 0.12)',
                          color: getStatusColor(character.status),
                          borderColor: getStatusColor(character.status),
                        }}
                        data-testid="character-status"
                      />
                    </Stack>

                    <Box
                      id={`character-detail-${character.id}`}
                      sx={{
                        mt: 0.5,
                        color: selectedCharacterId === character.id ? 'text.primary' : 'text.disabled',
                        fontSize: '0.65rem',
                      }}
                    >
                      <Typography variant="caption">
                        {selectedCharacterId === character.id
                          ? `${character.name} ready for orchestration`
                          : 'Select to inspect network details'}
                      </Typography>
                    </Box>
                  </Box>
                </CharacterCard>
              </Fade>
            ))}
          </List>
        </Box>

        {!isMobile && (
          <Box
            sx={{
              pt: 1,
              mt: 1,
              borderTop: (theme) => `1px solid ${theme.palette.divider}`,
              flexShrink: 0,
            }}
          >
            <Stack direction="row" justifyContent="space-between" alignItems="center" data-testid="network-health">
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                Network Health
              </Typography>
              <Stack direction="row" spacing={1} alignItems="center">
                <NetworkIcon sx={{ fontSize: '16px', color: getStatusColor(averageTrust >= 60 ? 'active' : 'inactive') }} />
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                  {averageTrust}% Avg Trust
                </Typography>
              </Stack>
            </Stack>
          </Box>
        )}
      </NetworkContainer>
    </GridTile>
  );
};

export default CharacterNetworks;
