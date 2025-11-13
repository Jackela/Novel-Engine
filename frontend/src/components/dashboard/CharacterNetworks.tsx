import React, { useState } from 'react';
import { 
  Box, 
  Typography, 
  Chip, 
  Stack, 
  List,
  ListItem,
  ListItemText,
  Avatar,
  LinearProgress,
  useTheme,
  useMediaQuery,
  Fade,
} from '@mui/material';
import { styled, alpha } from '@mui/material/styles';
import { motion } from 'framer-motion';
import { 
  Person as PersonIcon,
  Groups as GroupIcon,
  Link as LinkIcon,
  Diversity3 as NetworkIcon,
} from '@mui/icons-material';
import GridTile from '../layout/GridTile';

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

const CharacterCard = styled(motion(Box))<{ status: string }>(({ theme, status }) => ({
  display: 'flex',
  alignItems: 'center',
  padding: theme.spacing(1),
  borderRadius: theme.shape.borderRadius,
  backgroundColor: theme.palette.background.paper,
  border: `1px solid ${theme.palette.divider}`,
  marginBottom: theme.spacing(1),
  transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
  '&:hover': {
    backgroundColor: 'var(--color-bg-tertiary)',
    borderColor: status === 'active' ? theme.palette.success.main : status === 'hostile' ? theme.palette.error.main : theme.palette.warning.main,
    transform: 'translateY(-2px)',
    boxShadow: `0 4px 8px ${
      status === 'active' ? 'rgba(16, 185, 129, 0.2)' : 
      status === 'hostile' ? 'rgba(239, 68, 68, 0.2)' : 
      'rgba(245, 158, 11, 0.2)'
    }`,
  },
}));

const TrustProgress = styled(LinearProgress)<{ trustlevel: number }>(({ theme, trustlevel }) => ({
  height: 4,
  borderRadius: 2,
  backgroundColor: theme.palette.divider,
  '& .MuiLinearProgress-bar': {
    borderRadius: 2,
    backgroundColor: 
      trustlevel >= 80 ? theme.palette.success.main :
      trustlevel >= 60 ? theme.palette.primary.main :
      trustlevel >= 40 ? theme.palette.warning.main :
      theme.palette.error.main,
  },
}));

const StatusBadge = styled(Box)<{ status: string }>(({ theme, status }) => ({
  width: 8,
  height: 8,
  borderRadius: '50%',
  backgroundColor: 
    status === 'active' ? theme.palette.success.main :
    status === 'hostile' ? theme.palette.error.main :
    theme.palette.warning.main,
  animation: status === 'active' ? 'pulse 2s infinite' : 'none',
  '@keyframes pulse': {
    '0%, 100%': { opacity: 1 },
    '50%': { opacity: 0.5 },
  },
}));

interface CharacterData {
  id: string;
  name: string;
  role: string;
  trustLevel: number;
  connections: number;
  status: 'active' | 'inactive' | 'hostile';
}

interface CharacterNetworksProps {
  loading?: boolean;
  error?: boolean;
}

