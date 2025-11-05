import React, { useState, useEffect } from 'react';
import { logger } from '../services/logging/LoggerFactory';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Stepper,
  Step,
  StepLabel,
  Alert,
  Paper,
  CircularProgress,
  Divider,
  Chip,
  IconButton,
  Tooltip,
  LinearProgress,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Refresh as RefreshIcon,
  Save as SaveIcon,
  Download as DownloadIcon,
  Settings as SettingsIcon,
  AutoStories as StoryIcon,
  Group as GroupIcon,
  Tune as TuneIcon,
} from '@mui/icons-material';
import { useMutation } from 'react-query';
import api from '../../services/api';
import CharacterSelectionContainer from './CharacterSelectionContainer';
import StoryParameters from './StoryParameters';
import GenerationProgress from './GenerationProgress';
import StoryDisplay from './StoryDisplay';
import type { StoryFormData, StoryProject } from '../../types';

const WORKSHOP_STEPS = [
  'Select Characters',
  'Configure Story',
  'Generate Content',
  'Review & Edit',
];

interface GenerationState {
  isGenerating: boolean;
  progress: number;
  currentStage: string;
  estimatedTimeRemaining: number;
  error: string | null;
  generationId?: string | null;
}

export default function StoryWorkshop() {
  const [activeStep, setActiveStep] = useState(0);
  const [selectedCharacters, setSelectedCharacters] = useState<string[]>([]);
  const [storyParameters, setStoryParameters] = useState({
    title: '',
    description: '',
    settings: {
      turns: 5,
      narrativeStyle: 'balanced' as const,
      tone: 'neutral' as const,
      perspective: 'third_person' as const,
      maxWordsPerTurn: 200,
      scenario: '',
    },
  });
  const [generatedStory, setGeneratedStory] = useState<StoryProject | null>(null);
  const [generationState, setGenerationState] = useState<GenerationState>({
    isGenerating: false,
    progress: 0,
    currentStage: '',
    estimatedTimeRemaining: 0,
    error: null,
    generationId: null,
  });

  // Characters are provided via container using shared query hooks

  // Story generation mutation
  const generateStoryMutation = useMutation(
    (storyData: StoryFormData) => api.runSimulation(storyData),
    {
      onMutate: () => {
        setGenerationState({
          isGenerating: true,
          progress: 0,
          currentStage: 'Initializing story generation...',
          estimatedTimeRemaining: 120, // 2 minutes estimate
          error: null,
          generationId: null, // Will be set from response
        });
        setActiveStep(2); // Move to generation step
      },
      onSuccess: (response) => {
        setGeneratedStory(response.data);
        setGenerationState({
          isGenerating: false,
          progress: 100,
          currentStage: 'Story generation completed',
          estimatedTimeRemaining: 0,
          error: null,
          generationId: response.generation_id || null,
        });
        setActiveStep(3); // Move to review step
      },
      onError: (error: Error) => {
        setGenerationState(prev => ({
          ...prev,
          isGenerating: false,
          error: error.message,
        }));
      },
    }
  );

  // Simulate progress updates during generation
  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (generationState.isGenerating) {
      interval = setInterval(() => {
        setGenerationState(prev => {
          if (prev.progress >= 95) return prev; // Don't go to 100% until actually complete
          
          const increment = Math.random() * 5 + 2; // 2-7% increments
          const newProgress = Math.min(prev.progress + increment, 95);
          
          // Update stage based on progress
          let currentStage = prev.currentStage;
          let timeRemaining = prev.estimatedTimeRemaining - 3; // Decrease by 3 seconds
          
          if (newProgress < 20) {
            currentStage = 'Analyzing character personalities...';
          } else if (newProgress < 40) {
            currentStage = 'Planning narrative structure...';
          } else if (newProgress < 60) {
            currentStage = 'Generating story turns...';
          } else if (newProgress < 80) {
            currentStage = 'Coordinating character interactions...';
          } else {
            currentStage = 'Finalizing story content...';
          }
          
          return {
            ...prev,
            progress: newProgress,
            currentStage,
            estimatedTimeRemaining: Math.max(timeRemaining, 5),
          };
        });
      }, 3000); // Update every 3 seconds
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [generationState.isGenerating]);

  const canProceedToNext = () => {
    switch (activeStep) {
      case 0:
        return selectedCharacters.length >= 2 && selectedCharacters.length <= 6;
      case 1:
        return storyParameters.title.trim() !== '' && storyParameters.description.trim() !== '';
      case 2:
        return !generationState.isGenerating;
      default:
        return true;
    }
  };

  const handleNext = () => {
    if (activeStep === 1 && canProceedToNext()) {
      // Start story generation
      const storyData: StoryFormData = {
        title: storyParameters.title,
        description: storyParameters.description,
        characters: selectedCharacters,
        settings: storyParameters.settings,
      };
      generateStoryMutation.mutate(storyData);
    } else if (canProceedToNext()) {
      setActiveStep(prev => Math.min(prev + 1, WORKSHOP_STEPS.length - 1));
    }
  };

  const handleBack = () => {
    if (!generationState.isGenerating) {
      setActiveStep(prev => Math.max(prev - 1, 0));
    }
  };

  const handleReset = () => {
    setActiveStep(0);
    setSelectedCharacters([]);
    setStoryParameters({
      title: '',
      description: '',
      settings: {
        turns: 5,
        narrativeStyle: 'balanced',
        tone: 'neutral',
        perspective: 'third_person',
        maxWordsPerTurn: 200,
        scenario: '',
      },
    });
    setGeneratedStory(null);
    setGenerationState({
      isGenerating: false,
      progress: 0,
      currentStage: '',
      estimatedTimeRemaining: 0,
      error: null,
    });
  };

  const handleStopGeneration = () => {
    // TODO: Implement API call cancellation
    setGenerationState(prev => ({
      ...prev,
      isGenerating: false,
      error: 'Generation stopped by user',
    }));
  };

  const handleSaveStory = () => {
    if (generatedStory) {
      // TODO: Implement story saving to library
      logger.info('Saving story:', generatedStory);
    }
  };

  const handleExportStory = () => {
    if (generatedStory) {
      const storyText = generatedStory.storyContent || 'No content available';
      const blob = new Blob([storyText], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${generatedStory.title.replace(/[^a-z0-9]/gi, '_')}.txt`;
      link.click();
      URL.revokeObjectURL(url);
    }
  };

  return (
    <Box sx={{ maxWidth: 1400, mx: 'auto' }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h3" component="h1" sx={{ mb: 1, fontWeight: 700 }}>
          Story Workshop
        </Typography>
        <Typography variant="h6" color="text.secondary" sx={{ mb: 3 }}>
          Create compelling stories through AI-powered character interactions
        </Typography>

        {/* Progress Stepper */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Stepper activeStep={activeStep} alternativeLabel>
            {WORKSHOP_STEPS.map((label, index) => (
              <Step key={label}>
                <StepLabel
                  sx={{
                    '& .MuiStepLabel-label': {
                      fontWeight: activeStep === index ? 600 : 400,
                    },
                  }}
                >
                  {label}
                </StepLabel>
              </Step>
            ))}
          </Stepper>
        </Paper>

        {/* Action Buttons */}
        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={handleReset}
            disabled={generationState.isGenerating}
          >
            Start Over
          </Button>
          
          {activeStep > 0 && (
            <Button
              variant="outlined"
              onClick={handleBack}
              disabled={generationState.isGenerating}
            >
              Back
            </Button>
          )}
          
          {activeStep < WORKSHOP_STEPS.length - 1 && (
            <Button
              variant="contained"
              startIcon={activeStep === 1 ? <PlayIcon /> : undefined}
              onClick={handleNext}
              disabled={!canProceedToNext() || generationState.isGenerating}
              size="large"
            >
              {activeStep === 1 ? 'Generate Story' : 'Next'}
            </Button>
          )}

          {generationState.isGenerating && (
            <Button
              variant="outlined"
              color="error"
              startIcon={<StopIcon />}
              onClick={handleStopGeneration}
            >
              Stop Generation
            </Button>
          )}

          {generatedStory && activeStep === 3 && (
            <>
              <Button
                variant="outlined"
                startIcon={<SaveIcon />}
                onClick={handleSaveStory}
              >
                Save to Library
              </Button>
              <Button
                variant="contained"
                startIcon={<DownloadIcon />}
                onClick={handleExportStory}
              >
                Export Story
              </Button>
            </>
          )}
        </Box>
      </Box>

      {/* Step Content */}
      <Grid container spacing={3}>
        {/* Main Content */}
        <Grid item xs={12} lg={8}>
          {/* Step 0: Character Selection */}
          {activeStep === 0 && (
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                  <GroupIcon color="primary" sx={{ fontSize: 32 }} />
                  <Box>
                    <Typography variant="h5" sx={{ fontWeight: 600 }}>
                      Select Characters
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Choose 2-6 characters to participate in your story
                    </Typography>
                  </Box>
                </Box>

                <CharacterSelectionContainer
                  selectedCharacters={selectedCharacters}
                  onSelectionChange={setSelectedCharacters}
                />

                {selectedCharacters.length > 0 && (
                  <Box sx={{ mt: 3, p: 2, bgcolor: 'action.hover', borderRadius: 1 }}>
                    <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                      Selected Characters ({selectedCharacters.length})
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                      {selectedCharacters.map((character) => (
                        <Chip
                          key={character}
                          label={character}
                          onDelete={() => setSelectedCharacters(prev => 
                            prev.filter(c => c !== character)
                          )}
                          color="primary"
                          variant="outlined"
                        />
                      ))}
                    </Box>
                  </Box>
                )}
              </CardContent>
            </Card>
          )}

          {/* Step 1: Story Parameters */}
          {activeStep === 1 && (
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                  <TuneIcon color="primary" sx={{ fontSize: 32 }} />
                  <Box>
                    <Typography variant="h5" sx={{ fontWeight: 600 }}>
                      Configure Story
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Set up the parameters for your story generation
                    </Typography>
                  </Box>
                </Box>

                <StoryParameters
                  parameters={storyParameters}
                  onParametersChange={setStoryParameters}
                  selectedCharacters={selectedCharacters}
                />
              </CardContent>
            </Card>
          )}

          {/* Step 2: Generation Progress */}
          {activeStep === 2 && (
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                  <StoryIcon color="primary" sx={{ fontSize: 32 }} />
                  <Box>
                    <Typography variant="h5" sx={{ fontWeight: 600 }}>
                      Generating Story
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      AI agents are creating your story with the selected characters
                    </Typography>
                  </Box>
                </Box>

                <GenerationProgress
                  isGenerating={generationState.isGenerating}
                  progress={generationState.progress}
                  currentStage={generationState.currentStage}
                  estimatedTimeRemaining={generationState.estimatedTimeRemaining}
                  error={generationState.error}
                  generationId={generationState.generationId}
                  enableRealTimeUpdates={true}
                />

                {generationState.error && (
                  <Alert severity="error" sx={{ mt: 2 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                      Generation Failed
                    </Typography>
                    <Typography variant="body2">
                      {generationState.error}
                    </Typography>
                  </Alert>
                )}
              </CardContent>
            </Card>
          )}

          {/* Step 3: Story Display */}
          {activeStep === 3 && generatedStory && (
            <StoryDisplay
              story={generatedStory}
              onEdit={(updatedStory) => setGeneratedStory(updatedStory)}
            />
          )}
        </Grid>

        {/* Sidebar */}
        <Grid item xs={12} lg={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                Workshop Status
              </Typography>

              {/* Current Progress */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  Current Step: {WORKSHOP_STEPS[activeStep]}
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={(activeStep / (WORKSHOP_STEPS.length - 1)) * 100}
                  sx={{ height: 8, borderRadius: 1 }}
                />
              </Box>

              <Divider sx={{ my: 2 }} />

              {/* Story Information */}
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                  Story Information
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  <strong>Title:</strong> {storyParameters.title || 'Not set'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  <strong>Characters:</strong> {selectedCharacters.length}/6 selected
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  <strong>Turns:</strong> {storyParameters.settings.turns}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  <strong>Style:</strong> {storyParameters.settings.narrativeStyle}
                </Typography>
              </Box>

              {generatedStory && (
                <>
                  <Divider sx={{ my: 2 }} />
                  <Box>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                      Generated Story Stats
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      <strong>Word Count:</strong> {generatedStory.metadata?.wordCount || 'Unknown'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      <strong>Generation Time:</strong> {generatedStory.metadata?.generationTime || 'Unknown'}s
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      <strong>Participants:</strong> {generatedStory.metadata?.participantCount || 'Unknown'}
                    </Typography>
                  </Box>
                </>
              )}

              <Divider sx={{ my: 2 }} />

              {/* Tips */}
              <Box>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                  Tips
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.875rem' }}>
                  • Select characters with interesting dynamics
                  • Try different narrative styles for varied results
                  • Use the scenario field to guide the story direction
                  • Higher turn counts create longer, more detailed stories
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
