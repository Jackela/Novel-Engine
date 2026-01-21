import React, { useMemo, useRef, useState, useEffect, useCallback } from 'react';
import { Box } from '@mui/material';
import { Typography } from '@mui/material';
import { Chip } from '@mui/material';
import { Stack } from '@mui/material';
import { List } from '@mui/material';
import { Avatar } from '@mui/material';
import { LinearProgress } from '@mui/material';
import { Fade } from '@mui/material';
import { useMediaQuery } from '@mui/material';
import { styled, useTheme, alpha } from '@mui/material';
import { motion } from 'framer-motion';
import { Person as PersonIcon, Groups as GroupIcon, Link as LinkIcon, Diversity3 as NetworkIcon } from '@mui/icons-material';
import GridTile from '@/components/layout/GridTile';
import { useDashboardCharactersDataset } from '@/hooks/useDashboardCharactersDataset';
import type { DashboardCharacter } from '@/hooks/useDashboardCharactersDataset';

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
      ? alpha(theme.palette.success.main, 0.2)
      : status === 'hostile'
        ? alpha(theme.palette.error.main, 0.2)
        : alpha(theme.palette.warning.main, 0.2)
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

interface NetworkCharacter extends DashboardCharacter {
  roleLabel: string;
  connections: number;
}

const buildNetworkCharacters = (characters: DashboardCharacter[]): NetworkCharacter[] =>
  characters.map((character, index) => ({
    ...character,
    roleLabel: character.role.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase()),
    connections: Math.max(2, (index % 5) + 2),
  }));

const useCharacterNetworkSelection = (networkCharacters: NetworkCharacter[]) => {
  const [activeIndex, setActiveIndex] = useState(0);
  const [selectedCharacterId, setSelectedCharacterId] = useState<string | null>(null);
  const cardRefs = useRef<Array<HTMLButtonElement | null>>([]);

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

  const handleMoveFocus = useCallback(
    (direction: 1 | -1) => {
      if (!networkCharacters.length) {
        return;
      }
      setActiveIndex((prev) => (prev + direction + networkCharacters.length) % networkCharacters.length);
    },
    [networkCharacters.length]
  );

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent, characterId: string) => {
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

  const handleSelect = useCallback((characterId: string) => {
    setSelectedCharacterId((prev) => (prev === characterId ? null : characterId));
  }, []);

  return {
    activeIndex,
    selectedCharacterId,
    cardRefs,
    setActiveIndex,
    handleKeyDown,
    handleSelect,
  };
};

const getStatusColor = (status: string, theme: ReturnType<typeof useTheme>) => {
  if (status === 'active') return theme.palette.success.main;
  if (status === 'hostile') return theme.palette.error.main;
  return theme.palette.warning.main;
};

const getNetworkMetrics = (networkCharacters: NetworkCharacter[]) => {
  const totalConnections = networkCharacters.reduce((sum, character) => sum + character.connections, 0);
  const activeCount = networkCharacters.filter((character) => character.status === 'active').length;
  const averageTrust = networkCharacters.length
    ? Math.round(networkCharacters.reduce((sum, character) => sum + character.trust, 0) / networkCharacters.length)
    : 0;

  return {
    totalConnections,
    activeCount,
    averageTrust,
  };
};

const CharacterNetworkSummary: React.FC<{
  characterCount: number;
  totalConnections: number;
  activeCount: number;
  source: string;
}> = ({ characterCount, totalConnections, activeCount, source }) => (
  <Stack direction="row" spacing={1} justifyContent="center" sx={{ mb: 1.5, flexShrink: 0, flexWrap: 'wrap' }}>
    <Chip
      icon={<PersonIcon sx={{ fontSize: '16px' }} />}
      label={`${characterCount} Characters`}
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
        backgroundColor: (theme) => alpha(theme.palette.success.main, 0.12),
        borderColor: (theme) => theme.palette.success.main,
        color: (theme) => theme.palette.success.main,
        fontSize: '0.7rem',
        height: '22px',
        '& .MuiChip-icon': { color: (theme) => theme.palette.success.main },
      }}
    />
    <Chip
      label={source === 'api' ? 'API feed' : 'Demo data'}
      size="small"
      color={source === 'api' ? 'success' : 'default'}
      sx={{ fontSize: '0.7rem', height: '22px', fontWeight: 600 }}
    />
  </Stack>
);

