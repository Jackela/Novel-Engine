import React, { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  LinearProgress,
  Paper,
  Chip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  CircularProgress,
  Alert,
  Divider,
  Badge,
  Tooltip,
} from '@mui/material';
import {
  Psychology as PsychologyIcon,
  AutoStories as StoryIcon,
  Group as GroupIcon,
  Check as CheckIcon,
  Schedule as ScheduleIcon,
  Speed as SpeedIcon,
  Memory as MemoryIcon,
  Wifi as WifiIcon,
  WifiOff as WifiOffIcon,
  SignalWifi4Bar as SignalIcon,
} from '@mui/icons-material';
import { useWebSocketProgress, ProgressUpdate } from '../../hooks/useWebSocketProgress';

interface Props {
  isGenerating: boolean;
  progress: number;
  currentStage: string;
  estimatedTimeRemaining: number;
  error: string | null;
  generationId?: string | null;
  enableRealTimeUpdates?: boolean;
}

const GENERATION_STAGES = [
  {
    id: 'initializing',
    label: 'Initializing',
    description: 'Setting up generation parameters',
    icon: MemoryIcon,
    threshold: 0,
  },
  {
    id: 'analyzing',
    label: 'Character Analysis',
    description: 'Analyzing character personalities and relationships',
    icon: PsychologyIcon,
    threshold: 20,
  },
  {
    id: 'planning',
    label: 'Narrative Planning',
    description: 'Creating story structure and plot outline',
    icon: StoryIcon,
    threshold: 40,
  },
  {
    id: 'generating',
    label: 'Story Generation',
    description: 'AI agents creating story content',
    icon: GroupIcon,
    threshold: 60,
  },
  {
    id: 'finalizing',
    label: 'Finalizing',
    description: 'Post-processing and quality checks',
    icon: CheckIcon,
    threshold: 90,
  },
];

