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
import type { ChipProps } from '@mui/material';
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
import type { DensityMode } from '@/utils/density';

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
  steps: TurnStep[];
}

interface TurnPipelineStatusProps {
  loading?: boolean;
  error?: boolean;
  status?: 'idle' | 'running' | 'paused';
  isLive?: boolean;
  runSummary?: {
    phase: string;
    completed: number;
    total: number;
    lastSignal?: string;
    queueLength?: number;
  };
  density?: DensityMode;
}

const TurnPipelineStatus: React.FC<TurnPipelineStatusProps> = ({ loading, error, status = 'idle', isLive = false, runSummary, density = 'relaxed' }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  
  const [pipelineData, setPipelineData] = useState<PipelineData>({
    currentTurn: 47,
    totalTurns: 150,
    queueLength: 3,
    averageProcessingTime: 2.3,
    steps: [
      {
        id: 'input',
        name: 'Input Processing',
        status: 'completed',
        progress: 100,
        duration: 0.5,
        character: 'Aria Shadowbane',
      },
      {
        id: 'context',
        name: 'Context Analysis',
        status: 'completed',
        progress: 100,
        duration: 1.2,
      },
      {
        id: 'ai_generation',
        name: 'AI Response Generation',
        status: 'processing',
        progress: 73,
        character: 'Merchant Aldric',
      },
      {
        id: 'validation',
        name: 'Response Validation',
        status: 'queued',
        progress: 0,
      },
      {
        id: 'output',
        name: 'Output Delivery',
        status: 'queued',
        progress: 0,
      },
    ],
  });

  // Simulate pipeline progression
  useEffect(() => {
    const interval = setInterval(() => {
      setPipelineData(prev => {
        const newData = { ...prev };
        
        // Update step progress
        newData.steps = prev.steps.map(step => {
          if (step.status === 'processing') {
            const newProgress = Math.min(100, step.progress + Math.random() * 15);
            if (newProgress >= 100) {
              return { ...step, status: 'completed', progress: 100, duration: Math.random() * 2 + 0.5 };
            }
            return { ...step, progress: newProgress };
          }
          return step;
        });

        // Move pipeline forward
        const processingIndex = newData.steps.findIndex(step => step.status === 'processing');
        const completedCount = newData.steps.filter(step => step.status === 'completed').length;
        
        if (processingIndex !== -1 && newData.steps[processingIndex].progress >= 100) {
          // Start next step
          const nextIndex = processingIndex + 1;
          if (nextIndex < newData.steps.length) {
            newData.steps[nextIndex] = { 
              ...newData.steps[nextIndex], 
              status: 'processing', 
              progress: Math.random() * 20 
            };
          }
        }

        // Complete turn and reset if all steps done
        if (completedCount === newData.steps.length) {
          newData.currentTurn += 1;
          newData.queueLength = Math.max(0, newData.queueLength - 1 + Math.floor(Math.random() * 2));
          
          // Reset pipeline for next turn
          const characters = ['Aria Shadowbane', 'Merchant Aldric', 'Elder Thorne', 'Captain Vex'];
          newData.steps = newData.steps.map((step, index) => ({
            ...step,
            status: index === 0 ? 'processing' : 'queued',
            progress: index === 0 ? Math.random() * 30 : 0,
            character: step.id === 'input' || step.id === 'ai_generation' 
              ? characters[Math.floor(Math.random() * characters.length)]
              : undefined,
            duration: undefined,
          }));
        }

        return newData;
      });
    }, 2000);

    return () => clearInterval(interval);
  }, []);

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

  const statusLabel = status === 'running' ? 'Running' : status === 'paused' ? 'Paused' : 'Idle';
  const statusChipColor: ChipProps['color'] =
    status === 'running' ? 'success' : status === 'paused' ? 'warning' : 'default';
  const tileClassName =
    status === 'running'
      ? 'pipeline-active active'
      : status === 'paused'
      ? 'pipeline-paused'
      : 'pipeline-idle';

  return (
    <GridTile
      title="Turn Pipeline"
      data-testid="turn-pipeline-status"
      className={tileClassName}
      position={{
        desktop: { column: '5 / 9', height: '280px' },
        tablet: { column: '1 / 9', height: '240px' },
        mobile: { height: '180px' },
      }}
      loading={loading}
      error={error}
    >
      <PipelineContainer data-density={density} sx={density === 'compact' ? { maxHeight: 360 } : undefined}>
        {/* Header */}
        <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', md: 'center' }} sx={{ mb: 1, flexShrink: 0, gap: 1 }}>
          <Stack spacing={0.5}>
            <Typography variant="body2" color="text.secondary" fontWeight={500}>
              Turn {pipelineData.currentTurn} of {pipelineData.totalTurns}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Phase: {runSummary?.phase ?? 'Idle'}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Completed: {runSummary ? `${runSummary.completed}/${runSummary.total}` : `${pipelineData.currentTurn} / ${pipelineData.totalTurns}`}
            </Typography>
            {runSummary?.lastSignal && (
              <Typography variant="caption" color="text.secondary">
                Last signal {runSummary.lastSignal}
              </Typography>
            )}
          </Stack>
          <Stack direction="row" spacing={0.5} alignItems="center" flexWrap="wrap">
            <Chip 
              label={statusLabel}
              size="small"
              color={statusChipColor}
              sx={{
                height: '20px',
                fontWeight: 600,
              }}
            />
            {isLive && status === 'running' && (
              <Chip
                label="LIVE"
                size="small"
                color="error"
                data-testid="pipeline-live-indicator"
                sx={{ height: '20px', fontWeight: 600 }}
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