const CharacterNetworkItem: React.FC<{
  character: NetworkCharacter;
  isMobile: boolean;
  isActive: boolean;
  isSelected: boolean;
  theme: ReturnType<typeof useTheme>;
  cardRef: (node: HTMLButtonElement | null) => void;
  onFocus: () => void;
  onKeyDown: (event: React.KeyboardEvent) => void;
  onClick: () => void;
}> = ({
  character,
  isMobile,
  isActive,
  isSelected,
  theme,
  cardRef,
  onFocus,
  onKeyDown,
  onClick,
}) => (
  <CharacterCard
    status={character.status}
    data-character-id={character.id}
    data-character-status={character.status}
    data-character-name={character.name}
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.3 }}
    whileHover={{ scale: 1.02 }}
    data-testid="character-node"
    role="button"
    type="button"
    aria-pressed={isSelected}
    aria-controls={`character-detail-${character.id}`}
    tabIndex={isActive ? 0 : -1}
    ref={cardRef}
    onFocus={onFocus}
    onKeyDown={onKeyDown}
    onClick={onClick}
  >
    <CharacterNetworkAvatar character={character} isMobile={isMobile} theme={theme} />
    <CharacterNetworkInfo
      character={character}
      isMobile={isMobile}
      isSelected={isSelected}
      theme={theme}
    />
  </CharacterCard>
);

const CharacterNetworkAvatar: React.FC<{
  character: NetworkCharacter;
  isMobile: boolean;
  theme: ReturnType<typeof useTheme>;
}> = ({ character, isMobile, theme }) => (
  <Avatar
    sx={{
      width: isMobile ? 32 : 36,
      height: isMobile ? 32 : 36,
      backgroundColor: getStatusColor(character.status, theme),
      border: (themeInner) => `2px solid ${themeInner.palette.background.default}`,
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
        border: (themeInner) => `2px solid ${themeInner.palette.background.default}`,
      }}
    />
  </Avatar>
);

const CharacterNetworkInfo: React.FC<{
  character: NetworkCharacter;
  isMobile: boolean;
  isSelected: boolean;
  theme: ReturnType<typeof useTheme>;
}> = ({ character, isMobile, isSelected, theme }) => (
  <Box sx={{ flex: 1, minWidth: 0 }}>
    <CharacterNetworkHeader character={character} isMobile={isMobile} />
    <CharacterNetworkTrust character={character} />
    <CharacterNetworkMeta character={character} theme={theme} />
    <CharacterNetworkDetail character={character} isSelected={isSelected} />
  </Box>
);

const CharacterNetworkHeader: React.FC<{
  character: NetworkCharacter;
  isMobile: boolean;
}> = ({ character, isMobile }) => (
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
);

const CharacterNetworkTrust: React.FC<{ character: NetworkCharacter }> = ({ character }) => (
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
);

const CharacterNetworkMeta: React.FC<{
  character: NetworkCharacter;
  theme: ReturnType<typeof useTheme>;
}> = ({ character, theme }) => (
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
        backgroundColor: alpha(getStatusColor(character.status, theme), 0.12),
        color: getStatusColor(character.status, theme),
        borderColor: getStatusColor(character.status, theme),
      }}
      data-testid="character-status"
    />
  </Stack>
);

