import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Chip, 
  Stack, 
  Avatar,
  useTheme,
  useMediaQuery 
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  PlayArrow as EventIcon,
  TrendingFlat as ConnectionIcon,
  AccountTree as BranchIcon,
  CheckCircle as CompleteIcon
} from '@mui/icons-material';
import GridTile from '../layout/GridTile';

const FlowContainer = styled(Box)(({ theme }) => ({
  width: '100%',
  height: '100%',
  position: 'relative',
  padding: theme.spacing(1),
  overflowX: 'auto',
  overflowY: 'hidden',
  
  // Mobile: vertical flow
  [theme.breakpoints.down('md')]: {
    overflowX: 'hidden',
    overflowY: 'auto',
    padding: theme.spacing(0.5),
  },
}));

const EventNode = styled(Box)<{ status: 'completed' | 'active' | 'pending' }>(
  ({ theme, status }) => ({
    display: 'flex',
    alignItems: 'center',
    padding: theme.spacing(1),
    borderRadius: theme.spacing(1),
    backgroundColor: status === 'active' 
      ? theme.palette.primary.main + '20'
      : theme.palette.action.hover,
    border: status === 'active'
      ? `2px solid ${theme.palette.primary.main}`
      : `1px solid ${theme.palette.divider}`,
    minWidth: '180px',
    margin: theme.spacing(0.5),
    
    [theme.breakpoints.down('md')]: {
      minWidth: 'auto',
      width: '100%',
      padding: theme.spacing(0.75),
    },
  })
);

const FlowConnection = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: theme.spacing(0.5),
  
  [theme.breakpoints.down('md')]: {
    transform: 'rotate(90deg)',
    height: '20px',
  },
}));

const MobileFlowColumn = styled(Box)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  width: '100%',
}));

const DesktopFlowRow = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'flex-start',
  flexWrap: 'nowrap',
  minWidth: 'max-content',
}));

interface EventFlowNode {
  id: string;
  title: string;
  description: string;
  status: 'completed' | 'active' | 'pending';
  type: 'story' | 'character' | 'system' | 'branch';
  connections: string[];
}

interface EventCascadeFlowProps {
  loading?: boolean;
  error?: boolean;
}

