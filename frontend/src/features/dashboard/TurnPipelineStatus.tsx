import React, { useState, useEffect, useRef } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import type { AppDispatch } from '@/store/store';
import { fetchDashboardData } from '@/store/slices/dashboardSlice';
import {
  Box,
  Typography,
  Stack,
  Chip,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  Avatar,
  useTheme,
  useMediaQuery,
  Fade,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Psychology as ProcessingIcon,
  CheckCircle as CompleteIcon,
  Error as ErrorIcon,
  AccessTime as QueueIcon,
  Groups as CharacterIcon,
} from '@mui/icons-material';
import type { RootState } from '@/store/store';

const PipelineContainer = styled(Box)(({ theme }) => ({
  height: '100%',
  display: 'flex',
  flexDirection: 'column',

  [theme.breakpoints.down('md')]: {
    padding: theme.spacing(0.5),
  },
}));

const StageItem = styled(motion(ListItem), {
  shouldForwardProp: (prop: PropertyKey) => prop !== '$status'
})<{ $status: string }>(({ theme, $status }) => ({
  padding: theme.spacing(1, 0),
  borderBottom: `1px solid ${theme.palette.divider}`,
  borderLeft: `3px solid ${$status === 'processing' ? theme.palette.primary.main :
    $status === 'completed' ? theme.palette.success.main :
      $status === 'error' ? theme.palette.error.main :
        theme.palette.text.secondary
    }`,
  paddingLeft: theme.spacing(1),
  borderRadius: theme.shape.borderRadius / 2,
  marginBottom: theme.spacing(0.5),
  background: $status === 'processing' ? 'rgba(0, 240, 255, 0.05)' : 'transparent',
  transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
  '&:hover': {
    background: $status === 'processing' ? 'rgba(0, 240, 255, 0.1)' : 'var(--color-bg-tertiary)',
    borderLeftWidth: '4px',
  },
  '&:focus-visible': {
    outline: `2px solid ${theme.palette.info.main}`,
    outlineOffset: 2,
  },
}));

const StatusChip = styled(Chip)<{ status: string }>(({ theme, status }) => ({
  fontSize: '0.65rem',
  height: '18px',
  fontWeight: 500,
  '& .MuiChip-label': {
    padding: '0 6px',
  },
  backgroundColor:
    status === 'processing' ? 'rgba(0, 240, 255, 0.2)' :
      status === 'completed' ? 'rgba(0, 255, 157, 0.2)' :
        status === 'queued' ? 'rgba(255, 184, 0, 0.2)' :
          status === 'error' ? 'rgba(255, 0, 85, 0.2)' :
            'transparent',
  color:
    status === 'processing' ? theme.palette.primary.main :
      status === 'completed' ? theme.palette.success.main :
        status === 'queued' ? theme.palette.warning.main :
          status === 'error' ? theme.palette.error.main :
            theme.palette.text.secondary,
  border: `1px solid ${status === 'processing' ? theme.palette.primary.main :
    status === 'completed' ? theme.palette.success.main :
      status === 'queued' ? theme.palette.warning.main :
        status === 'error' ? theme.palette.error.main :
          theme.palette.divider
    }`,
}));

const AnimatedProgress = styled(motion(LinearProgress))(({ theme }) => ({
  height: 4,
  borderRadius: 2,
  backgroundColor: theme.palette.divider,
  '& .MuiLinearProgress-bar': {
    borderRadius: 2,
    transition: 'transform 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
  },
}));

interface TurnStep {
  id: string;
  name: string;
  status: 'queued' | 'processing' | 'completed' | 'error';
  progress: number;
  duration?: number;
  character?: string;
}

interface PipelineData {
  currentTurn: number;
  totalTurns: number;
  queueLength: number;
  averageProcessingTime: number;
  steps: TurnStep[];
}

interface TurnPipelineStatusProps {
  loading?: boolean;
  error?: boolean;
  status?: 'idle' | 'running' | 'paused' | 'stopped';
  isLive?: boolean;
  isOnline?: boolean;
}

// Default empty pipeline data structure
const DEFAULT_PIPELINE: PipelineData = {
  currentTurn: 0,
  totalTurns: 0,
  queueLength: 0,
  averageProcessingTime: 0,
  steps: [],
};

