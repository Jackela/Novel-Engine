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
import { styled } from '@mui/material/styles';
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

const StageItem = styled(motion(ListItem))<{ status: string }>(({ theme, status }) => ({
  padding: theme.spacing(1, 0),
  borderBottom: `1px solid #2a2a30`,
  borderLeft: `3px solid ${
    status === 'processing' ? '#6366f1' :
    status === 'completed' ? '#10b981' :
    status === 'error' ? '#ef4444' :
    '#808088'
  }`,
  paddingLeft: theme.spacing(1),
  borderRadius: theme.shape.borderRadius / 2,
  marginBottom: theme.spacing(0.5),
  background: status === 'processing' ? 'rgba(99, 102, 241, 0.05)' : 'transparent',
  transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
  '&:hover': {
    background: status === 'processing' ? 'rgba(99, 102, 241, 0.1)' : '#1a1a1d',
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
    status === 'processing' ? 'rgba(99, 102, 241, 0.2)' :
    status === 'completed' ? 'rgba(16, 185, 129, 0.2)' :
    status === 'queued' ? 'rgba(245, 158, 11, 0.2)' :
    status === 'error' ? 'rgba(239, 68, 68, 0.2)' :
    'transparent',
  color: 
    status === 'processing' ? '#6366f1' :
    status === 'completed' ? '#10b981' :
    status === 'queued' ? '#f59e0b' :
    status === 'error' ? '#ef4444' :
    '#b0b0b8',
  border: `1px solid ${
    status === 'processing' ? '#6366f1' :
    status === 'completed' ? '#10b981' :
    status === 'queued' ? '#f59e0b' :
    status === 'error' ? '#ef4444' :
    '#3a3a42'
  }`,
}));

const AnimatedProgress = styled(motion(LinearProgress))(({ theme }) => ({
  height: 4,
  borderRadius: 2,
  backgroundColor: '#2a2a30',
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
}

const TurnPipelineStatus: React.FC<TurnPipelineStatusProps> = ({ loading, error }) => {
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
        return <CompleteIcon {...iconProps} sx={{ color: '#10b981' }} />;
      case 'processing':
        return <ProcessingIcon {...iconProps} sx={{ color: '#6366f1' }} />;
      case 'error':
        return <ErrorIcon {...iconProps} sx={{ color: '#ef4444' }} />;
      default:
        return <QueueIcon {...iconProps} sx={{ color: '#808088' }} />;
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
            <Chip 
              label={`${pipelineData.queueLength} queued`} 
              size="small" 
              sx={{
                backgroundColor: '#111113',
                borderColor: '#2a2a30',
                color: '#b0b0b8',
                fontSize: '0.65rem',
                height: '20px',
              }}
            />
            <Chip 
              label={`${pipelineData.averageProcessingTime.toFixed(1)}s avg`} 
              size="small" 
              sx={{
                backgroundColor: '#111113',
                borderColor: '#2a2a30',
                color: '#b0b0b8',
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
                            sx={{ color: '#f0f0f2' }}
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
                                <CharacterIcon sx={{ fontSize: '14px', color: '#6366f1' }} />
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
