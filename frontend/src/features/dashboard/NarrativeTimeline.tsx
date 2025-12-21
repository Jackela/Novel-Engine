import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Typography,
  Chip,
  Stack,
  LinearProgress,
  Avatar,
  useTheme,
  useMediaQuery,
  Fade,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { motion } from 'framer-motion';
import {
  CheckCircle as CompletedIcon,
  RadioButtonUnchecked as PendingIcon,
  PlayCircle as ActiveIcon,
  MenuBook as ChapterIcon,
  AutoStories as StoryIcon,
  TrendingFlat as ConnectionIcon,
} from '@mui/icons-material';
import GridTile from '@/components/layout/GridTile';

const TimelineContainer = styled(Box)(({ theme }) => ({
  width: '100%',
  height: '100%',
  position: 'relative',
  display: 'flex',
  flexDirection: 'column',

  [theme.breakpoints.down('md')]: {
    padding: theme.spacing(0.5),
  },
}));

const ProgressHeader = styled(Box)(({ theme }) => ({
  flexShrink: 0,
  marginBottom: theme.spacing(1.5),
  paddingBottom: theme.spacing(1),
  borderBottom: (theme) => `1px solid ${theme.palette.divider}`,
}));

const TimelineTrack = styled(Box)(({ theme }) => ({
  flex: 1,
  display: 'flex',

  // Desktop: horizontal track
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

  // Mobile: vertical track
  [theme.breakpoints.down('md')]: {
    flexDirection: 'column',
    overflowY: 'auto',
    overflowX: 'hidden',
    gap: theme.spacing(0.5),
  },
}));

const TimelineNode = styled(motion(Box))<{ status: string }>(({ theme, status }) => ({
  display: 'flex',
  alignItems: 'center',
  padding: theme.spacing(1),
  borderRadius: theme.shape.borderRadius,
  backgroundColor: status === 'current' ? 'rgba(0, 240, 255, 0.15)' : theme.palette.background.paper,
  border: status === 'current'
    ? `2px solid ${theme.palette.primary.main}`
    : `1px solid ${theme.palette.divider}`,
  transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
  '&:hover': {
    backgroundColor: status === 'current' ? 'rgba(0, 240, 255, 0.2)' : 'var(--color-bg-tertiary)',
    borderColor: status === 'completed' ? theme.palette.success.main : theme.palette.primary.main,
    transform: 'scale(1.02)',
  },
  '&:focus-visible': {
    outline: `2px solid ${theme.palette.info.main}`,
    outlineOffset: 2,
  },
  '&:focus:not(:focus-visible)': {
    outline: 'none',
  },

  // Desktop: vertical layout
  [theme.breakpoints.up('md')]: {
    flexDirection: 'column',
    minWidth: '120px',
    maxWidth: '140px',
    flexShrink: 0,
  },

  // Mobile: horizontal layout
  [theme.breakpoints.down('md')]: {
    flexDirection: 'row',
    width: '100%',
  },
}));

const TimelineConnector = styled(Box)(({ theme }) => ({
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
    height: '20px',
    transform: 'rotate(90deg)',
  },
}));

interface TimelineEvent {
  id: string;
  title: string;
  description: string;
  turn: number;
  status: 'completed' | 'current' | 'upcoming';
  type: 'chapter' | 'plot' | 'character' | 'climax';
}

interface NarrativeTimelineProps {
  loading?: boolean;
  error?: boolean;
}

