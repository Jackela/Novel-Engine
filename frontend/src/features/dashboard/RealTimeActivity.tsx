import React, { useState, useEffect, useCallback, useMemo } from 'react';
import Box from '@mui/material/Box';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Avatar from '@mui/material/Avatar';
import Stack from '@mui/material/Stack';
import Badge from '@mui/material/Badge';
import Fade from '@mui/material/Fade';
import Button from '@mui/material/Button';
import Alert from '@mui/material/Alert';
import useMediaQuery from '@mui/material/useMediaQuery';
import { styled, useTheme, alpha } from '@mui/material/styles';
import { motion, AnimatePresence } from 'framer-motion';
import PersonIcon from '@mui/icons-material/Person';
import StoryIcon from '@mui/icons-material/AutoStories';
import BrainIcon from '@mui/icons-material/Psychology';
import ActivityIcon from '@mui/icons-material/Speed';
import NotificationIcon from '@mui/icons-material/Notifications';
import AlertCircleIcon from '@mui/icons-material/Error';
import GridTile from '@/components/layout/GridTile';
import { useRealtimeEvents } from '../../hooks/useRealtimeEvents';

const ActivityList = styled(List)(({ theme }) => ({
  padding: 0,
  maxHeight: 'calc(100% - 40px)',
  overflowY: 'auto',
  '&::-webkit-scrollbar': {
    width: '4px',
  },
  '&::-webkit-scrollbar-track': {
    backgroundColor: 'transparent',
  },
  '&::-webkit-scrollbar-thumb': {
    backgroundColor: theme.palette.divider,
    borderRadius: '2px',
  },
}));

const ActivityItem = styled(motion(ListItem))<{ severity?: string }>(({ theme, severity }) => ({
  padding: theme.spacing(1, 0),
  borderBottom: `1px solid ${theme.palette.divider}`,
  borderLeft: `3px solid ${
    severity === 'high'
      ? theme.palette.error.main
      : severity === 'medium'
        ? theme.palette.warning.main
        : theme.palette.success.main
  }`,
  paddingLeft: theme.spacing(1),
  borderRadius: theme.shape.borderRadius / 2,
  marginBottom: theme.spacing(0.5),
  background: 'transparent',
  transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
  '&:hover': {
    background: 'var(--color-bg-tertiary)',
    borderLeftWidth: '4px',
    transform: 'translateX(4px)',
  },
  '&:last-child': {
    borderBottom: `1px solid ${theme.palette.divider}`,
  },
}));

const ActivityHeader = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  marginBottom: theme.spacing(1.5),
  paddingBottom: theme.spacing(1),
  borderBottom: `1px solid ${theme.palette.divider}`,
}));

const PulsingBadge = styled(motion.div)({
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
});

interface RealTimeActivityProps {
  loading?: boolean;
  error?: boolean;
  density?: 'default' | 'condensed';
}

interface ActivityEvent {
  id: string;
  type: 'character' | 'story' | 'system' | 'interaction';
  title?: string;
  description: string;
  timestamp?: number | null;
  severity: 'low' | 'medium' | 'high';
  characterName?: string;
}

const FALLBACK_EVENTS: ActivityEvent[] = [
  {
    id: 'offline-telemetry',
    type: 'system',
    title: 'Running in offline mode',
    description: 'Displaying cached activity until connectivity is restored.',
    timestamp: Date.now(),
    severity: 'low',
  },
  {
    id: 'guest-dataset',
    type: 'character',
    title: 'Guest workspace active',
    description: 'Using guest dataset to keep the dashboard interactive.',
    timestamp: Date.now(),
    severity: 'medium',
  },
];

const getActivityIcon = (type: ActivityEvent['type']) => {
  const iconProps = { fontSize: 'small' as const };
  switch (type) {
    case 'character':
      return <PersonIcon {...iconProps} />;
    case 'story':
      return <StoryIcon {...iconProps} />;
    case 'interaction':
      return <BrainIcon {...iconProps} />;
    default:
      return <ActivityIcon {...iconProps} />;
  }
};

const getSeverityColor = (severity: ActivityEvent['severity'], theme: ReturnType<typeof useTheme>) => {
  if (severity === 'high') return theme.palette.error.main;
  if (severity === 'medium') return theme.palette.warning.main;
  return theme.palette.success.main;
};

const formatTimestamp = (timestamp: number | null | undefined) => {
  if (!timestamp || typeof timestamp !== 'number' || isNaN(timestamp)) {
    return 'Recently';
  }

  const normalizedTs = timestamp < 1e11 ? timestamp * 1000 : timestamp;
  const now = Date.now();
  const diff = now - normalizedTs;

  if (diff < 0 || diff > 365 * 24 * 60 * 60 * 1000) {
    return 'Recently';
  }

  if (diff < 60000) {
    return 'Just now';
  }
  if (diff < 3600000) {
    return `${Math.floor(diff / 60000)}m ago`;
  }
  if (diff < 86400000) {
    return `${Math.floor(diff / 3600000)}h ago`;
  }
  return `${Math.floor(diff / 86400000)}d ago`;
};

