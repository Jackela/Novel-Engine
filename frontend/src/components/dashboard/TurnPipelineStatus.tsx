import React, { useState, useEffect, useRef } from 'react';
import { 
  Box, 
  Typography, 
  Stack, 
  Chip, 
  LinearProgress, 
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Avatar,
  useTheme,
  useMediaQuery,
  Fade,
} from '@mui/material';
import { styled, alpha } from '@mui/material/styles';
import { motion, AnimatePresence } from 'framer-motion';
import {
  PlayCircleOutline as StartIcon,
  Psychology as ProcessingIcon,
  CheckCircle as CompleteIcon,
  Error as ErrorIcon,
  AccessTime as QueueIcon,
  Groups as CharacterIcon,
} from '@mui/icons-material';
import GridTile from '../layout/GridTile';

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
  borderLeft: `3px solid ${
    $status === 'processing' ? theme.palette.primary.main :
    $status === 'completed' ? theme.palette.success.main :
    $status === 'error' ? theme.palette.error.main :
    theme.palette.text.secondary
  }`,
  paddingLeft: theme.spacing(1),
  borderRadius: theme.shape.borderRadius / 2,
  marginBottom: theme.spacing(0.5),
  background: $status === 'processing' ? alpha(theme.palette.primary.main, 0.05) : 'transparent',
  transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
  '&:hover': {
    background: $status === 'processing' ? alpha(theme.palette.primary.main, 0.1) : 'var(--color-bg-tertiary)',
    borderLeftWidth: '4px',
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
    status === 'processing' ? alpha(theme.palette.primary.main, 0.2) :
    status === 'completed' ? alpha(theme.palette.success.main, 0.2) :
    status === 'queued' ? alpha(theme.palette.warning.main, 0.2) :
    status === 'error' ? alpha(theme.palette.error.main, 0.2) :
    'transparent',
  color: 
    status === 'processing' ? theme.palette.primary.main :
    status === 'completed' ? theme.palette.success.main :
    status === 'queued' ? theme.palette.warning.main :
    status === 'error' ? theme.palette.error.main :
    theme.palette.text.secondary,
  border: `1px solid ${
    status === 'processing' ? theme.palette.primary.main :
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
}

const TurnPipelineStatus: React.FC<TurnPipelineStatusProps> = ({ 
  loading, 
  error,
  status = 'idle',
  isLive = false,
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const previousStatus = useRef(status);
  
  const [pipelineData, setPipelineData] = useState<PipelineData>({
    currentTurn: 47,
    totalTurns: 150,
    queueLength: 3,
    averageProcessingTime: 2.3,
    steps: [
      {
        id: 'world-update',
        name: 'World Update',
        status: 'completed',
        progress: 100,
        duration: 0.5,
        character: 'Aria Shadowbane',
      },
      {
        id: 'subjective-brief',
        name: 'Subjective Brief',
        status: 'completed',
        progress: 100,
        duration: 1.2,
      },
      {
        id: 'interaction-orchestration',
        name: 'Interaction Orchestration',
        status: 'processing',
        progress: 73,
        character: 'Merchant Aldric',
      },
      {
        id: 'event-integration',
        name: 'Event Integration',
        status: 'queued',
        progress: 0,
      },
      {
        id: 'narrative-integration',
        name: 'Narrative Integration',
        status: 'queued',
        progress: 0,
      },
    ],
  });

  // Ensure pipeline visibly restarts whenever orchestration resumes.
  useEffect(() => {
    if (status === 'running' && previousStatus.current !== 'running') {
      setPipelineData(prev => ({
        ...prev,
        steps: prev.steps.map((step, index) => ({
          ...step,
          status: index === 0 ? 'processing' : 'queued',
          progress: index === 0 ? Math.random() * 30 : 0,
          duration: undefined,
        })),
      }));
    }
    previousStatus.current = status;
  }, [status]);

  // Simulate pipeline progression when running
  useEffect(() => {
    if (status !== 'running') {
      return;
    }

    const PROCESS_INTERVAL = 1200;
    const interval = setInterval(() => {
      setPipelineData(prev => {
        const next = { ...prev };

        const ensureProcessingStep = () => {
          const activeIndex = next.steps.findIndex(step => step.status === 'processing');
          if (activeIndex === -1) {
            const nextIndex = next.steps.findIndex(step => step.status !== 'completed');
            if (nextIndex !== -1) {
              next.steps[nextIndex] = {
                ...next.steps[nextIndex],
                status: 'processing',
                progress: Math.max(next.steps[nextIndex].progress, 20 + Math.random() * 15),
              };
            }
          }
        };

        next.steps = next.steps.map(step => {
          if (step.status === 'processing') {
            const increment = 35 + Math.random() * 30;
            const newProgress = Math.min(100, step.progress + increment);
            if (newProgress >= 100) {
              return {
                ...step,
                status: 'completed',
                progress: 100,
                duration: (step.duration ?? 0) + increment / 60,
              };
            }
            return { ...step, progress: newProgress };
          }
          return step;
        });

        ensureProcessingStep();

        const completedCount = next.steps.filter(step => step.status === 'completed').length;
        if (completedCount === next.steps.length) {
          const characters = ['Aria Shadowbane', 'Merchant Aldric', 'Elder Thorne', 'Captain Vex'];
          next.currentTurn += 1;
          next.queueLength = Math.max(0, next.queueLength - 1 + Math.floor(Math.random() * 2));
          next.steps = next.steps.map((step, index) => ({
            ...step,
            status: index === 0 ? 'processing' : 'queued',
            progress: index === 0 ? 25 + Math.random() * 20 : 0,
            character: step.id === 'world-update' || step.id === 'interaction-orchestration'
              ? characters[Math.floor(Math.random() * characters.length)]
              : undefined,
            duration: undefined,
          }));
        }

        return next;
      });
    }, PROCESS_INTERVAL);

    return () => clearInterval(interval);
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
    <GridTile
      title="Turn Pipeline"
      data-testid="turn-pipeline-status"
      data-role="pipeline"
      position={{
        desktop: { column: 'span 2', height: '260px' },
        tablet: { column: 'span 2', height: '240px' },
        mobile: { column: 'span 1', height: '220px' },
      }}
      loading={loading}
      error={error}
    >
      <PipelineContainer>
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
                backgroundColor: (theme) => status === 'running'
                  ? alpha(theme.palette.success.main, 0.15)
                  : alpha(theme.palette.text.primary, 0.05),
                color: (theme) => status === 'running'
                  ? theme.palette.success.main
                  : theme.palette.text.secondary,
              }}
            />
            {isLive && (
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
                      <ListItemText
                        primary={
                          <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 0.25 }}>
                            <Typography 
                              variant={isMobile ? 'caption' : 'body2'} 
                              fontWeight={500}
                              sx={{ color: (theme) => theme.palette.text.primary }}
                            >
                              {step.name}
                            </Typography>
                            <StatusChip 
                              status={step.status} 
                              label={step.status} 
                              size="small"
                            />
                          </Stack>
                        }
                        secondary={
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
                                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                                    {step.character}
                                  </Typography>
                                </Stack>
                              )}
                              {step.duration !== undefined && (
                                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                                  {step.duration.toFixed(1)}s
                                </Typography>
                              )}
                              {step.status === 'processing' && (
                                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                                  {step.progress.toFixed(0)}%
                                </Typography>
                              )}
                            </Stack>
                          </Box>
                        }
                      />
                    </Box>
                  </StageItem>
                </Fade>
              ))}
            </AnimatePresence>
          </List>
        </Box>
      </PipelineContainer>
    </GridTile>
  );
};

export default TurnPipelineStatus;