const NarrativeTimeline: React.FC<NarrativeTimelineProps> = ({ loading, error }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const [timelineEvents] = useState<TimelineEvent[]>([
    {
      id: '1',
      title: 'Prologue',
      description: 'Journey begins',
      turn: 1,
      status: 'completed',
      type: 'chapter',
    },
    {
      id: '2',
      title: 'Ancient Prophecy',
      description: 'Discovery phase',
      turn: 15,
      status: 'completed',
      type: 'plot',
    },
    {
      id: '3',
      title: 'Merchant Alliance',
      description: 'Aldric partnership',
      turn: 47,
      status: 'current',
      type: 'character',
    },
    {
      id: '4',
      title: 'Crystal Caverns',
      description: 'New territory',
      turn: 75,
      status: 'upcoming',
      type: 'chapter',
    },
    {
      id: '5',
      title: 'Final Confrontation',
      description: 'Climax approach',
      turn: 120,
      status: 'upcoming',
      type: 'climax',
    },
  ]);

  const currentTurn = 47;
  const maxTurn = 150;
  const progressPercentage = (currentTurn / maxTurn) * 100;
  const currentIndex = timelineEvents.findIndex((event) => event.status === 'current');
  const [focusIndex, setFocusIndex] = useState(currentIndex >= 0 ? currentIndex : 0);
  const nodeRefs = useRef<Array<HTMLDivElement | null>>([]);

  useEffect(() => {
    const node = nodeRefs.current[focusIndex];
    if (node && document.activeElement !== node) {
      node.focus();
    }
  }, [focusIndex]);

  const handleNodeKeyDown = useCallback(
    (event: React.KeyboardEvent, index: number) => {
      if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
        event.preventDefault();
        setFocusIndex((prev) => (prev + 1) % timelineEvents.length);
      }
      if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
        event.preventDefault();
        setFocusIndex((prev) => (prev - 1 + timelineEvents.length) % timelineEvents.length);
      }
      if (event.key === 'Home') {
        event.preventDefault();
        setFocusIndex(0);
      }
      if (event.key === 'End') {
        event.preventDefault();
        setFocusIndex(timelineEvents.length - 1);
      }
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        setFocusIndex(index);
      }
    },
    [timelineEvents.length]
  );

  const getStatusIcon = (status: TimelineEvent['status']) => {
    const iconProps = { fontSize: 'small' as const };
    switch (status) {
      case 'completed':
        return <CompletedIcon {...iconProps} />;
      case 'current':
        return <ActiveIcon {...iconProps} />;
      default:
        return <PendingIcon {...iconProps} />;
    }
  };

  const getStatusColor = (status: TimelineEvent['status']) => {
    switch (status) {
      case 'completed':
        return theme.palette.success.main;
      case 'current':
        return theme.palette.primary.main;
      default:
        return theme.palette.text.secondary;
    }
  };

  const getTypeIcon = (type: TimelineEvent['type']) => {
    switch (type) {
      case 'chapter':
        return <ChapterIcon sx={{ fontSize: '14px' }} />;
      case 'plot':
      case 'character':
      case 'climax':
        return <StoryIcon sx={{ fontSize: '14px' }} />;
      default:
        return undefined;
    }
  };

  return (
    <GridTile
      title="Narrative Arc Timeline"
      data-testid="narrative-timeline"
      data-role="narrative-timeline"
      position={{
        desktop: { column: '1 / 13', height: '200px' },
        tablet: { column: '1 / 9', height: '180px' },
        mobile: { height: '160px' },
      }}
      loading={loading}
      error={error}
    >
      <TimelineContainer>
        {/* Progress Header */}
        <ProgressHeader>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 0.5 }}>
            <Typography variant="caption" color="text.secondary" fontWeight={500} component="div">
              Turn {currentTurn} of {maxTurn}
            </Typography>
            <Typography
              variant="caption"
              sx={{ color: (theme) => theme.palette.primary.light, fontWeight: 600 }}
              component="div"
            >
              {Math.round(progressPercentage)}% Complete
            </Typography>
          </Stack>

          <LinearProgress
            variant="determinate"
            value={progressPercentage}
            data-testid="timeline-progress"
            aria-label={`Narrative arc progress ${Math.round(progressPercentage)} percent complete`}
            sx={{
              height: 6,
              borderRadius: 3,
              backgroundColor: 'var(--color-border-primary)',
              '& .MuiLinearProgress-bar': {
                backgroundColor: 'primary.main',
                borderRadius: 3,
              }
            }}
          />

          <Stack direction="row" spacing={1} justifyContent="center" sx={{ mt: 1 }}>
            <Chip
              label="Act 1 Complete"
              size="small"
              sx={{
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                borderColor: 'success.main',
                color: 'var(--color-success-text)',
                fontSize: '0.65rem',
                height: '20px',
              }}
            />
            <Chip
              label="3 Plot Threads"
              size="small"
              sx={{
                backgroundColor: 'background.paper',
                borderColor: 'divider',
                color: 'text.secondary',
                fontSize: '0.65rem',
                height: '20px',
              }}
            />
          </Stack>
        </ProgressHeader>

        {/* Timeline Track */}
        <TimelineTrack role="tablist" aria-label="Narrative Arc Timeline">
          {timelineEvents.map((event, index) => (
            <React.Fragment key={event.id}>
              <Fade in timeout={300 + index * 100}>
                <TimelineNode
                  status={event.status}
                  data-testid="timeline-node"
                  data-status={event.status}
                  data-turn={event.turn}
                  role="tab"
                  aria-current={event.status === 'current' ? 'step' : undefined}
                  aria-selected={focusIndex === index}
                  tabIndex={focusIndex === index ? 0 : -1}
                  ref={(node: HTMLDivElement | null) => {
                    nodeRefs.current[index] = node;
                  }}
                  onFocus={() => setFocusIndex(index)}
                  onKeyDown={(event) => handleNodeKeyDown(event, index)}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.3, delay: index * 0.05 }}
                >
                  <Avatar
                    sx={{
                      bgcolor: 'transparent',
                      color: getStatusColor(event.status),
                      width: isMobile ? 28 : 32,
                      height: isMobile ? 28 : 32,
                      mr: isMobile ? 1 : 0,
                      mb: isMobile ? 0 : 0.5,
                    }}
                  >
                    {getStatusIcon(event.status)}
                  </Avatar>

                  <Box sx={{ flex: 1, textAlign: isMobile ? 'left' : 'center' }}>
                    <Typography
                      variant="caption"
                      fontWeight={600}
                      sx={{
                        color: 'var(--color-text-primary)',
                        lineHeight: 1.2,
                        display: 'block',
                        mb: 0.25,
                      }}
                      component="div"
                    >
                      {event.title}
                    </Typography>

                    <Typography
                      variant="caption"
                      color="text.secondary"
                      data-testid={event.status === 'current' ? 'current-turn' : undefined}
                      sx={{
                        fontSize: '0.7rem',
                        display: 'block',
                        mb: 0.5,
                      }}
                      component="div"
                    >
                      Turn {event.turn}
                    </Typography>

                    <Stack
                      direction="row"
                      spacing={0.5}
                      alignItems="center"
                      justifyContent={isMobile ? 'flex-start' : 'center'}
                      flexWrap="wrap"
                    >
                      <Chip
                        label={event.type}
                        size="small"
                        {...(getTypeIcon(event.type) ? { icon: getTypeIcon(event.type) as React.ReactElement } : {})}
                        sx={{
                          height: '16px',
                          fontSize: '0.6rem',
                          backgroundColor: 'transparent',
                          color: 'var(--color-text-primary)',
                          borderColor: getStatusColor(event.status),
                          '& .MuiChip-icon': {
                            color: getStatusColor(event.status),
                          }
                        }}
                      />
                    </Stack>
                  </Box>
                </TimelineNode>
              </Fade>

              {index < timelineEvents.length - 1 && (
                <TimelineConnector>
                  <ConnectionIcon fontSize="small" />
                </TimelineConnector>
              )}
            </React.Fragment>
          ))}
        </TimelineTrack>
      </TimelineContainer>
    </GridTile>
  );
};

export default NarrativeTimeline;
