import React, { useState } from 'react';
import { 
  Box, 
  Typography, 
  Chip, 
  Stack, 
  List,
  ListItem,
  Avatar,
  LinearProgress,
  useTheme,
  useMediaQuery 
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { 
  Person as PersonIcon,
  Groups as GroupIcon,
  Link as LinkIcon 
} from '@mui/icons-material';
import GridTile from '../layout/GridTile';

const NetworkContainer = styled(Box)({
  width: '100%',
  height: '100%',
  position: 'relative',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
});

const PlaceholderContent = styled(Box)(({ theme }) => ({
  textAlign: 'center',
  padding: theme.spacing(2),
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
      case 'active': return theme.palette.success.main;
      case 'hostile': return theme.palette.error.main;
      case 'inactive': return theme.palette.warning.main;
      default: return theme.palette.grey[500];
    }
  };

  const getTrustColor = (trust: number) => {
    if (trust >= 80) return 'success';
    if (trust >= 60) return 'primary';
    if (trust >= 40) return 'warning';
    return 'error';
  };

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
        {isMobile ? (
          // Mobile: Character list with key metrics
          <Box sx={{ height: '100%', overflow: 'auto' }}>
            <Stack spacing={1} sx={{ p: 1 }}>
              {characters.slice(0, 3).map((character) => (
                <Box
                  key={character.id}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    p: 1,
                    borderRadius: 1,
                    bgcolor: 'action.hover',
                    gap: 1
                  }}
                >
                  <Avatar
                    sx={{
                      width: 32,
                      height: 32,
                      bgcolor: getStatusColor(character.status)
                    }}
                  >
                    <PersonIcon fontSize="small" />
                  </Avatar>
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography variant="body2" fontWeight={500} noWrap>
                      {character.name}
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <Typography variant="caption" color="text.secondary">
                        Trust: {character.trustLevel}%
                      </Typography>
                      <LinearProgress
                        variant="determinate"
                        value={character.trustLevel}
                        sx={{ flex: 1, height: 4, borderRadius: 2 }}
                        color={getTrustColor(character.trustLevel)}
                      />
                    </Box>
                  </Box>
                  <Chip
                    label={`${character.connections}`}
                    size="small"
                    icon={<LinkIcon />}
                    variant="outlined"
                  />
                </Box>
              ))}
              <Box sx={{ textAlign: 'center', pt: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  {characters.length} characters • {characters.reduce((sum, c) => sum + c.connections, 0)} total connections
                </Typography>
              </Box>
            </Stack>
          </Box>
        ) : (
          // Desktop: Network overview with stats
          <Box sx={{ height: '100%', p: 2 }}>
            <Stack spacing={2}>
              <Box>
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  Character Relationships
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Network of character relationships, trust levels, and social dynamics.
                </Typography>
              </Box>
              
              <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap">
                <Chip 
                  label={`${characters.length} Characters`} 
                  size="small" 
                  variant="outlined"
                  icon={<PersonIcon />}
                />
                <Chip 
                  label={`${characters.reduce((sum, c) => sum + c.connections, 0)} Connections`} 
                  size="small" 
                  variant="outlined"
                  icon={<LinkIcon />}
                />
                <Chip 
                  label={`${characters.filter(c => c.status === 'active').length} Active`} 
                  size="small" 
                  variant="outlined"
                  icon={<GroupIcon />}
                />
              </Stack>

              <List dense>
                {characters.slice(0, 3).map((character) => (
                  <ListItem key={character.id} sx={{ px: 0 }}>
                    <Avatar
                      sx={{
                        width: 24,
                        height: 24,
                        bgcolor: getStatusColor(character.status),
                        mr: 2
                      }}
                    >
                      <PersonIcon fontSize="small" />
                    </Avatar>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="body2" fontWeight={500}>
                        {character.name} • {character.role}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Trust: {character.trustLevel}% • {character.connections} connections
                      </Typography>
                    </Box>
                  </ListItem>
                ))}
              </List>
            </Stack>
          </Box>
        )}
      </NetworkContainer>
    </GridTile>
  );
};

export default CharacterNetworks;