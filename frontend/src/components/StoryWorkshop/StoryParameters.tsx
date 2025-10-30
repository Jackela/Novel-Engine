import React from 'react';
import {
  Box,
  Grid,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Typography,
  Slider,
  Paper,
  Chip,
  Alert,
  Divider,
  Card,
  CardContent,
} from '@mui/material';
import {
  AutoStories as StoryIcon,
  Settings as SettingsIcon,
  Group as GroupIcon,
} from '@mui/icons-material';
import type { StoryFormData } from '../../types';

interface Props {
  parameters: StoryFormData;
  onParametersChange: (parameters: StoryFormData) => void;
  selectedCharacters: string[];
}

const NARRATIVE_STYLES = [
  { value: 'action', label: 'Action-Packed', description: 'Fast-paced with emphasis on combat and conflict' },
  { value: 'dialogue', label: 'Dialogue-Heavy', description: 'Character conversations and interactions' },
  { value: 'balanced', label: 'Balanced', description: 'Mix of action, dialogue, and description' },
  { value: 'descriptive', label: 'Descriptive', description: 'Rich environmental and character descriptions' },
];

const TONES = [
  { value: 'dark', label: 'Dark', description: 'Gritty, serious, and dramatic' },
  { value: 'heroic', label: 'Heroic', description: 'Noble, inspiring, and uplifting' },
  { value: 'comedy', label: 'Comedy', description: 'Light-hearted and humorous' },
  { value: 'neutral', label: 'Neutral', description: 'Balanced tone without extremes' },
];

const PERSPECTIVES = [
  { value: 'first_person', label: 'First Person', description: 'Written from a character\'s perspective using "I"' },
  { value: 'third_person', label: 'Third Person', description: 'Written from an outside perspective using "he/she/they"' },
];

