import React, { useState } from 'react';
import { 
  Box, 
  Typography, 
  Chip, 
  Stack,
  LinearProgress,
  Avatar,
  useTheme,
  useMediaQuery 
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  CheckCircle as CompletedIcon,
  RadioButtonUnchecked as PendingIcon,
  PlayCircle as ActiveIcon,
  MenuBook as ChapterIcon
} from '@mui/icons-material';
import GridTile from '../layout/GridTile';

const TimelineContainer = styled(Box)(({ theme }) => ({
  width: '100%',
  height: '100%',
  position: 'relative',
  padding: theme.spacing(1),
  overflowX: 'auto',
  overflowY: 'hidden',
  
  [theme.breakpoints.down('md')]: {
    padding: theme.spacing(0.5),
    overflowX: 'hidden',
    overflowY: 'auto',
  },
}));

const TimelineTrack = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  position: 'relative',
  minWidth: 'max-content',
  height: '100%',
  
  [theme.breakpoints.down('md')]: {
    flexDirection: 'column',
    minWidth: 'auto',
    width: '100%',
    height: 'auto',
  },
}));

const TimelineNode = styled(Box)<{ status: 'completed' | 'active' | 'pending' }>(
  ({ theme, status }) => ({
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    minWidth: '120px',
    padding: theme.spacing(1),
    position: 'relative',
    
    [theme.breakpoints.down('md')]: {
      flexDirection: 'row',
      minWidth: 'auto',
      width: '100%',
      padding: theme.spacing(1),
      borderRadius: theme.spacing(1),
      backgroundColor: status === 'active' 
        ? theme.palette.primary.main + '15'
        : theme.palette.action.hover,
      marginBottom: theme.spacing(0.5),
    },
  })
);

const TimelineConnector = styled(Box)(({ theme }) => ({
  width: '40px',
  height: '2px',
  backgroundColor: theme.palette.divider,
  position: 'relative',
  
  [theme.breakpoints.down('md')]: {
    width: '2px',
    height: '20px',
    alignSelf: 'center',
  },
}));

const ProgressIndicator = styled(Box)(({ theme }) => ({
  width: '100%',
  marginBottom: theme.spacing(1),
}));


interface TimelineEvent {
  id: string;
  title: string;
  description: string;
  turn: number;
  status: 'completed' | 'active' | 'pending';
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
      status: 'active',
      type: 'character',
    },
    {
      id: '4',
      title: 'Crystal Caverns',
      description: 'New territory',
      turn: 75,
      status: 'pending',
      type: 'chapter',
    },
    {
      id: '5',
      title: 'Final Confrontation',
      description: 'Climax approach',
      turn: 120,
      status: 'pending',
      type: 'climax',
    },
  ]);

  const currentTurn = 47;
  const maxTurn = 150;
  const progressPercentage = (currentTurn / maxTurn) * 100;

  const getStatusIcon = (status: TimelineEvent['status']) => {
    switch (status) {
      case 'completed':
        return <CompletedIcon fontSize="small" />;
      case 'active':
        return <ActiveIcon fontSize="small" />;
      default:
        return <PendingIcon fontSize="small" />;
    }
  };

  const getStatusColor = (status: TimelineEvent['status']) => {
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
      title="Narrative Arc Timeline"
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
        <ProgressIndicator>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 0.5 }}>
            <Typography variant="caption" color="text.secondary">
              Turn {currentTurn} of {maxTurn}
            </Typography>
            <Typography variant="caption" color="primary">
              {Math.round(progressPercentage)}% Complete
            </Typography>
          </Stack>
          <LinearProgress 
            variant="determinate" 
            value={progressPercentage}
            sx={{ height: 6, borderRadius: 3 }}
          />
          <Stack direction="row" spacing={1} justifyContent="center" sx={{ mt: 1 }}>
            <Chip label="Act 1 Complete" size="small" color="success" variant="outlined" />
            <Chip label="3 Plot Threads" size="small" variant="outlined" />
          </Stack>
        </ProgressIndicator>

        {isMobile ? (
          // Mobile: Vertical timeline
          <Box sx={{ flex: 1, overflowY: 'auto', maxHeight: '120px' }}>
            <Stack spacing={0.5}>
              {timelineEvents.map((event, index) => (
                <Box key={event.id}>
                  <TimelineNode status={event.status}>
                    <Avatar
                      sx={{
                        bgcolor: 'transparent',
                        color: getStatusColor(event.status),
                        width: 28,
                        height: 28,
                        mr: isMobile ? 1 : 0,
                        mb: isMobile ? 0 : 0.5,
                      }}
                    >
                      {getStatusIcon(event.status)}
                    </Avatar>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="caption" fontWeight={600} sx={{ lineHeight: 1.2 }}>
                        {event.title}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', fontSize: '0.7rem' }}>
                        {event.description} • Turn {event.turn}
                      </Typography>
                    </Box>
                    <Chip
                      label={event.type}
                      size="small"
                      variant="outlined"
                      sx={{ 
                        height: '18px', 
                        fontSize: '0.6rem',
                        color: getStatusColor(event.status),
                        borderColor: getStatusColor(event.status)
                      }}
                    />
                  </TimelineNode>
                  
                  {index < timelineEvents.length - 1 && (
                    <TimelineConnector />
                  )}
                </Box>
              ))}
            </Stack>
          </Box>
        ) : (
          // Desktop: Horizontal timeline
          <Box sx={{ flex: 1 }}>
            <TimelineTrack>
              {timelineEvents.map((event, index) => (
                <React.Fragment key={event.id}>
                  <TimelineNode status={event.status}>
                    <Avatar
                      sx={{
                        bgcolor: 'transparent',
                        color: getStatusColor(event.status),
                        width: 32,
                        height: 32,
                        mb: 0.5,
                      }}
                    >
                      {getStatusIcon(event.status)}
                    </Avatar>
                    <Typography variant="caption" fontWeight={600} sx={{ textAlign: 'center', lineHeight: 1.2 }}>
                      {event.title}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ textAlign: 'center', fontSize: '0.7rem' }}>
                      Turn {event.turn}
                    </Typography>
                    <Chip
                      label={event.type}
                      size="small"
                      variant="outlined"
                      sx={{ 
                        height: '16px', 
                        fontSize: '0.6rem',
                        mt: 0.5,
                        color: getStatusColor(event.status),
                        borderColor: getStatusColor(event.status)
                      }}
                    />
                  </TimelineNode>
                  
                  {index < timelineEvents.length - 1 && (
                    <TimelineConnector />
                  )}
                </React.Fragment>
              ))}
            </TimelineTrack>
          </Box>
        )}
      </TimelineContainer>
    </GridTile>
  );
};

export default NarrativeTimeline;