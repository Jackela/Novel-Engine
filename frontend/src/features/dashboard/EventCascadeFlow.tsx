import React from 'react';
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
import { styled, alpha } from '@mui/material/styles';
import { motion } from 'framer-motion';
import {
  PlayArrow as EventIcon,
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
  backgroundColor: status === 'active' ? alpha(theme.palette.primary.main, 0.12) : theme.palette.background.paper,
  border:
    status === 'active'
      ? `2px solid ${theme.palette.primary.main}`
      : `1px solid ${theme.palette.divider}`,
  transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
  '&:hover': {
    backgroundColor: status === 'active' ? alpha(theme.palette.primary.main, 0.16) : 'var(--color-bg-tertiary)',
    borderColor: status === 'completed' ? theme.palette.success.main : theme.palette.primary.main,
    transform: 'translateY(-2px)',
    boxShadow: `0 4px 8px ${status === 'completed'
      ? alpha(theme.palette.success.main, 0.2)
      : alpha(theme.palette.primary.main, status === 'active' ? 0.3 : 0.1)}`,
  },
  [theme.breakpoints.up('md')]: {
    flexDirection: 'column',
    minWidth: '140px',
    maxWidth: '160px',
    flexShrink: 0,
  },
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
  [theme.breakpoints.up('md')]: {
    padding: theme.spacing(0, 0.5),
    flexShrink: 0,
  },
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

const EVENT_FLOW_NODES: EventFlowNode[] = [
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
];

const getEventIcon = (type: EventFlowNode['type'], status: EventFlowNode['status']) => {
  const iconProps = { fontSize: 'small' as const };

  if (status === 'completed') return <CompleteIcon {...iconProps} />;
  if (status === 'active') return <ActiveIcon {...iconProps} />;

  if (type === 'branch') {
    return <BranchIcon {...iconProps} />;
  }

  return <PendingIcon {...iconProps} />;
};

const getStatusColor = (status: EventFlowNode['status'], theme: ReturnType<typeof useTheme>) => {
  if (status === 'completed') return theme.palette.success.main;
  if (status === 'active') return theme.palette.primary.main;
  return theme.palette.text.secondary;
};

const getTruncatedDescription = (description: string, isMobile: boolean) => {
  if (!isMobile) return description;
  if (description.length <= 30) return description;
  return `${description.substring(0, 30)}...`;
};

const EventFlowSummary: React.FC<{
  totalEvents: number;
  totalDependencies: number;
  activeCount: number;
  completedCount: number;
  isMobile: boolean;
}> = ({ totalEvents, totalDependencies, activeCount, completedCount, isMobile }) => (
  <Stack direction="row" spacing={1} justifyContent="center" sx={{ mb: 1.5, flexShrink: 0, flexWrap: 'wrap' }}>
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
        backgroundColor: (theme) => alpha(theme.palette.primary.main, 0.12),
        borderColor: (theme) => theme.palette.primary.main,
        color: (theme) => theme.palette.primary.main,
        fontSize: '0.7rem',
        height: '22px',
      }}
    />
    {!isMobile && (
      <Chip
        label={`${completedCount} Done`}
        size="small"
        sx={{
          backgroundColor: (theme) => alpha(theme.palette.success.main, 0.12),
          borderColor: (theme) => theme.palette.success.main,
          color: (theme) => theme.palette.success.main,
          fontSize: '0.7rem',
          height: '22px',
        }}
      />
    )}
  </Stack>
);

const EventFlowNodeCard: React.FC<{
  node: EventFlowNode;
  isMobile: boolean;
  theme: ReturnType<typeof useTheme>;
  animationDelay: number;
}> = ({ node, isMobile, theme, animationDelay }) => (
  <Fade in timeout={300 + animationDelay}>
    <EventNode
      status={node.status}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3, delay: animationDelay * 0.05 }}
      whileHover={{ scale: 1.05 }}
    >
      <Avatar
        sx={{
          bgcolor: 'transparent',
          color: getStatusColor(node.status, theme),
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
          sx={{ color: 'var(--color-text-primary)', lineHeight: 1.3, mb: 0.25 }}
        >
          {node.title}
        </Typography>

        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ display: 'block', fontSize: '0.7rem', lineHeight: 1.3, mb: 0.5 }}
        >
          {getTruncatedDescription(node.description, isMobile)}
        </Typography>

        <Stack direction="row" spacing={0.5} alignItems="center" justifyContent={isMobile ? 'flex-start' : 'center'}>
          <Chip
            label={node.status}
            size="small"
            sx={{
              height: '16px',
              fontSize: '0.6rem',
              backgroundColor: `${getStatusColor(node.status, theme)}20`,
              color: getStatusColor(node.status, theme),
              borderColor: getStatusColor(node.status, theme),
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
);

const EventFlowList: React.FC<{
  nodes: EventFlowNode[];
  isMobile: boolean;
  theme: ReturnType<typeof useTheme>;
}> = ({ nodes, isMobile, theme }) => (
  <FlowTrack>
    {nodes.map((node, index) => (
      <React.Fragment key={node.id}>
        <EventFlowNodeCard
          node={node}
          isMobile={isMobile}
          theme={theme}
          animationDelay={index}
        />
        {index < nodes.length - 1 && node.connections > 0 && (
          <EventConnector>
            <ConnectionIcon fontSize="small" />
          </EventConnector>
        )}
      </React.Fragment>
    ))}
  </FlowTrack>
);

const EventCascadeFlow: React.FC<EventCascadeFlowProps> = ({ loading, error }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const totalEvents = EVENT_FLOW_NODES.length;
  const activeCount = EVENT_FLOW_NODES.filter((node) => node.status === 'active').length;
  const completedCount = EVENT_FLOW_NODES.filter((node) => node.status === 'completed').length;
  const totalDependencies = EVENT_FLOW_NODES.reduce((sum, node) => sum + node.connections, 0);

  return (
    <GridTile title="Event Cascade Flow" loading={loading} error={error} className="h-full">
      <FlowContainer>
        <EventFlowSummary
          totalEvents={totalEvents}
          totalDependencies={totalDependencies}
          activeCount={activeCount}
          completedCount={completedCount}
          isMobile={isMobile}
        />
        <EventFlowList nodes={EVENT_FLOW_NODES} isMobile={isMobile} theme={theme} />
      </FlowContainer>
    </GridTile>
  );
};

export default EventCascadeFlow;
