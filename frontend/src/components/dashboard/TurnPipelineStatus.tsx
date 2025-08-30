import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Stack, 
  Chip, 
  LinearProgress, 
  Stepper,
  Step,
  StepLabel,
  StepContent,
  useTheme,
  List,
  ListItem,
  ListItemText,
  ListItemIcon
} from '@mui/material';
import { styled } from '@mui/material/styles';
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
}));

const StatusChip = styled(Chip)<{ status: string }>(({ theme, status }) => ({
  fontSize: '0.7rem',
  height: '20px',
  '& .MuiChip-label': {
    padding: '0 6px',
  },
  backgroundColor: 
    status === 'processing' ? theme.palette.info.light :
    status === 'completed' ? theme.palette.success.light :
    status === 'queued' ? theme.palette.warning.light :
    status === 'error' ? theme.palette.error.light :
    theme.palette.grey[300],
  color: 
    status === 'processing' ? theme.palette.info.contrastText :
    status === 'completed' ? theme.palette.success.contrastText :
    status === 'queued' ? theme.palette.warning.contrastText :
    status === 'error' ? theme.palette.error.contrastText :
    theme.palette.text.primary,
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
    switch (step.status) {
      case 'completed':
        return <CompleteIcon fontSize="small" color="success" />;
      case 'processing':
        return <ProcessingIcon fontSize="small" color="info" />;
      case 'error':
        return <ErrorIcon fontSize="small" color="error" />;
      default:
        return <QueueIcon fontSize="small" color="disabled" />;
    }
  };

  const currentStep = pipelineData.steps.findIndex(step => step.status === 'processing');

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
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Turn {pipelineData.currentTurn} of {pipelineData.totalTurns}
          </Typography>
          <Stack direction="row" spacing={0.5}>
            <Chip 
              label={`${pipelineData.queueLength} queued`} 
              size="small" 
              variant="outlined"
            />
            <Chip 
              label={`${pipelineData.averageProcessingTime}s avg`} 
              size="small" 
              variant="outlined"
            />
          </Stack>
        </Stack>

        <Box sx={{ flex: 1, overflowY: 'auto' }}>
          <List dense sx={{ py: 0 }}>
            {pipelineData.steps.map((step, index) => (
              <ListItem key={step.id} sx={{ py: 0.5, px: 0 }}>
                <ListItemIcon sx={{ minWidth: 28 }}>
                  {getStepIcon(step)}
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Stack direction="row" alignItems="center" spacing={1}>
                      <Typography variant="body2" fontWeight={500}>
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
                        <LinearProgress
                          variant="determinate"
                          value={step.progress}
                          sx={{ 
                            height: 3, 
                            borderRadius: 1.5,
                            mb: 0.5,
                            backgroundColor: theme.palette.action.hover,
                          }}
                        />
                      )}
                      <Stack direction="row" alignItems="center" spacing={1}>
                        {step.character && (
                          <Stack direction="row" alignItems="center" spacing={0.5}>
                            <CharacterIcon fontSize="small" />
                            <Typography variant="caption" color="text.secondary">
                              {step.character}
                            </Typography>
                          </Stack>
                        )}
                        {step.duration && (
                          <Typography variant="caption" color="text.secondary">
                            {step.duration.toFixed(1)}s
                          </Typography>
                        )}
                        {step.status === 'processing' && (
                          <Typography variant="caption" color="text.secondary">
                            {step.progress.toFixed(0)}%
                          </Typography>
                        )}
                      </Stack>
                    </Box>
                  }
                />
              </ListItem>
            ))}
          </List>
        </Box>
      </PipelineContainer>
    </GridTile>
  );
};

export default TurnPipelineStatus;