const useActivityEvents = (propLoading?: boolean, propError?: boolean) => {
  const { events, loading: hookLoading, error: hookError, connectionState } = useRealtimeEvents({
    enabled: true,
  });

  const loading = propLoading ?? hookLoading;
  const error = propError ?? hookError;
  const displayEvents =
    events.length > 0 || connectionState === 'connected' ? events : FALLBACK_EVENTS;

  return { loading, error, connectionState, displayEvents };
};

const useUnreadCounter = (connectionState: string, displayEvents: ActivityEvent[]) => {
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    if (connectionState === 'connected' && displayEvents.length > 0) {
      setUnreadCount(displayEvents.length);
    }
  }, [displayEvents.length, connectionState]);

  const handleMarkAsRead = useCallback(() => {
    setUnreadCount(0);
  }, []);

  return { unreadCount, handleMarkAsRead };
};

const ActivityErrorState: React.FC<{ errorMessage?: string; isCondensed: boolean }> = ({
  errorMessage,
  isCondensed,
}) => {
  const theme = useTheme();

  return (
    <GridTile
      title="Real-time Activity"
      data-testid="real-time-activity"
      position={{
        desktop: { column: 'span 2', height: isCondensed ? '240px' : '280px' },
        tablet: { column: 'span 2', height: '260px' },
        mobile: { column: 'span 1', height: '220px' },
      }}
      loading={false}
      error={false}
    >
      <Box
        role="alert"
        sx={{
          p: 2,
          borderRadius: 1,
          border: `1px solid ${theme.palette.error.light}`,
          backgroundColor: theme.palette.error.main + '10',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          textAlign: 'center',
        }}
      >
        <AlertCircleIcon sx={{ fontSize: 48, color: theme.palette.error.main, mb: 2 }} />
        <Typography variant="h6" component="div" sx={{ fontWeight: 600, color: theme.palette.error.main, mb: 1 }}>
          Unable to load live events
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3, maxWidth: '400px' }}>
          {errorMessage || 'Failed to connect to event stream. Please check your connection and try again.'}
        </Typography>
        <Button variant="contained" color="error" onClick={() => window.location.reload()} sx={{ textTransform: 'none' }}>
          Retry Connection
        </Button>
      </Box>
    </GridTile>
  );
};

const ActivityHeaderView: React.FC<{
  badgeCount: number;
  connectionLabel: string;
  connectionColor: string;
  eventCountLabel: string;
}> = ({ badgeCount, connectionLabel, connectionColor, eventCountLabel }) => (
  <ActivityHeader>
    <Stack direction="row" spacing={1} alignItems="center">
      <PulsingBadge
        animate={badgeCount > 0 ? { scale: [1, 1.1, 1] } : {}}
        transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
      >
        <Badge badgeContent={badgeCount} color="primary">
          <NotificationIcon fontSize="small" sx={{ color: (theme) => theme.palette.primary.main }} />
        </Badge>
      </PulsingBadge>
      <Typography variant="body2" fontWeight={500} component="div" sx={{ color: connectionColor }}>
        {connectionLabel}
      </Typography>
    </Stack>
    <Chip
      label={eventCountLabel}
      size="small"
      sx={{
        backgroundColor: 'background.paper',
        borderColor: 'divider',
        color: (theme) => theme.palette.text.secondary,
        fontWeight: 500,
      }}
    />
  </ActivityHeader>
);

const ActivityEmptyState: React.FC<{ isMobile: boolean }> = ({ isMobile }) => (
  <Typography variant="body2" color="text.secondary" sx={{ p: 2, textAlign: 'center' }}>
    {isMobile ? 'No recent events' : 'No recent events'}
  </Typography>
);

const ActivityCharacterChip: React.FC<{ name: string }> = ({ name }) => (
  <Box data-testid="character-activity" sx={{ display: 'inline-flex' }}>
    <Chip
      label={name}
      size="small"
      sx={{
        height: '18px',
        fontSize: '0.6rem',
        backgroundColor: (theme) => alpha(theme.palette.primary.main, 0.1),
        borderColor: (theme) => theme.palette.primary.main,
        color: (theme) => theme.palette.text.secondary,
      }}
    />
  </Box>
);

const ActivityItemContent: React.FC<{
  activity: ActivityEvent;
  isCondensed: boolean;
  isMobile: boolean;
}> = ({ activity, isCondensed, isMobile }) => (
  <Box sx={{ flex: 1, minWidth: 0 }}>
    <Typography variant="body2" component="div" fontWeight={500} sx={{ color: 'text.primary', lineHeight: 1.3 }}>
      {isMobile && activity.description.length > 60
        ? `${activity.description.substring(0, 60)}...`
        : activity.description}
    </Typography>
    <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 0.5, flexWrap: 'wrap' }}>
      {activity.characterName && <ActivityCharacterChip name={activity.characterName} />}
      <Typography variant="caption" component="span" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
        {formatTimestamp(activity.timestamp)}
      </Typography>
    </Stack>
  </Box>
);