const EventCascadeFlow: React.FC<EventCascadeFlowProps> = ({ loading, error }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  
  const [flowNodes] = useState<EventFlowNode[]>([
    {
      id: '1',
      title: 'Ancient Prophecy',
      description: 'Prophecy discovery triggers quest',
      status: 'completed',
      type: 'story',
      connections: ['2'],
    },
    {
      id: '2', 
      title: 'Merchant Meeting',
      description: 'Aldric provides crucial information',
      status: 'active',
      type: 'character',
      connections: ['3', '4'],
    },
    {
      id: '3',
      title: 'Trust Building',
      description: 'Relationship development arc',
      status: 'active',
      type: 'character',
      connections: ['5'],
    },
    {
      id: '4',
      title: 'Crystal Caverns',
      description: 'New location discovered',
      status: 'pending',
      type: 'story',
      connections: ['5'],
    },
    {
      id: '5',
      title: 'Final Confrontation',
      description: 'Climax event pending',
      status: 'pending',
      type: 'story',
      connections: [],
    },
  ]);

  const getEventIcon = (type: EventFlowNode['type'], status: EventFlowNode['status']) => {
    if (status === 'completed') return <CompleteIcon fontSize="small" />;
    
    switch (type) {
      case 'story':
        return <EventIcon fontSize="small" />;
      case 'character':
        return <EventIcon fontSize="small" />;
      case 'branch':
        return <BranchIcon fontSize="small" />;
      default:
        return <EventIcon fontSize="small" />;
    }
  };

  const getStatusColor = (status: EventFlowNode['status']) => {
    switch (status) {
      case 'completed':
        return theme.palette.success.main;
      case 'active':
        return theme.palette.primary.main;
      default:
        return theme.palette.text.secondary;
    }
  };

  return (
    <GridTile
      title="Event Cascade Flow"
      position={{
        desktop: { column: '8 / 13', height: '280px' },
        tablet: { column: '5 / 9', height: '260px' },
        mobile: { height: '160px' },
      }}
      loading={loading}
      error={error}
    >
      <FlowContainer>
        {isMobile ? (
          // Mobile: Vertical flow visualization
          <MobileFlowColumn>
            <Stack spacing={1} sx={{ width: '100%', pb: 1 }}>
              <Stack direction="row" spacing={1} justifyContent="center">
                <Chip label="5 Events" size="small" variant="outlined" />
                <Chip label="6 Dependencies" size="small" variant="outlined" />
              </Stack>
            </Stack>
            
            <Box sx={{ width: '100%', maxHeight: '200px', overflowY: 'auto' }}>
              {flowNodes.map((node, index) => (
                <Box key={node.id}>
                  <EventNode status={node.status}>
                    <Avatar
                      sx={{
                        bgcolor: 'transparent',
                        color: getStatusColor(node.status),
                        width: 32,
                        height: 32,
                        mr: 1,
                      }}
                    >
                      {getEventIcon(node.type, node.status)}
                    </Avatar>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="caption" fontWeight={600} sx={{ lineHeight: 1.2 }}>
                        {node.title}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', fontSize: '0.7rem' }}>
                        {node.description}
                      </Typography>
                    </Box>
                    <Chip
                      label={node.status}
                      size="small"
                      variant="outlined"
                      sx={{ 
                        height: '20px', 
                        fontSize: '0.6rem',
                        color: getStatusColor(node.status),
                        borderColor: getStatusColor(node.status)
                      }}
                    />
                  </EventNode>
                  
                  {index < flowNodes.length - 1 && node.connections.length > 0 && (
                    <FlowConnection>
                      <ConnectionIcon 
                        fontSize="small" 
                        sx={{ color: theme.palette.text.secondary, transform: 'rotate(90deg)' }}
                      />
                    </FlowConnection>
                  )}
                </Box>
              ))}
            </Box>
          </MobileFlowColumn>
        ) : (
          // Desktop: Horizontal flow visualization
          <Box sx={{ height: '100%' }}>
            <Stack spacing={1} sx={{ mb: 2 }}>
              <Stack direction="row" spacing={1} justifyContent="center">
                <Chip label="5 Events" size="small" variant="outlined" />
                <Chip label="6 Dependencies" size="small" variant="outlined" />
                <Chip label="2 Active" size="small" color="primary" variant="outlined" />
              </Stack>
            </Stack>
            
            <DesktopFlowRow>
              {flowNodes.map((node, index) => (
                <React.Fragment key={node.id}>
                  <EventNode status={node.status}>
                    <Avatar
                      sx={{
                        bgcolor: 'transparent',
                        color: getStatusColor(node.status),
                        width: 36,
                        height: 36,
                        mr: 1.5,
                      }}
                    >
                      {getEventIcon(node.type, node.status)}
                    </Avatar>
                    <Box>
                      <Typography variant="body2" fontWeight={600}>
                        {node.title}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {node.description}
                      </Typography>
                      <Box sx={{ mt: 0.5 }}>
                        <Chip
                          label={node.status}
                          size="small"
                          variant="outlined"
                          sx={{ 
                            height: '18px', 
                            fontSize: '0.65rem',
                            color: getStatusColor(node.status),
                            borderColor: getStatusColor(node.status)
                          }}
                        />
                      </Box>
                    </Box>
                  </EventNode>
                  
                  {index < flowNodes.length - 1 && node.connections.length > 0 && (
                    <FlowConnection>
                      <ConnectionIcon 
                        fontSize="small" 
                        sx={{ color: theme.palette.text.secondary }}
                      />
                    </FlowConnection>
                  )}
                </React.Fragment>
              ))}
            </DesktopFlowRow>
          </Box>
        )}
      </FlowContainer>
    </GridTile>
  );
};

export default EventCascadeFlow;