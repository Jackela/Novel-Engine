import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  List,
  ListItem,
  Typography,
  Chip,
  Avatar,
  Stack,
  Badge,
  useTheme,
  useMediaQuery,
  Fade,
  Button,
  Alert,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Person as PersonIcon,
  AutoStories as StoryIcon,
  Psychology as BrainIcon,
  Speed as ActivityIcon,
  Notifications as NotificationIcon,
  Error as AlertCircleIcon,
} from '@mui/icons-material';
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
  borderLeft: `3px solid ${severity === 'high' ? theme.palette.error.main : severity === 'medium' ? theme.palette.warning.main : theme.palette.success.main}`,
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

const RealTimeActivity: React.FC<RealTimeActivityProps> = ({ loading: propLoading, error: propError, density = 'default' }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const isCondensed = density === 'condensed' && !isMobile;
  const [unreadCount, setUnreadCount] = useState(0);
  const [_highlightedId] = useState<string | null>(null); // Unused - reserved for future event highlighting feature

  // Use SSE hook for real-time events
  const { events, loading: hookLoading, error: hookError, connectionState } = useRealtimeEvents({ enabled: true });

  // Use hook state or prop state
  const loading = propLoading ?? hookLoading;
  const error = propError ?? hookError;

  const fallbackEvents = [
    {
      id: 'offline-telemetry',
      type: 'system' as const,
      title: 'Running in offline mode',
      description: 'Displaying cached activity until connectivity is restored.',
      timestamp: Date.now(),
      severity: 'low' as const,
    },
    {
      id: 'guest-dataset',
      type: 'character' as const,
      title: 'Guest workspace active',
      description: 'Using guest dataset to keep the dashboard interactive.',
      timestamp: Date.now(),
      severity: 'medium' as const,
    },
  ];

  const displayEvents =
    events.length > 0 || connectionState === 'connected'
      ? events
      : fallbackEvents;

  const handleMarkAsRead = useCallback(() => {
    setUnreadCount(0);
  }, []);

  // Update unread count when new events arrive
  useEffect(() => {
    if (connectionState === 'connected' && displayEvents.length > 0) {
      setUnreadCount(displayEvents.length);
    }
  }, [displayEvents.length, connectionState]);

  const getActivityIcon = (type: 'character' | 'story' | 'system' | 'interaction') => {
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

  const getSeverityColor = (severity: 'low' | 'medium' | 'high') => {
    switch (severity) {
      case 'high':
        return theme.palette.error.main;
      case 'medium':
        return theme.palette.warning.main;
      default:
        return theme.palette.success.main;
    }
  };

  const formatTimestamp = (timestamp: number | null | undefined) => {
    // Handle invalid timestamps
    if (!timestamp || typeof timestamp !== 'number' || isNaN(timestamp)) {
      return 'Recently';
    }

    // Normalize timestamp: detect if it's in seconds vs milliseconds
    // If timestamp is less than 1e11 (year ~1973 in ms), assume it's in seconds
    const normalizedTs = timestamp < 1e11 ? timestamp * 1000 : timestamp;

    const now = Date.now();
    const diff = now - normalizedTs;

    // Handle future timestamps or very old timestamps (likely invalid)
    if (diff < 0 || diff > 365 * 24 * 60 * 60 * 1000) {
      return 'Recently';
    }

    if (diff < 60000) {
      return 'Just now';
    } else if (diff < 3600000) {
      return `${Math.floor(diff / 60000)}m ago`;
    } else if (diff < 86400000) {
      return `${Math.floor(diff / 3600000)}h ago`;
    } else {
      return `${Math.floor(diff / 86400000)}d ago`;
    }
  };

  const badgeCount = Math.min(unreadCount, displayEvents.length);
  const eventCountLabel = displayEvents.length > 0 ? `${displayEvents.length} events` : 'No events';
  const isConnected = connectionState === 'connected';
  const connectionLabel = isConnected ? '● Live' : '○ Connecting';
  const connectionColor = isConnected ? theme.palette.success.main : theme.palette.text.disabled;

  // Error-first UI: Show error state when connection fails
  if (error) {
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
          <AlertCircleIcon
            sx={{
              fontSize: 48,
              color: theme.palette.error.main,
              mb: 2,
            }}
            aria-hidden="true"
          />
          <Typography
            variant="h6"
            component="div"
            sx={{ fontWeight: 600, color: theme.palette.error.main, mb: 1 }}
          >
            Unable to load live events
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3, maxWidth: '400px' }}>
            {hookError?.message || 'Failed to connect to event stream. Please check your connection and try again.'}
          </Typography>
          <Button
            variant="contained"
            color="error"
            onClick={() => window.location.reload()}
            sx={{ textTransform: 'none' }}
          >
            Retry Connection
          </Button>
        </Box>
      </GridTile>
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
      {isMobile ? (
        // Mobile: Enhanced activity list with better visibility
        <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          <ActivityHeader sx={{ flexShrink: 0 }}>
            <Stack direction="row" spacing={1} alignItems="center">
              <PulsingBadge
                animate={badgeCount > 0 ? {
                  scale: [1, 1.1, 1],
                } : {}}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
              >
                <Badge badgeContent={badgeCount} color="primary">
                  <NotificationIcon fontSize="small" sx={{ color: (theme) => theme.palette.primary.main }} />
                </Badge>
              </PulsingBadge>
              <Typography
                variant="body2"
                fontWeight={500}
                component="div"
                sx={{ color: connectionColor }}
              >
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

          <ActivityList sx={{ flex: 1, minHeight: '160px' }}>
            {displayEvents.length === 0 && connectionState === 'connected' ? (
              <Typography variant="body2" color="text.secondary" sx={{ p: 2, textAlign: 'center' }}>
                No recent events
              </Typography>
            ) : (
              <AnimatePresence initial={false}>
                {displayEvents.slice(0, 6).map((activity, index) => (
                  <ActivityItem
                    data-testid="activity-event"
                    key={activity.id}
                    severity={activity.severity}
                    sx={{
                      py: 1,
                      minHeight: '48px',
                      backgroundColor: _highlightedId === activity.id ? 'rgba(99, 102, 241, 0.1)' : 'transparent',
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
                        color: getSeverityColor(activity.severity),
                        width: 28,
                        height: 28,
                        mr: 1.5,
                      }}
                    >
                      {getActivityIcon(activity.type)}
                    </Avatar>
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Typography
                        variant="body2"
                        component="div"
                        fontWeight={500}
                        sx={{ lineHeight: 1.3, mb: 0.25, color: 'text.primary' }}
                      >
                        {activity.description.length > 60
                          ? `${activity.description.substring(0, 60)}...`
                          : activity.description}
                      </Typography>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Typography variant="caption" component="span" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                          {formatTimestamp(activity.timestamp)}
                        </Typography>
                        {activity.characterName && (
                          <Box data-testid="character-activity" sx={{ display: 'inline-flex' }}>
                            <Chip
                              label={activity.characterName}
                              size="small"
                              sx={{
                                height: '18px',
                                fontSize: '0.6rem',
                                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                                borderColor: (theme) => theme.palette.primary.main,
                                color: (theme) => theme.palette.text.secondary,
                              }}
                            />
                          </Box>
                        )}
                      </Stack>
                    </Box>
                  </ActivityItem>
                ))}
              </AnimatePresence>
            )}
          </ActivityList>
        </Box>
      ) : (
        // Desktop: Full or condensed activity list
        <Box sx={{ height: '100%' }} data-density={isCondensed ? 'condensed' : 'default'}>
          <ActivityHeader>
            <Stack direction="row" spacing={1} alignItems="center">
              <PulsingBadge
                animate={badgeCount > 0 ? {
                  scale: [1, 1.1, 1],
                } : {}}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
              >
                <Badge badgeContent={badgeCount} color="primary">
                  <NotificationIcon fontSize="small" sx={{ color: (theme) => theme.palette.primary.main }} />
                </Badge>
              </PulsingBadge>
              <Typography
                variant="body2"
                fontWeight={500}
                component="div"
                sx={{ color: connectionColor }}
              >
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

          <ActivityList
            sx={
              isCondensed
                ? {
                  display: 'grid',
                  gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
                  columnGap: 1.5,
                  rowGap: 0.5,
                }
                : undefined
            }
            data-density={isCondensed ? 'condensed' : 'default'}
          >
            {displayEvents.length === 0 && connectionState === 'connected' ? (
              <Typography variant="body2" color="text.secondary" sx={{ p: 2, textAlign: 'center' }}>
                No recent events
              </Typography>
            ) : (
              <AnimatePresence initial={false}>
                {displayEvents.map((activity, index) => (
                  <ActivityItem
                    data-testid="activity-event"
                    key={activity.id}
                    severity={activity.severity}
                    sx={{
                      backgroundColor: _highlightedId === activity.id ? 'rgba(99, 102, 241, 0.1)' : 'transparent',
                      flexDirection: isCondensed ? 'column' : 'row',
                      gap: isCondensed ? 0.5 : 0,
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
                        color: getSeverityColor(activity.severity),
                        width: 32,
                        height: 32,
                        mr: isCondensed ? 0 : 2,
                      }}
                    >
                      {getActivityIcon(activity.type)}
                    </Avatar>
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Typography
                        variant="body2"
                        component="div"
                        fontWeight={500}
                        sx={{ color: 'text.primary', lineHeight: 1.3 }}
                      >
                        {activity.description}
                      </Typography>
                      <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 0.5, flexWrap: 'wrap' }}>
                        {activity.characterName && (
                          <Box data-testid="character-activity" sx={{ display: 'inline-flex' }}>
                            <Chip
                              label={activity.characterName}
                              size="small"
                              sx={{
                                height: '16px',
                                fontSize: '0.65rem',
                                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                                borderColor: (theme) => theme.palette.primary.main,
                                color: (theme) => theme.palette.text.secondary,
                              }}
                            />
                          </Box>
                        )}
                        <Typography variant="caption" component="span" color="text.secondary">
                          {formatTimestamp(activity.timestamp)}
                        </Typography>
                      </Stack>
                    </Box>
                  </ActivityItem>
                ))}
              </AnimatePresence>
            )}
          </ActivityList>
        </Box>
      )}
    </GridTile>
  );
};

export default RealTimeActivity;