export default function StoryParameters({
  parameters,
  onParametersChange,
  selectedCharacters,
}: Props) {
  const updateParameters = (updates: Partial<StoryFormData>) => {
    onParametersChange({ ...parameters, ...updates });
  };

  const updateSettings = (updates: Partial<StoryFormData['settings']>) => {
    onParametersChange({
      ...parameters,
      settings: { ...parameters.settings, ...updates },
    });
  };

  const estimatedWordCount = parameters.settings.turns * parameters.settings.maxWordsPerTurn;
  const estimatedReadingTime = Math.ceil(estimatedWordCount / 200); // ~200 words per minute

  return (
    <Box>
      {/* Basic Story Information */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
          Story Details
        </Typography>
        
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Story Title"
              value={parameters.title}
              onChange={(e) => updateParameters({ title: e.target.value })}
              placeholder="Enter a compelling title for your story"
              helperText="A clear, engaging title that captures the essence of your story"
            />
          </Grid>
          
          <Grid item xs={12}>
            <TextField
              fullWidth
              multiline
              rows={3}
              label="Story Description"
              value={parameters.description}
              onChange={(e) => updateParameters({ description: e.target.value })}
              placeholder="Describe the story you want to create..."
              helperText="Provide context and background that will guide the AI in generating your story"
            />
          </Grid>
        </Grid>
      </Box>

      <Divider sx={{ my: 3 }} />

      {/* Generation Settings */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
          Generation Settings
        </Typography>
        
        <Grid container spacing={3}>
          {/* Story Length */}
          <Grid item xs={12} md={6}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 600 }}>
                  Story Length
                </Typography>
                
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    Number of turns: {parameters.settings.turns}
                  </Typography>
                  <Slider
                    value={parameters.settings.turns}
                    onChange={(_, value) => updateSettings({ turns: value as number })}
                    min={3}
                    max={20}
                    step={1}
                    marks={[
                      { value: 3, label: '3' },
                      { value: 10, label: '10' },
                      { value: 20, label: '20' },
                    ]}
                    valueLabelDisplay="auto"
                  />
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    Max words per turn: {parameters.settings.maxWordsPerTurn}
                  </Typography>
                  <Slider
                    value={parameters.settings.maxWordsPerTurn}
                    onChange={(_, value) => updateSettings({ maxWordsPerTurn: value as number })}
                    min={50}
                    max={500}
                    step={25}
                    marks={[
                      { value: 50, label: '50' },
                      { value: 200, label: '200' },
                      { value: 500, label: '500' },
                    ]}
                    valueLabelDisplay="auto"
                  />
                </Box>

                <Paper sx={{ p: 2, bgcolor: 'action.hover' }}>
                  <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
                    Estimated Output
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    • {estimatedWordCount.toLocaleString()} words total
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    • ~{estimatedReadingTime} minute read
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    • {parameters.settings.turns} character turns
                  </Typography>
                </Paper>
              </CardContent>
            </Card>
          </Grid>

          {/* Style Settings */}
          <Grid item xs={12} md={6}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 600 }}>
                  Writing Style
                </Typography>
                
                <Box sx={{ mb: 3 }}>
                  <FormControl fullWidth>
                    <InputLabel>Narrative Style</InputLabel>
                    <Select
                      value={parameters.settings.narrativeStyle}
                      label="Narrative Style"
                      onChange={(e) => updateSettings({ narrativeStyle: e.target.value as unknown as 'epic' | 'detailed' | 'concise' })}
                    >
                      {NARRATIVE_STYLES.map((style) => (
                        <MenuItem key={style.value} value={style.value}>
                          {style.label}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                    {NARRATIVE_STYLES.find(s => s.value === parameters.settings.narrativeStyle)?.description}
                  </Typography>
                </Box>

                <Box sx={{ mb: 3 }}>
                  <FormControl fullWidth>
                    <InputLabel>Tone</InputLabel>
                    <Select
                      value={parameters.settings.tone}
                      label="Tone"
                      onChange={(e) => updateSettings({ tone: e.target.value as unknown as 'grimdark' | 'heroic' | 'tactical' | 'dramatic' })}
                    >
                      {TONES.map((tone) => (
                        <MenuItem key={tone.value} value={tone.value}>
                          {tone.label}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                    {TONES.find(t => t.value === parameters.settings.tone)?.description}
                  </Typography>
                </Box>

                <Box>
                  <FormControl fullWidth>
                    <InputLabel>Perspective</InputLabel>
                    <Select
                      value={parameters.settings.perspective}
                      label="Perspective"
                      onChange={(e) => updateSettings({ perspective: e.target.value as unknown as 'first_person' | 'third_person' })}
                    >
                      {PERSPECTIVES.map((perspective) => (
                        <MenuItem key={perspective.value} value={perspective.value}>
                          {perspective.label}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                    {PERSPECTIVES.find(p => p.value === parameters.settings.perspective)?.description}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>

      <Divider sx={{ my: 3 }} />

      {/* Optional Scenario */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
          Story Direction (Optional)
        </Typography>
        
        <TextField
          fullWidth
          multiline
          rows={4}
          label="Scenario or Prompt"
          value={parameters.settings.scenario}
          onChange={(e) => updateSettings({ scenario: e.target.value })}
          placeholder="Describe the initial situation, setting, or conflict to guide the story..."
          helperText="Provide specific details about the scenario, setting, or situation you want the story to explore"
        />
      </Box>

      <Divider sx={{ my: 3 }} />

      {/* Selected Characters Summary */}
      <Box>
        <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
          Story Participants
        </Typography>
        
        <Paper sx={{ p: 3, bgcolor: 'action.hover' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
            <GroupIcon color="primary" />
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
              Selected Characters ({selectedCharacters.length})
            </Typography>
          </Box>
          
          {selectedCharacters.length > 0 ? (
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {selectedCharacters.map((character, index) => (
                <Chip
                  key={character}
                  label={`${index + 1}. ${character.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}`}
                  color="primary"
                  variant="outlined"
                />
              ))}
            </Box>
          ) : (
            <Alert severity="warning">
              No characters selected. Return to the previous step to select characters.
            </Alert>
          )}

          {selectedCharacters.length > 0 && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" color="text.secondary">
                These characters will take turns advancing the story based on their personalities and the parameters you've set.
                The AI will maintain character consistency while creating engaging interactions between them.
              </Typography>
            </Box>
          )}
        </Paper>
      </Box>

      {/* Validation Messages */}
      <Box sx={{ mt: 3 }}>
        {!parameters.title.trim() && (
          <Alert severity="error" sx={{ mb: 1 }}>
            Story title is required to proceed with generation.
          </Alert>
        )}
        
        {!parameters.description.trim() && (
          <Alert severity="error" sx={{ mb: 1 }}>
            Story description is required to guide the AI generation.
          </Alert>
        )}
        
        {selectedCharacters.length < 2 && (
          <Alert severity="error" sx={{ mb: 1 }}>
            At least 2 characters are required for story generation.
          </Alert>
        )}

        {parameters.title.trim() && parameters.description.trim() && selectedCharacters.length >= 2 && (
          <Alert severity="success">
            All requirements met! You can proceed to generate your story.
          </Alert>
        )}
      </Box>
    </Box>
  );
}
