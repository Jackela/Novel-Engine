import React, { useState } from 'react';
import {
  Box,
  Typography,
  Chip,
  Stack,
  Avatar,
  useTheme,
  useMediaQuery,
  Fade,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { motion } from 'framer-motion';
import {
  TrendingFlat as ConnectionIcon,
  AccountTree as BranchIcon,
  CheckCircle as CompleteIcon,
  FiberManualRecord as ActiveIcon,
  RadioButtonUnchecked as PendingIcon,
} from '@mui/icons-material';
import GridTile from '@/components/layout/GridTile';

const FlowContainer = styled(Box)(({ theme }) => ({
  width: '100%',
  height: '100%',
  position: 'relative',
  display: 'flex',
  flexDirection: 'column',

  [theme.breakpoints.down('md')]: {
    padding: theme.spacing(0.5),
  },
}));

const FlowTrack = styled(Box)(({ theme }) => ({
  display: 'flex',
  flex: 1,

  // Desktop: horizontal flow
  [theme.breakpoints.up('md')]: {
    flexDirection: 'row',
    alignItems: 'center',
    overflowX: 'auto',
    overflowY: 'hidden',
    gap: theme.spacing(1),
    '&::-webkit-scrollbar': {
      height: '4px',
    },
    '&::-webkit-scrollbar-track': {
      backgroundColor: 'transparent',
    },
    '&::-webkit-scrollbar-thumb': {
      backgroundColor: theme.palette.divider,
      borderRadius: '2px',
    },
  },

  // Mobile: vertical flow
  [theme.breakpoints.down('md')]: {
    flexDirection: 'column',
    overflowY: 'auto',
    overflowX: 'hidden',
    gap: theme.spacing(0.5),
  },
}));

const EventNode = styled(motion(Box))<{ status: string }>(({ theme, status }) => ({
  display: 'flex',
  alignItems: 'center',
  padding: theme.spacing(1),
  borderRadius: theme.shape.borderRadius,
  backgroundColor: status === 'active' ? 'rgba(0, 240, 255, 0.15)' : theme.palette.background.paper,
  border: status === 'active'
    ? `2px solid ${theme.palette.primary.main}`
    : `1px solid ${theme.palette.divider}`,
  transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
  '&:hover': {
    backgroundColor: status === 'active' ? 'rgba(0, 240, 255, 0.2)' : 'var(--color-bg-tertiary)',
    borderColor: status === 'completed' ? theme.palette.success.main : theme.palette.primary.main,
    transform: 'translateY(-2px)',
    boxShadow: `0 4px 8px ${status === 'completed' ? 'rgba(16, 185, 129, 0.2)' :
        status === 'active' ? 'rgba(99, 102, 241, 0.3)' :
          'rgba(99, 102, 241, 0.1)'
      }`,
  },

  // Desktop: vertical layout
  [theme.breakpoints.up('md')]: {
    flexDirection: 'column',
    minWidth: '140px',
    maxWidth: '160px',
    flexShrink: 0,
  },

  // Mobile: horizontal layout
  [theme.breakpoints.down('md')]: {
    flexDirection: 'row',
    width: '100%',
  },
}));

const EventConnector = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  color: 'var(--color-text-tertiary)',

  // Desktop: horizontal connector
  [theme.breakpoints.up('md')]: {
    padding: theme.spacing(0, 0.5),
    flexShrink: 0,
  },

  // Mobile: vertical connector
  [theme.breakpoints.down('md')]: {
    width: '100%',
    height: '24px',
    transform: 'rotate(90deg)',
  },
}));

