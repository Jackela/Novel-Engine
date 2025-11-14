import React, { useState, useEffect } from 'react';
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
import type { RunStateSummary } from './types';

const PipelineContainer = styled(Box)(({ theme }) => ({
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  
  [theme.breakpoints.down('md')]: {
    padding: theme.spacing(0.5),
  },
}));

const StageItem = styled(motion(ListItem))<{ status: string }>(({ theme, status }) => ({
  padding: theme.spacing(1, 0),
  borderBottom: `1px solid ${theme.palette.divider}`,
  borderLeft: `3px solid ${
    status === 'processing' ? theme.palette.primary.main :
    status === 'completed' ? theme.palette.success.main :
    status === 'error' ? theme.palette.error.main :
    theme.palette.text.secondary
  }`,
  paddingLeft: theme.spacing(1),
  borderRadius: theme.shape.borderRadius / 2,
  marginBottom: theme.spacing(0.5),
  background: status === 'processing' ? alpha(theme.palette.primary.main, 0.05) : 'transparent',
  transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
  '&:hover': {
    background: status === 'processing' ? alpha(theme.palette.primary.main, 0.1) : 'var(--color-bg-tertiary)',
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
  activeStepIndex: number;
  steps: TurnStep[];
}

interface TurnPipelineStatusProps {
  loading?: boolean;
  error?: boolean;
  runState?: RunStateSummary;
  onPhaseChange?: (phase: string) => void;
}

const TurnPipelineStatus: React.FC<TurnPipelineStatusProps> = ({ 
  loading, 
  error,
  runState,
  onPhaseChange,
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  
  const [pipelineData, setPipelineData] = useState<PipelineData>({
    currentTurn: 47,
    totalTurns: 150,
    queueLength: 3,
    averageProcessingTime: 2.3,
    activeStepIndex: 0,
    steps: [
      {
        id: 'world-update',
        name: 'World Update',
        status: 'processing',
        progress: 45,
        character: 'Aria Shadowbane',
      },
      {
        id: 'subjective-brief',
        name: 'Subjective Brief',
        status: 'queued',
        progress: 0,
      },
      {
        id: 'interaction-orchestration',
        name: 'Interaction Orchestration',
        status: 'queued',
        progress: 0,
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

  // Simulate pipeline progression with deterministic step advancement
  useEffect(() => {
    const interval = setInterval(() => {
      setPipelineData(prev => {
        const newData = { ...prev };
        const totalSteps = prev.steps.length;
        let steps = prev.steps.map(step => ({ ...step }));

        let activeIndex = Math.min(newData.activeStepIndex, totalSteps - 1);
        if (newData.activeStepIndex >= totalSteps) {
          activeIndex = totalSteps - 1;
        }

        const activeStep = newData.activeStepIndex >= totalSteps ? null : steps[activeIndex];

        if (activeStep) {
          if (activeStep.status === 'processing') {
            const increment = 40 + Math.random() * 35;
            const updatedProgress = Math.min(100, activeStep.progress + increment);
            steps[activeIndex] = { ...activeStep, progress: updatedProgress };
            if (updatedProgress >= 100) {
              steps[activeIndex] = {
                ...steps[activeIndex],
                status: 'completed',
                progress: 100,
                duration: Math.random() * 2 + 0.8,
              };
              newData.activeStepIndex = activeIndex + 1;
              activeIndex = newData.activeStepIndex;
            }
          } else if (activeStep.status === 'queued') {
            steps[activeIndex] = {
              ...activeStep,
              status: 'processing',
              progress: 35 + Math.random() * 25,
            };
          }
        }

        if (newData.activeStepIndex < totalSteps) {
          const candidateIndex = Math.max(newData.activeStepIndex, 0);
          const candidate = steps[candidateIndex];
          if (candidate && candidate.status === 'queued') {
            steps[candidateIndex] = {
              ...candidate,
              status: 'processing',
              progress: 30 + Math.random() * 30,
            };
          }
        }

        const completedCount = steps.filter(step => step.status === 'completed').length;
        const allCompleted = completedCount === totalSteps;

        if (!allCompleted && !steps.some(step => step.status === 'processing')) {
          const nextIndex = steps.findIndex(step => step.status === 'queued');
          if (nextIndex !== -1) {
            steps[nextIndex] = {
              ...steps[nextIndex],
              status: 'processing',
              progress: 35 + Math.random() * 30,
            };
            newData.activeStepIndex = nextIndex;
          }
        }

        if (allCompleted) {
          newData.currentTurn += 1;
          newData.queueLength = Math.max(0, newData.queueLength - 1 + Math.floor(Math.random() * 2));

          const characters = ['Aria Shadowbane', 'Merchant Aldric', 'Elder Thorne', 'Captain Vex'];
          steps = steps.map((step, index) => ({
            ...step,
            status: index === 0 ? 'processing' : 'queued',
            progress: index === 0 ? 30 + Math.random() * 20 : 0,
            character: step.id === 'input' || step.id === 'ai_generation'
              ? characters[Math.floor(Math.random() * characters.length)]
              : undefined,
            duration: undefined,
          }));
          newData.activeStepIndex = 0;
        }

        newData.steps = steps;
        return newData;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!onPhaseChange) return;
    const activeStep = pipelineData.steps[pipelineData.activeStepIndex];
    if (activeStep) {
      onPhaseChange(activeStep.name);
    }
  }, [pipelineData.steps, pipelineData.activeStepIndex, onPhaseChange]);

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

  return (
    <GridTile
      title="Turn Pipeline"
      data-testid="turn-pipeline-status"
      position={{
        desktop: { column: '8 / 11', height: '160px' },
        tablet: { column: '1 / 9', height: '140px' },
        mobile: { height: '120px' },
      }}
      loading={loading}
      error={error}
    >
      <PipelineContainer>
        {/* Header */}
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1, flexShrink: 0 }}>
          <Typography variant="body2" color="text.secondary" fontWeight={500}>
            Turn {pipelineData.currentTurn} of {pipelineData.totalTurns}
          </Typography>
          <Stack direction="row" spacing={0.5}>
            {runState && (
              <Chip
                data-testid="pipeline-run-state"
                size="small"
                label={runState.status.toUpperCase()}
                sx={{
                  textTransform: 'uppercase',
                  backgroundColor: (theme) =>
                    runState.status === 'running'
                      ? alpha(theme.palette.success.main, 0.15)
                      : runState.status === 'paused'
                        ? alpha(theme.palette.warning.main, 0.15)
                        : alpha(theme.palette.text.secondary, 0.1),
                  borderColor: (theme) =>
                    runState.status === 'running'
                      ? theme.palette.success.main
                      : runState.status === 'paused'
                        ? theme.palette.warning.main
                        : theme.palette.divider,
                  color: (theme) =>
                    runState.status === 'running'
                      ? theme.palette.success.main
                      : runState.status === 'paused'
                        ? theme.palette.warning.main
                        : theme.palette.text.secondary,
                  fontSize: '0.65rem',
                  height: '20px',
                }}
              />
            )}
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
                    status={step.status}
                    data-status={step.status}
                    data-phase={step.name}
                    data-step-index={index}
                    sx={{ 
                      py: isMobile ? 0.5 : 0.75,
                      px: 0,
                    }}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3, delay: index * 0.05 }}
                  >
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
                            data-status={step.status}
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
