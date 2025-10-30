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
import { styled } from '@mui/material/styles';
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
  backgroundColor: '#111113',
  border: `1px solid #2a2a30`,
  marginBottom: theme.spacing(1),
  transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
  '&:hover': {
    backgroundColor: '#1a1a1d',
    borderColor: status === 'active' ? '#10b981' : status === 'hostile' ? '#ef4444' : '#f59e0b',
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
  backgroundColor: '#2a2a30',
  '& .MuiLinearProgress-bar': {
    borderRadius: 2,
    backgroundColor: 
      trustlevel >= 80 ? '#10b981' :
      trustlevel >= 60 ? '#6366f1' :
      trustlevel >= 40 ? '#f59e0b' :
      '#ef4444',
  },
}));

const StatusBadge = styled(Box)<{ status: string }>(({ theme, status }) => ({
  width: 8,
  height: 8,
  borderRadius: '50%',
  backgroundColor: 
    status === 'active' ? '#10b981' :
    status === 'hostile' ? '#ef4444' :
    '#f59e0b',
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
      case 'active': return '#10b981';
      case 'hostile': return '#ef4444';
      case 'inactive': return '#f59e0b';
      default: return '#808088';
    }
  };

  const getTrustColor = (trust: number) => {
    if (trust >= 80) return '#10b981';
    if (trust >= 60) return '#6366f1';
    if (trust >= 40) return '#f59e0b';
    return '#ef4444';
  };

  const totalConnections = characters.reduce((sum, c) => sum + c.connections, 0);
  const activeCount = characters.filter(c => c.status === 'active').length;
  const averageTrust = Math.round(
    characters.reduce((sum, c) => sum + c.trustLevel, 0) / characters.length
  );

  return (
    <GridTile
      title="Character Networks"
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
              backgroundColor: '#111113',
              borderColor: '#2a2a30',
              color: '#b0b0b8',
              fontSize: '0.7rem',
              height: '22px',
              '& .MuiChip-icon': { color: '#6366f1' }
            }}
          />
          <Chip 
            icon={<LinkIcon sx={{ fontSize: '16px' }} />}
            label={`${totalConnections} Links`} 
            size="small" 
            sx={{
              backgroundColor: '#111113',
              borderColor: '#2a2a30',
              color: '#b0b0b8',
              fontSize: '0.7rem',
              height: '22px',
              '& .MuiChip-icon': { color: '#8b5cf6' }
            }}
          />
          <Chip 
            icon={<GroupIcon sx={{ fontSize: '16px' }} />}
            label={`${activeCount} Active`} 
            size="small" 
            sx={{
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              borderColor: '#10b981',
              color: '#6ee7b7',
              fontSize: '0.7rem',
              height: '22px',
              '& .MuiChip-icon': { color: '#10b981' }
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
                      border: '2px solid #0a0a0b',
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
                        border: '2px solid #0a0a0b',
                      }}
                    />
                  </Avatar>

                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Stack direction="row" alignItems="center" spacing={0.5} sx={{ mb: 0.25 }}>
                      <Typography 
                        variant={isMobile ? 'caption' : 'body2'} 
                        fontWeight={600} 
                        noWrap
                        sx={{ color: '#f0f0f2' }}
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
                      />
                    </Stack>

                    <Stack direction="row" alignItems="center" spacing={0.5}>
                      <LinkIcon sx={{ fontSize: '12px', color: '#8b5cf6' }} />
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
                          backgroundColor: `${getStatusColor(character.status)}20`,
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
              borderTop: '1px solid #2a2a30',
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