const ActivityItemView: React.FC<{
  activity: ActivityEvent;
  index: number;
  isCondensed: boolean;
  isMobile: boolean;
  theme: ReturnType<typeof useTheme>;
}> = ({ activity, index, isCondensed, isMobile, theme }) => (
  <ActivityItem
    data-testid="activity-event"
    key={activity.id}
    severity={activity.severity}
    sx={{
      backgroundColor: 'transparent',
      flexDirection: isCondensed ? 'column' : 'row',
      gap: isCondensed ? 0.5 : 0,
      py: isMobile ? 1 : undefined,
      minHeight: isMobile ? '48px' : undefined,
    }}
    data-activity-type={activity.type}
    data-severity={activity.severity}
    data-activity-id={activity.id}
    data-character-activity={activity.characterName ? 'true' : 'false'}
    initial={{ opacity: 0, x: -20 }}
    animate={{ opacity: 1, x: 0 }}
    exit={{ opacity: 0, x: 20 }}
    transition={{ duration: 0.3, delay: index * 0.05 }}
  >
    <Avatar
      sx={{
        bgcolor: 'transparent',
        color: getSeverityColor(activity.severity, theme),
        width: isMobile ? 28 : 32,
        height: isMobile ? 28 : 32,
        mr: isCondensed ? 0 : 2,
      }}
    >
      {getActivityIcon(activity.type)}
    </Avatar>
    <ActivityItemContent activity={activity} isCondensed={isCondensed} isMobile={isMobile} />
  </ActivityItem>
);

const ActivityListView: React.FC<{
  events: ActivityEvent[];
  isCondensed: boolean;
  isMobile: boolean;
  isConnected: boolean;
}> = ({ events, isCondensed, isMobile, isConnected }) => {
  const theme = useTheme();
  const visibleEvents = useMemo(() => (isMobile ? events.slice(0, 6) : events), [events, isMobile]);

  if (visibleEvents.length === 0 && isConnected) {
    return <ActivityEmptyState isMobile={isMobile} />;
  }

  return (
    <AnimatePresence initial={false}>
      {visibleEvents.map((activity, index) => (
        <ActivityItemView
          activity={activity}
          index={index}
          isCondensed={isCondensed}
          isMobile={isMobile}
          theme={theme}
          key={activity.id}
        />
      ))}
    </AnimatePresence>
  );
};

const ActivityPanel: React.FC<{
  isMobile: boolean;
  isCondensed: boolean;
  badgeCount: number;
  connectionLabel: string;
  connectionColor: string;
  eventCountLabel: string;
  displayEvents: ActivityEvent[];
  isConnected: boolean;
}> = ({
  isMobile,
  isCondensed,
  badgeCount,
  connectionLabel,
  connectionColor,
  eventCountLabel,
  displayEvents,
  isConnected,
}) => (
  <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }} data-density={isCondensed ? 'condensed' : 'default'}>
    <ActivityHeaderView
      badgeCount={badgeCount}
      connectionLabel={connectionLabel}
      connectionColor={connectionColor}
      eventCountLabel={eventCountLabel}
    />
    <ActivityList
      sx={
        isCondensed
          ? {
              display: 'grid',
              gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
              columnGap: 1.5,
              rowGap: 0.5,
            }
          : { flex: 1, minHeight: isMobile ? '160px' : undefined }
      }
      data-density={isCondensed ? 'condensed' : 'default'}
    >
      <ActivityListView
        events={displayEvents}
        isCondensed={isCondensed}
        isMobile={isMobile}
        isConnected={isConnected}
      />
    </ActivityList>
  </Box>
);

const RealTimeActivity: React.FC<RealTimeActivityProps> = ({
  loading: propLoading,
  error: propError,
  density = 'default',
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const isCondensed = density === 'condensed' && !isMobile;

  const { loading, error, connectionState, displayEvents } = useActivityEvents(propLoading, propError);
  const { unreadCount, handleMarkAsRead } = useUnreadCounter(connectionState, displayEvents);

  const badgeCount = Math.min(unreadCount, displayEvents.length);
  const eventCountLabel = displayEvents.length > 0 ? `${displayEvents.length} events` : 'No events';
  const isConnected = connectionState === 'connected';
  const connectionLabel = isConnected ? '● Live' : '○ Connecting';
  const connectionColor = isConnected ? theme.palette.success.main : theme.palette.text.disabled;

  if (error) {
    return (
      <ActivityErrorState
        errorMessage={(error as Error | undefined)?.message}
        isCondensed={isCondensed}
      />
    );
  }

  return (
    <GridTile
      title="Real-time Activity"
      data-testid="real-time-activity"
      position={{
        desktop: { column: 'span 2', height: isCondensed ? '240px' : '280px' },
        tablet: { column: 'span 2', height: '260px' },
        mobile: { column: 'span 1', height: '220px' },
      }}
      loading={loading}
      error={false}
      onMenuClick={handleMarkAsRead}
    >
      <ActivityPanel
        isMobile={isMobile}
        isCondensed={isCondensed}
        badgeCount={badgeCount}
        connectionLabel={connectionLabel}
        connectionColor={connectionColor}
        eventCountLabel={eventCountLabel}
        displayEvents={displayEvents}
        isConnected={isConnected}
      />
    </GridTile>
  );
};

export default RealTimeActivity;
