import React, { useState, useEffect, useCallback } from 'react';
import { 
  Box, 
  List, 
  ListItem, 
  ListItemText, 
  Typography, 
  Chip, 
  Avatar, 
  Stack, 
  Badge,
  useTheme,
  useMediaQuery,
  Fade,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Person as PersonIcon,
  AutoStories as StoryIcon,
  Psychology as BrainIcon,
  Speed as ActivityIcon,
  Notifications as NotificationIcon
} from '@mui/icons-material';
import GridTile from '../layout/GridTile';

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

interface ActivityEvent {
  id: string;
  type: 'character' | 'story' | 'system' | 'interaction';
  title: string;
  description: string;
  timestamp: Date;
  characterName?: string;
  severity: 'low' | 'medium' | 'high';
}

interface RealTimeActivityProps {
  loading?: boolean;
  error?: boolean;
  density?: 'default' | 'condensed';
}

const RealTimeActivity: React.FC<RealTimeActivityProps> = ({ loading, error, density = 'default' }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const isCondensed = density === 'condensed' && !isMobile;
  const [activities, setActivities] = useState<ActivityEvent[]>([
    {
      id: '1',
      type: 'character',
      title: 'Character Action',
      description: 'Aria Shadowbane initiated a stealth sequence',
      timestamp: new Date(Date.now() - 30000),
      characterName: 'Aria Shadowbane',
      severity: 'medium',
    },
    {
      id: '2',
      type: 'story',
      title: 'Plot Development',
      description: 'New narrative thread: "The Ancient Prophecy" introduced',
      timestamp: new Date(Date.now() - 120000),
      severity: 'high',
    },
    {
      id: '3',
      type: 'system',
      title: 'AI Processing',
      description: 'Generated 3 dialogue responses for merchant encounter',
      timestamp: new Date(Date.now() - 180000),
      severity: 'low',
    },
    {
      id: '4',
      type: 'interaction',
      title: 'Character Interaction',
      description: 'Merchant Aldric engaged in dialogue with party',
      timestamp: new Date(Date.now() - 240000),
      characterName: 'Merchant Aldric',
      severity: 'medium',
    },
    {
      id: '5',
      type: 'system',
      title: 'Memory Update',
      description: 'Updated character relationship: Trust +2 (Aria → Aldric)',
      timestamp: new Date(Date.now() - 300000),
      severity: 'low',
    },
  ]);

  const [unreadCount, setUnreadCount] = useState(2);
  const [highlightedId, setHighlightedId] = useState<string | null>(null);

  const handleMarkAsRead = useCallback(() => {
    setUnreadCount(0);
  }, []);

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      const eventTypes: ActivityEvent['type'][] = ['character', 'story', 'system', 'interaction'];
      const severities: ActivityEvent['severity'][] = ['low', 'medium', 'high'];
      const characters = ['Aria Shadowbane', 'Merchant Aldric', 'Elder Thorne', 'Captain Vex'];
      
      const descriptions = {
        character: [
          'initiated a combat sequence',
          'cast a spell: Healing Light',
          'discovered a hidden passage',
          'leveled up to level 5',
        ],
        story: [
          'New quest: "The Lost Crown" available',
          'Plot twist revealed in current arc',
          'Chapter completed: "The Forest Path"',
          'New location unlocked: Crystal Caverns',
        ],
        system: [
          'Generated environmental description',
          'Processed emotion analysis for dialogue',
          'Updated world state: Weather changed',
          'AI model responded in 1.2s',
        ],
        interaction: [
          'engaged in complex dialogue',
          'formed alliance with party',
          'entered hostile state',
          'provided quest information',
        ],
      };

      if (Math.random() < 0.3) { // 30% chance to add new activity
        const type = eventTypes[Math.floor(Math.random() * eventTypes.length)];
        const severity = severities[Math.floor(Math.random() * severities.length)];
        const descList = descriptions[type];
        
        const newActivity: ActivityEvent = {
          id: Date.now().toString(),
          type,
          title: type.charAt(0).toUpperCase() + type.slice(1) + ' Event',
          description: type === 'character' || type === 'interaction' 
            ? `${characters[Math.floor(Math.random() * characters.length)]} ${descList[Math.floor(Math.random() * descList.length)]}`
            : descList[Math.floor(Math.random() * descList.length)],
          timestamp: new Date(),
          characterName: (type === 'character' || type === 'interaction') 
            ? characters[Math.floor(Math.random() * characters.length)]
            : undefined,
          severity,
        };

        setActivities(prev => [newActivity, ...prev.slice(0, 9)]); // Keep only 10 most recent
        setUnreadCount(prev => prev + 1);
        setHighlightedId(newActivity.id);
        setTimeout(() => setHighlightedId(null), 3000);
      }
    }, 5000); // Check every 5 seconds

    return () => clearInterval(interval);
  }, []);

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

  const getSeverityColor = (severity: ActivityEvent['severity']) => {
    switch (severity) {
      case 'high':
        return theme.palette.error.main;
      case 'medium':
        return theme.palette.warning.main;
      default:
        return theme.palette.success.main;
    }
  };

  const formatTimestamp = (timestamp: Date) => {
    const now = new Date();
    const diff = now.getTime() - timestamp.getTime();
    
    if (diff < 60000) {
      return 'Just now';
    } else if (diff < 3600000) {
      return `${Math.floor(diff / 60000)}m ago`;
    } else {
      return `${Math.floor(diff / 3600000)}h ago`;
    }
  };

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
      error={error}
      onMenuClick={handleMarkAsRead}
    >
      {isMobile ? (
        // Mobile: Enhanced activity list with better visibility
        <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          <ActivityHeader sx={{ flexShrink: 0 }}>
            <Stack direction="row" spacing={1} alignItems="center">
              <PulsingBadge
                animate={unreadCount > 0 ? {
                  scale: [1, 1.1, 1],
                } : {}}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
              >
                <Badge badgeContent={unreadCount} color="primary">
                  <NotificationIcon fontSize="small" sx={{ color: (theme) => theme.palette.primary.main }} />
                </Badge>
              </PulsingBadge>
              <Typography variant="body2" color="text.secondary" fontWeight={500}>
                Live Feed
              </Typography>
            </Stack>
            <Chip 
              label={`${activities.length} events`} 
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
            <AnimatePresence initial={false}>
              {activities.slice(0, 6).map((activity, index) => (
                <ActivityItem 
                  data-testid="activity-event"
                  key={activity.id} 
                  severity={activity.severity}
                  sx={{ 
                    py: 1, 
                    minHeight: '48px',
                    backgroundColor: highlightedId === activity.id ? 'rgba(99, 102, 241, 0.1)' : 'transparent',
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
                  <ListItemText
                    primary={
                      <Typography variant="body2" fontWeight={500} sx={{ lineHeight: 1.3, mb: 0.25, color: 'text.primary' }}>
                        {activity.description.length > 60 
                          ? `${activity.description.substring(0, 60)}...`
                          : activity.description
                        }
                      </Typography>
                    }
                    secondary={
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
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
                    }
                  />
                </ActivityItem>
              ))}
            </AnimatePresence>
          </ActivityList>
        </Box>
      ) : (
        // Desktop: Full or condensed activity list
        <Box sx={{ height: '100%' }} data-density={isCondensed ? 'condensed' : 'default'}>
          <ActivityHeader>
            <Stack direction="row" spacing={1} alignItems="center">
              <PulsingBadge
                animate={unreadCount > 0 ? {
                  scale: [1, 1.1, 1],
                } : {}}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
              >
                <Badge badgeContent={unreadCount} color="primary">
                  <NotificationIcon fontSize="small" sx={{ color: (theme) => theme.palette.primary.main }} />
                </Badge>
              </PulsingBadge>
              <Typography variant="body2" color="text.secondary" fontWeight={500}>
                Live Feed
              </Typography>
            </Stack>
            <Chip 
              label={`${activities.length} events`} 
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
            <AnimatePresence initial={false}>
              {activities.map((activity, index) => (
                <ActivityItem 
                  data-testid="activity-event"
                  key={activity.id}
                  severity={activity.severity}
                  sx={{
                    backgroundColor: highlightedId === activity.id ? 'rgba(99, 102, 241, 0.1)' : 'transparent',
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
                  <ListItemText
                    primary={
                      <Typography
                        variant="body2"
                        fontWeight={500}
                        sx={{ color: 'text.primary', lineHeight: 1.3 }}
                      >
                        {activity.description}
                      </Typography>
                    }
                    secondary={
                      <Stack
                        direction="row"
                        spacing={1}
                        alignItems="center"
                        sx={{ mt: 0.5, flexWrap: 'wrap' }}
                      >
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
                        <Typography variant="caption" color="text.secondary">
                          {formatTimestamp(activity.timestamp)}
                        </Typography>
                      </Stack>
                    }
                  />
                </ActivityItem>
              ))}
            </AnimatePresence>
          </ActivityList>
        </Box>
      )}
    </GridTile>
  );
};

export default RealTimeActivity;