interface EventFlowNode {
  id: string;
  title: string;
  description: string;
  status: 'completed' | 'active' | 'pending';
  type: 'story' | 'character' | 'system' | 'branch';
  connections: number;
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
      connections: 1,
    },
    {
      id: '2',
      title: 'Merchant Meeting',
      description: 'Aldric provides crucial information',
      status: 'active',
      type: 'character',
      connections: 2,
    },
    {
      id: '3',
      title: 'Trust Building',
      description: 'Relationship development arc',
      status: 'active',
      type: 'character',
      connections: 1,
    },
    {
      id: '4',
      title: 'Crystal Caverns',
      description: 'New location discovered',
      status: 'pending',
      type: 'story',
      connections: 1,
    },
    {
      id: '5',
      title: 'Final Confrontation',
      description: 'Climax event pending',
      status: 'pending',
      type: 'story',
      connections: 0,
    },
  ]);

  const getEventIcon = (type: EventFlowNode['type'], status: EventFlowNode['status']) => {
    const iconProps = { fontSize: 'small' as const };

    if (status === 'completed') return <CompleteIcon {...iconProps} />;
    if (status === 'active') return <ActiveIcon {...iconProps} />;

    switch (type) {
      case 'branch':
        return <BranchIcon {...iconProps} />;
      default:
        return <PendingIcon {...iconProps} />;
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

  const totalEvents = flowNodes.length;
  const activeCount = flowNodes.filter(n => n.status === 'active').length;
  const completedCount = flowNodes.filter(n => n.status === 'completed').length;
  const totalDependencies = flowNodes.reduce((sum, n) => sum + n.connections, 0);

  return (
    <GridTile
      title="Event Cascade Flow"
      loading={loading}
      error={error}
      className="h-full"
    >
      <FlowContainer>
        {/* Stats Header */}
        <Stack
          direction="row"
          spacing={1}
          justifyContent="center"
          sx={{ mb: 1.5, flexShrink: 0, flexWrap: 'wrap' }}
        >
          <Chip
            label={`${totalEvents} Events`}
            size="small"
            sx={{
              backgroundColor: 'var(--color-bg-paper)',
              borderColor: 'var(--color-border-primary)',
              color: 'var(--color-text-secondary)',
              fontSize: '0.7rem',
              height: '22px',
            }}
          />
          <Chip
            label={`${totalDependencies} Links`}
            size="small"
            sx={{
              backgroundColor: 'var(--color-bg-paper)',
              borderColor: 'var(--color-border-primary)',
              color: 'var(--color-text-secondary)',
              fontSize: '0.7rem',
              height: '22px',
            }}
          />
          <Chip
            label={`${activeCount} Active`}
            size="small"
            sx={{
              backgroundColor: 'rgba(99, 102, 241, 0.2)',
              borderColor: 'var(--color-primary)',
              color: 'var(--color-primary)',
              fontSize: '0.7rem',
              height: '22px',
            }}
          />
          {!isMobile && (
            <Chip
              label={`${completedCount} Done`}
              size="small"
              sx={{
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                borderColor: 'var(--color-success)',
                color: 'var(--color-success)',
                fontSize: '0.7rem',
                height: '22px',
              }}
            />
          )}
        </Stack>

        {/* Event Flow */}
        <FlowTrack>
          {flowNodes.map((node, index) => (
            <React.Fragment key={node.id}>
              <Fade in timeout={300 + index * 100}>
                <EventNode
                  status={node.status}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.3, delay: index * 0.05 }}
                  whileHover={{ scale: 1.05 }}
                >
                  <Avatar
                    sx={{
                      bgcolor: 'transparent',
                      color: getStatusColor(node.status),
                      width: isMobile ? 32 : 36,
                      height: isMobile ? 32 : 36,
                      mr: isMobile ? 1.5 : 0,
                      mb: isMobile ? 0 : 0.5,
                    }}
                  >
                    {getEventIcon(node.type, node.status)}
                  </Avatar>

                  <Box sx={{ flex: 1, textAlign: isMobile ? 'left' : 'center' }}>
                    <Typography
                      variant={isMobile ? 'caption' : 'body2'}
                      fontWeight={600}
                      sx={{
                        color: 'var(--color-text-primary)',
                        lineHeight: 1.3,
                        mb: 0.25,
                      }}
                    >
                      {node.title}
                    </Typography>

                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{
                        display: 'block',
                        fontSize: '0.7rem',
                        lineHeight: 1.3,
                        mb: 0.5,
                      }}
                    >
                      {isMobile && node.description.length > 30
                        ? `${node.description.substring(0, 30)}...`
                        : node.description
                      }
                    </Typography>

                    <Stack
                      direction="row"
                      spacing={0.5}
                      alignItems="center"
                      justifyContent={isMobile ? 'flex-start' : 'center'}
                    >
                      <Chip
                        label={node.status}
                        size="small"
                        sx={{
                          height: '16px',
                          fontSize: '0.6rem',
                          backgroundColor: `${getStatusColor(node.status)}20`,
                          color: getStatusColor(node.status),
                          borderColor: getStatusColor(node.status),
                        }}
                      />
                      {!isMobile && node.connections > 0 && (
                        <Chip
                          label={`${node.connections} link${node.connections > 1 ? 's' : ''}`}
                          size="small"
                          sx={{
                            height: '16px',
                            fontSize: '0.6rem',
                            backgroundColor: 'var(--color-bg-paper)',
                            borderColor: 'var(--color-border-primary)',
                            color: 'var(--color-text-secondary)',
                          }}
                        />
                      )}
                    </Stack>
                  </Box>
                </EventNode>
              </Fade>

              {index < flowNodes.length - 1 && node.connections > 0 && (
                <EventConnector>
                  <ConnectionIcon fontSize="small" />
                </EventConnector>
              )}
            </React.Fragment>
          ))}
        </FlowTrack>
      </FlowContainer>
    </GridTile>
  );
};

export default EventCascadeFlow;