const CharacterNetworks: React.FC<CharacterNetworksProps> = ({ loading, error }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  
  const [characters] = useState<CharacterData[]>([
    {
      id: '1',
      name: 'Aria Shadowbane',
      role: 'Rogue',
      trustLevel: 85,
      connections: 4,
      status: 'active'
    },
    {
      id: '2', 
      name: 'Elder Thorne',
      role: 'Mentor',
      trustLevel: 95,
      connections: 6,
      status: 'active'
    },
    {
      id: '3',
      name: 'Merchant Aldric', 
      role: 'Trader',
      trustLevel: 65,
      connections: 3,
      status: 'active'
    },
    {
      id: '4',
      name: 'Captain Vex',
      role: 'Guard Captain',
      trustLevel: 40,
      connections: 2,
      status: 'hostile'
    },
    {
      id: '5',
      name: 'Mystic Vera',
      role: 'Oracle',
      trustLevel: 78,
      connections: 5,
      status: 'inactive'
    }
  ]);

  const getStatusColor = (status: CharacterData['status']) => {
    switch (status) {
      case 'active':
        return theme.palette.success.main;
      case 'hostile':
        return theme.palette.error.main;
      case 'inactive':
        return theme.palette.warning.main;
      default:
        return theme.palette.text.secondary;
    }
  };

  const getTrustColor = (trust: number) => {
    if (trust >= 80) return theme.palette.success.main;
    if (trust >= 60) return theme.palette.primary.main;
    if (trust >= 40) return theme.palette.warning.main;
    return theme.palette.error.main;
  };

  const totalConnections = characters.reduce((sum, c) => sum + c.connections, 0);
  const activeCount = characters.filter(c => c.status === 'active').length;
  const averageTrust = Math.round(
    characters.reduce((sum, c) => sum + c.trustLevel, 0) / characters.length
  );

  return (
    <GridTile
      title="Character Networks"
      data-testid="character-networks"
      data-role="character-networks"
      position={{
        desktop: { column: '1 / 7', height: '280px' },
        tablet: { column: '1 / 5', height: '260px' },
        mobile: { height: '160px' },
      }}
      loading={loading}
      error={error}
    >
      <NetworkContainer>
        {/* Stats Header */}
        <Stack 
          direction="row" 
          spacing={1} 
          justifyContent="center" 
          sx={{ mb: 1.5, flexShrink: 0, flexWrap: 'wrap' }}
        >
          <Chip 
            icon={<PersonIcon sx={{ fontSize: '16px' }} />}
            label={`${characters.length} Characters`} 
            size="small" 
            sx={{
              backgroundColor: (theme) => theme.palette.background.paper,
              borderColor: (theme) => theme.palette.divider,
              color: (theme) => theme.palette.text.secondary,
              fontSize: '0.7rem',
              height: '22px',
              '& .MuiChip-icon': { color: (theme) => theme.palette.primary.main }
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
              '& .MuiChip-icon': { color: (theme) => theme.palette.secondary.main }
            }}
          />
          <Chip 
            icon={<GroupIcon sx={{ fontSize: '16px' }} />}
            label={`${activeCount} Active`} 
            size="small" 
            sx={{
              backgroundColor: (theme) => alpha(theme.palette.success.main, 0.12),
              borderColor: (theme) => theme.palette.success.main,
              color: (theme) => alpha(theme.palette.success.main, 0.8),
              fontSize: '0.7rem',
              height: '22px',
              '& .MuiChip-icon': { color: (theme) => theme.palette.success.main }
            }}
          />
        </Stack>

        {/* Character List */}
        <Box sx={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
          <List dense sx={{ py: 0 }}>
            {characters.slice(0, isMobile ? 3 : 5).map((character, index) => (
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
                      <Typography 
                        variant="caption" 
                        color="text.secondary"
                        sx={{ fontSize: '0.7rem' }}
                      >
                        • {character.role}
                      </Typography>
                    </Stack>

                    <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
                      <Typography 
                        variant="caption" 
                        color="text.secondary"
                        sx={{ fontSize: '0.7rem', minWidth: '50px' }}
                      >
                        Trust: {character.trustLevel}%
                      </Typography>
                      <TrustProgress
                        variant="determinate"
                        value={character.trustLevel}
                        trustlevel={character.trustLevel}
                        sx={{ flex: 1 }}
                        aria-label={`${character.name} trust level ${character.trustLevel} percent`}
                        data-testid="character-trust-progress"
                      />
                    </Stack>

                    <Stack direction="row" alignItems="center" spacing={0.5}>
                      <LinkIcon sx={{ fontSize: '12px', color: 'secondary.main' }} />
                      <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                        {character.connections} connections
                      </Typography>
                      <Chip
                        label={character.status}
                        size="small"
                        sx={{
                          height: '16px',
                          fontSize: '0.6rem',
                          ml: 'auto',
                          backgroundColor: alpha(getStatusColor(character.status), 0.12),
                          color: getStatusColor(character.status),
                          borderColor: getStatusColor(character.status),
                        }}
                      />
                    </Stack>
                  </Box>
                </CharacterCard>
              </Fade>
            ))}
          </List>
        </Box>

        {/* Summary Footer */}
        {!isMobile && (
          <Box 
            sx={{ 
              pt: 1, 
              mt: 1, 
              borderTop: (theme) => `1px solid ${theme.palette.divider}`,
              flexShrink: 0,
            }}
          >
            <Stack direction="row" justifyContent="space-between" alignItems="center">
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                Network Health
              </Typography>
              <Stack direction="row" spacing={1} alignItems="center">
                <NetworkIcon sx={{ fontSize: '16px', color: getTrustColor(averageTrust) }} />
                <Typography 
                  variant="caption" 
                  sx={{ 
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    color: getTrustColor(averageTrust)
                  }}
                >
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