const CharacterNetworkDetail: React.FC<{
  character: NetworkCharacter;
  isSelected: boolean;
}> = ({ character, isSelected }) => (
  <Box
    id={`character-detail-${character.id}`}
    sx={{
      mt: 0.5,
      color: isSelected ? 'text.primary' : 'text.disabled',
      fontSize: '0.65rem',
    }}
  >
    <Typography variant="caption">
      {isSelected ? `${character.name} ready for orchestration` : 'Select to inspect network details'}
    </Typography>
  </Box>
);

const CharacterNetworkList: React.FC<{
  characters: NetworkCharacter[];
  isMobile: boolean;
  activeIndex: number;
  selectedCharacterId: string | null;
  theme: ReturnType<typeof useTheme>;
  cardRefs: React.MutableRefObject<Array<HTMLButtonElement | null>>;
  onFocusIndex: (index: number) => void;
  onKeyDown: (event: React.KeyboardEvent, characterId: string) => void;
  onSelect: (characterId: string) => void;
}> = ({
  characters,
  isMobile,
  activeIndex,
  selectedCharacterId,
  theme,
  cardRefs,
  onFocusIndex,
  onKeyDown,
  onSelect,
}) => (
  <Box sx={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
    <List dense sx={{ py: 0 }}>
      {characters.slice(0, isMobile ? 3 : 5).map((character, index) => (
        <Fade in key={character.id} timeout={300 + index * 100}>
          <CharacterNetworkItem
            character={character}
            isMobile={isMobile}
            isActive={activeIndex === index}
            isSelected={selectedCharacterId === character.id}
            theme={theme}
            cardRef={(node: HTMLButtonElement | null) => {
              cardRefs.current[index] = node;
            }}
            onFocus={() => onFocusIndex(index)}
            onKeyDown={(event) => onKeyDown(event, character.id)}
            onClick={() => onSelect(character.id)}
          />
        </Fade>
      ))}
    </List>
  </Box>
);

const CharacterNetworkFooter: React.FC<{
  averageTrust: number;
  theme: ReturnType<typeof useTheme>;
}> = ({ averageTrust, theme }) => (
  <Box
    sx={{
      pt: 1,
      mt: 1,
      borderTop: (themeInner) => `1px solid ${themeInner.palette.divider}`,
      flexShrink: 0,
    }}
  >
    <Stack direction="row" justifyContent="space-between" alignItems="center" data-testid="network-health">
      <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
        Network Health
      </Typography>
      <Stack direction="row" spacing={1} alignItems="center">
        <NetworkIcon
          sx={{
            fontSize: '16px',
            color: getStatusColor(averageTrust >= 60 ? 'active' : 'inactive', theme),
          }}
        />
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
          {averageTrust}% Avg Trust
        </Typography>
      </Stack>
    </Stack>
  </Box>
);

const CharacterNetworks: React.FC<CharacterNetworksProps> = ({ loading, error }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { characters, loading: charactersLoading, error: charactersError, source } =
    useDashboardCharactersDataset();
  const networkCharacters = useMemo(() => buildNetworkCharacters(characters), [characters]);
  const { totalConnections, activeCount, averageTrust } = getNetworkMetrics(networkCharacters);
  const selection = useCharacterNetworkSelection(networkCharacters);

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
        <CharacterNetworkSummary
          characterCount={networkCharacters.length}
          totalConnections={totalConnections}
          activeCount={activeCount}
          source={source}
        />

        <CharacterNetworkList
          characters={networkCharacters}
          isMobile={isMobile}
          activeIndex={selection.activeIndex}
          selectedCharacterId={selection.selectedCharacterId}
          theme={theme}
          cardRefs={selection.cardRefs}
          onFocusIndex={selection.setActiveIndex}
          onKeyDown={selection.handleKeyDown}
          onSelect={selection.handleSelect}
        />

        {!isMobile && <CharacterNetworkFooter averageTrust={averageTrust} theme={theme} />}
      </NetworkContainer>
    </GridTile>
  );
};

export default CharacterNetworks;