const TurnPipelineStatus: React.FC<TurnPipelineStatusProps> = ({
  loading,
  status = 'idle',
  isLive = false,
  isOnline = true,
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const previousStatus = useRef(status);
  const dispatch = useDispatch<AppDispatch>();

  // Get pipeline data from Redux store
  const storePipeline = useSelector((state: RootState) => state.dashboard.pipeline);

  // Fetch orchestration status on mount and periodically
  useEffect(() => {
    // Initial fetch
    dispatch(fetchDashboardData());

    // Poll for updates every 5 seconds when running
    const interval = setInterval(() => {
      dispatch(fetchDashboardData());
    }, 5000);

    return () => clearInterval(interval);
  }, [dispatch]);

  // Use store data if available, otherwise use empty defaults
  const hasStoreData = storePipeline && storePipeline.steps && storePipeline.steps.length > 0;

  const [pipelineData, setPipelineData] = useState<PipelineData>(
    hasStoreData ? {
      currentTurn: storePipeline.currentTurn,
      totalTurns: storePipeline.totalTurns,
      queueLength: storePipeline.queueLength,
      averageProcessingTime: storePipeline.averageProcessingTime,
      steps: storePipeline.steps.map(step => ({
        id: step.id,
        name: step.name,
        status: step.status,
        progress: step.progress,
        ...(step.duration !== undefined && { duration: step.duration }),
        ...(step.character !== undefined && { character: step.character }),
      })),
    } : DEFAULT_PIPELINE
  );

  // Sync with Redux store when it changes
  useEffect(() => {
    if (storePipeline && storePipeline.steps && storePipeline.steps.length > 0) {
      setPipelineData({
        currentTurn: storePipeline.currentTurn,
        totalTurns: storePipeline.totalTurns,
        queueLength: storePipeline.queueLength,
        averageProcessingTime: storePipeline.averageProcessingTime,
        steps: storePipeline.steps.map(step => ({
          id: step.id,
          name: step.name,
          status: step.status,
          progress: step.progress,
          ...(step.duration !== undefined && { duration: step.duration }),
          ...(step.character !== undefined && { character: step.character }),
        })),
      });
    }
  }, [storePipeline]);

  // Track status changes for UI feedback
  useEffect(() => {
    previousStatus.current = status;
  }, [status]);

  const getStepIcon = (step: TurnStep) => {
    const iconProps = { fontSize: 'small' as const };
    switch (step.status) {
      case 'completed':
        return <CompleteIcon {...iconProps} sx={{ color: (theme) => theme.palette.success.main }} />;
      case 'processing':
        return <ProcessingIcon {...iconProps} sx={{ color: (theme) => theme.palette.primary.main }} />;
      case 'error':
        return <ErrorIcon {...iconProps} sx={{ color: (theme) => theme.palette.error.main }} />;
      default:
        return <QueueIcon {...iconProps} sx={{ color: (theme) => theme.palette.text.secondary }} />;
    }
  };

  const statusLabel = (() => {
    switch (status) {
      case 'running':
        return 'Processing';
      case 'paused':
        return 'Paused';
      case 'stopped':
        return 'Stopped';
      default:
        return 'Idle';
    }
  })();

  return (

    <PipelineContainer className={loading ? 'loading' : ''} data-testid="turn-pipeline-status">
      {/* Header */}
      <Stack direction={isMobile ? 'column' : 'row'} justifyContent="space-between" alignItems={isMobile ? 'flex-start' : 'center'} sx={{ mb: 1, flexShrink: 0 }} spacing={1}>
        <Stack direction="row" spacing={1} alignItems="center">
          <Typography variant="body2" color="text.secondary" fontWeight={500}>
            Turn {pipelineData.currentTurn} of {pipelineData.totalTurns}
          </Typography>
          <Chip
            label={statusLabel}
            size="small"
            data-testid="pipeline-run-state"
            sx={{
              height: 20,
              fontSize: '0.65rem',
              fontWeight: 600,
              backgroundColor: status === 'running'
                ? 'rgba(0, 255, 157, 0.15)'
                : 'rgba(255, 255, 255, 0.05)',
              color: (theme) => status === 'running'
                ? theme.palette.success.main
                : theme.palette.text.secondary,
            }}
          />
          {isLive && isOnline && (
            <Chip
              label="LIVE"
              color="success"
              size="small"
              data-testid="pipeline-live-indicator"
              sx={{
                fontWeight: 700,
                letterSpacing: '0.04em',
                height: 20,
              }}
            />
          )}

          {!isLive && isOnline && (
            <Chip
               label="ONLINE"
               size="small"
               data-testid="pipeline-live-indicator"
               sx={{
                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                color: (theme) => theme.palette.text.secondary,
                fontWeight: 700,
                letterSpacing: '0.04em',
                height: 20,
              }}
            />
          )}

          {!isOnline && (
            <Chip
              label="OFFLINE"
              color="error"
              size="small"
              data-testid="pipeline-live-indicator"
              sx={{
                fontWeight: 700,
                letterSpacing: '0.04em',
                height: 20,
              }}
            />
          )}
        </Stack>
        <Stack direction="row" spacing={0.5}>
          <Chip
            label={`${pipelineData.queueLength} queued`}
            size="small"
            sx={{
              backgroundColor: (theme) => theme.palette.background.paper,
              borderColor: (theme) => theme.palette.divider,
              color: (theme) => theme.palette.text.secondary,
              fontSize: '0.65rem',
              height: '20px',
            }}
          />
          <Chip
            label={`${pipelineData.averageProcessingTime.toFixed(1)}s avg`}
            size="small"
            sx={{
              backgroundColor: (theme) => theme.palette.background.paper,
              borderColor: (theme) => theme.palette.divider,
              color: (theme) => theme.palette.text.secondary,
              fontSize: '0.65rem',
              height: '20px',
            }}
          />
        </Stack>
      </Stack>

      {/* Pipeline Steps */}
      <Box sx={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
        <List dense sx={{ py: 0 }}>
          <AnimatePresence>
            {pipelineData.steps.map((step, index) => (
              <Fade in key={step.id} timeout={300 + index * 100}>
                <StageItem
                  $status={step.status}
                  data-status={step.status}
                  data-phase={step.id}
                  data-phase-name={step.name}
                  data-step-index={index}
                  tabIndex={0}
                  aria-label={`${step.name} ${step.status}${step.progress ? ` ${step.progress.toFixed(0)} percent` : ''}`}
                  sx={{
                    py: isMobile ? 0.5 : 0.75,
                    px: 0,
                  }}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: index * 0.05 }}
                >
                  {/* Hidden marker ensures deterministic selectors for Playwright & monitoring */}
                  <Box
                    component="span"
                    sx={{ display: 'none' }}
                    data-testid="pipeline-stage-marker"
                    data-status={step.status}
                    data-phase={step.id}
                    data-phase-name={step.name}
                    data-step-index={index}
                  />
                  <Box sx={{ display: 'flex', width: '100%', alignItems: 'center' }}>
                    <ListItemIcon sx={{ minWidth: 32 }}>
                      <Avatar
                        sx={{
                          bgcolor: 'transparent',
                          width: 28,
                          height: 28,
                        }}
                      >
                        {getStepIcon(step)}
                      </Avatar>
                    </ListItemIcon>
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 0.25 }}>
                        <Typography
                          variant={isMobile ? 'caption' : 'body2'}
                          fontWeight={500}
                          sx={{ color: (theme) => theme.palette.text.primary }}
                          component="div"
                        >
                          {step.name}
                        </Typography>
                        <StatusChip status={step.status} label={step.status} size="small" />
                      </Stack>
                      <Box sx={{ mt: 0.5 }}>
                        {step.status === 'processing' && (
                          <AnimatedProgress
                            variant="determinate"
                            value={step.progress}
                            sx={{ mb: 0.5 }}
                            initial={{ scaleX: 0 }}
                            animate={{ scaleX: 1 }}
                            transition={{ duration: 0.5 }}
                            aria-label={`${step.name} processing progress`}
                            data-testid="pipeline-progress"
                          />
                        )}
                        <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap">
                          {step.character && (
                            <Stack direction="row" alignItems="center" spacing={0.5}>
                              <CharacterIcon sx={{ fontSize: '14px', color: (theme) => theme.palette.primary.main }} />
                              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }} component="span">
                                {step.character}
                              </Typography>
                            </Stack>
                          )}
                          {step.duration !== undefined && (
                            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }} component="span">
                              {step.duration.toFixed(1)}s
                            </Typography>
                          )}
                          {step.status === 'processing' && (
                            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }} component="span">
                              {step.progress.toFixed(0)}%
                            </Typography>
                          )}
                        </Stack>
                      </Box>
                    </Box>
                  </Box>
                </StageItem>
              </Fade>
            ))}
          </AnimatePresence>
        </List>
      </Box>
    </PipelineContainer>
  );
};

export default TurnPipelineStatus;