export default function GenerationProgress({
  isGenerating,
  progress: propProgress,
  currentStage: propCurrentStage,
  estimatedTimeRemaining: propEstimatedTime,
  error,
  generationId,
  enableRealTimeUpdates = true,
}: Props) {
  // State for real-time updates
  const [realtimeData, setRealtimeData] = useState<{
    progress: number;
    currentStage: string;
    estimatedTimeRemaining: number;
    stageDetail?: string;
    activeAgents?: string[];
  } | null>(null);

  // WebSocket hook for real-time updates
  const {
    isConnected: wsConnected,
    lastUpdate,
    error: wsError,
    connectionAttempts,
  } = useWebSocketProgress({
    generationId,
    enabled: enableRealTimeUpdates && isGenerating && !!generationId,
    onUpdate: (update: ProgressUpdate) => {
      setRealtimeData({
        progress: update.progress,
        currentStage: update.stage,
        estimatedTimeRemaining: update.estimated_time_remaining,
        stageDetail: update.stage_detail,
        activeAgents: update.active_agents,
      });
    },
    onError: (error) => {
      console.warn('WebSocket progress error:', error);
    },
  });

  // Use real-time data if available, otherwise fall back to props
  const progress = realtimeData?.progress ?? propProgress;
  const currentStage = realtimeData?.currentStage ?? propCurrentStage;
  const estimatedTimeRemaining = realtimeData?.estimatedTimeRemaining ?? propEstimatedTime;
  const stageDetail = realtimeData?.stageDetail;
  const activeAgents = realtimeData?.activeAgents ?? [];

  // Connection status for display
  const connectionStatus = enableRealTimeUpdates && generationId
    ? wsConnected
      ? 'connected'
      : connectionAttempts > 0
      ? 'reconnecting'
      : 'disconnected'
    : 'disabled';
  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    
    if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}s`;
    }
    return `${remainingSeconds}s`;
  };

  const getCurrentStageIndex = () => {
    for (let i = GENERATION_STAGES.length - 1; i >= 0; i--) {
      if (progress >= GENERATION_STAGES[i].threshold) {
        return i;
      }
    }
    return 0;
  };

  const currentStageIndex = getCurrentStageIndex();

  if (error) {
    return (
      <Paper sx={{ p: 3 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            Generation Failed
          </Typography>
          <Typography variant="body2">
            {error}
          </Typography>
        </Alert>
        
        <Typography variant="body2" color="text.secondary">
          The story generation encountered an error. Please try again with different parameters or check your connection.
        </Typography>
      </Paper>
    );
  }

  return (
    <Box>
      {/* Main Progress Display */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
          {isGenerating ? (
            <CircularProgress size={40} />
          ) : (
            <CheckIcon sx={{ fontSize: 40, color: 'success.main' }} />
          )}
          
          <Box sx={{ flexGrow: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                {isGenerating ? 'Generating Story...' : 'Story Generation Complete'}
              </Typography>
              
              {/* Real-time connection indicator */}
              {enableRealTimeUpdates && generationId && (
                <Tooltip
                  title={
                    connectionStatus === 'connected'
                      ? 'Real-time updates active'
                      : connectionStatus === 'reconnecting'
                      ? `Reconnecting... (attempt ${connectionAttempts})`
                      : connectionStatus === 'disconnected'
                      ? 'Real-time updates disconnected'
                      : 'Real-time updates disabled'
                  }
                >
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    {connectionStatus === 'connected' && (
                      <Badge color="success" variant="dot">
                        <SignalIcon sx={{ fontSize: 16, color: 'success.main' }} />
                      </Badge>
                    )}
                    {connectionStatus === 'reconnecting' && (
                      <Badge color="warning" variant="dot">
                        <WifiIcon sx={{ fontSize: 16, color: 'warning.main' }} />
                      </Badge>
                    )}
                    {connectionStatus === 'disconnected' && (
                      <WifiOffIcon sx={{ fontSize: 16, color: 'error.main' }} />
                    )}
                  </Box>
                </Tooltip>
              )}
            </Box>
            
            <Typography variant="body2" color="text.secondary">
              {stageDetail || currentStage}
            </Typography>
            
            {/* Active agents indicator */}
            {activeAgents.length > 0 && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
                <Typography variant="caption" color="text.secondary">
                  Active: 
                </Typography>
                {activeAgents.map((agent, index) => (
                  <Chip
                    key={agent}
                    label={agent.replace('Agent', '')}
                    size="small"
                    variant="outlined"
                    color="primary"
                    sx={{ height: 16, fontSize: '0.625rem' }}
                  />
                ))}
              </Box>
            )}
          </Box>

          {isGenerating && (
            <Box sx={{ textAlign: 'right' }}>
              <Typography variant="h5" sx={{ fontWeight: 700, color: 'primary.main' }}>
                {Math.round(progress)}%
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Complete
              </Typography>
            </Box>
          )}
        </Box>

        {/* Progress Bar */}
        <Box sx={{ mb: 2 }}>
          <LinearProgress
            variant="determinate"
            value={progress}
            sx={{
              height: 8,
              borderRadius: 1,
              '& .MuiLinearProgress-bar': {
                borderRadius: 1,
              },
            }}
          />
        </Box>

        {/* Time and Status */}
        {isGenerating && (
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <ScheduleIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
              <Typography variant="body2" color="text.secondary">
                Est. {formatTime(estimatedTimeRemaining)} remaining
              </Typography>
            </Box>
            
            <Chip
              label={isGenerating ? 'Generating' : 'Complete'}
              color={isGenerating ? 'primary' : 'success'}
              size="small"
            />
          </Box>
        )}
      </Paper>

      {/* Detailed Stage Progress */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
          Generation Stages
        </Typography>

        <List dense>
          {GENERATION_STAGES.map((stage, index) => {
            const isCompleted = progress > stage.threshold;
            const isActive = index === currentStageIndex && isGenerating;
            const IconComponent = stage.icon;

            return (
              <React.Fragment key={stage.id}>
                <ListItem
                  sx={{
                    pl: 0,
                    opacity: isCompleted || isActive ? 1 : 0.5,
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 40 }}>
                    {isCompleted ? (
                      <CheckIcon sx={{ color: 'success.main' }} />
                    ) : isActive ? (
                      <CircularProgress size={20} />
                    ) : (
                      <IconComponent sx={{ color: 'text.secondary' }} />
                    )}
                  </ListItemIcon>

                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography
                          variant="subtitle2"
                          sx={{
                            fontWeight: isActive ? 600 : 500,
                            color: isCompleted ? 'success.main' : isActive ? 'primary.main' : 'text.primary',
                          }}
                        >
                          {stage.label}
                        </Typography>
                        {isCompleted && (
                          <Chip label="Complete" size="small" color="success" variant="outlined" />
                        )}
                        {isActive && (
                          <Chip label="In Progress" size="small" color="primary" variant="outlined" />
                        )}
                      </Box>
                    }
                    secondary={stage.description}
                  />

                  <Box sx={{ textAlign: 'right', minWidth: 60 }}>
                    <Typography variant="caption" color="text.secondary">
                      {isCompleted ? '100%' : isActive ? `${Math.round(progress)}%` : '0%'}
                    </Typography>
                  </Box>
                </ListItem>

                {index < GENERATION_STAGES.length - 1 && <Divider />}
              </React.Fragment>
            );
          })}
        </List>
        </Collapse>
      </Paper>

      {/* Performance Metrics - Collapsible on Mobile */}
      {isGenerating && (
        <Paper sx={{ p: { xs: 2, sm: 3 }, mt: 3 }}>
          <Box sx={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            mb: 2
          }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Performance Metrics
            </Typography>
            
            {isMobile && (
              <IconButton
                onClick={() => setShowMetrics(!showMetrics)}
                size="small"
                aria-label={showMetrics ? 'Hide metrics' : 'Show metrics'}
              >
                {showMetrics ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            )}
          </Box>

          <Collapse in={showMetrics || !isMobile}>
          <Box sx={{ 
            display: 'grid', 
            gridTemplateColumns: { 
              xs: '1fr', 
              sm: 'repeat(auto-fit, minmax(150px, 1fr))',
              md: 'repeat(auto-fit, minmax(200px, 1fr))'
            }, 
            gap: 2 
          }}>
            <Box sx={{ textAlign: 'center' }}>
              <SpeedIcon sx={{ fontSize: 32, color: 'primary.main', mb: 1 }} />
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                {progress > 0 ? Math.round(100 / (progress / 100)) : '--'}s
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Est. Total Time
              </Typography>
            </Box>

            <Box sx={{ textAlign: 'center' }}>
              <MemoryIcon sx={{ fontSize: 32, color: 'info.main', mb: 1 }} />
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                {Math.round(progress / 20)}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Turns Processed
              </Typography>
            </Box>

            <Box sx={{ textAlign: 'center' }}>
              <GroupIcon sx={{ fontSize: 32, color: 'secondary.main', mb: 1 }} />
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Multi-Agent
              </Typography>
              <Typography variant="caption" color="text.secondary">
                AI Orchestration
              </Typography>
            </Box>
          </Box>
          </Collapse>
        </Paper>
      )}

      {/* Tips and Information - Enhanced Mobile Layout */}
      <Paper sx={{ 
        p: { xs: 2, sm: 3 }, 
        mt: 3, 
        bgcolor: 'action.hover',
        '& .MuiListItem-root': {
          px: { xs: 0, sm: 2 },
        }
      }}>
        <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 600 }}>
          What's Happening?
        </Typography>
        
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Our AI agents are working together to create your story:
        </Typography>

        <List dense sx={{
          '& .MuiListItemText-secondary': {
            fontSize: { xs: '0.875rem', sm: '0.875rem' }
          }
        }}>
          <ListItem sx={{ py: { xs: 1, sm: 0.5 } }}>
            <ListItemText
              primary="Character Analysis"
              secondary="Each character's personality, motivations, and relationships are analyzed"
            />
          </ListItem>
          <ListItem sx={{ py: { xs: 1, sm: 0.5 } }}>
            <ListItemText
              primary="Narrative Planning"
              secondary="The overall story structure and key plot points are planned"
            />
          </ListItem>
          <ListItem sx={{ py: { xs: 1, sm: 0.5 } }}>
            <ListItemText
              primary="Turn Generation"
              secondary="Multiple AI agents take turns writing from each character's perspective"
            />
          </ListItem>
          <ListItem sx={{ py: { xs: 1, sm: 0.5 } }}>
            <ListItemText
              primary="Quality Control"
              secondary="The story is reviewed for consistency and narrative flow"
            />
          </ListItem>
        </List>
      </Paper>
    </Box>
  );
}