import React, { useState, useRef, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Alert,
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Typography,
  Grid,
  Chip,
  Slider,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Paper,
  Divider,
  FormHelperText,
  LinearProgress,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Upload as UploadIcon,
  Close as CloseIcon,
  Person as PersonIcon,
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import { useCreateCharacter } from '../../hooks/useCharacters';
import { CharacterFormData, CharacterStats, Equipment } from '../../types';
import { useFocusTrap, announceToScreenReader } from '../../utils/focusManagement';

interface Props {
  open: boolean;
  onClose: () => void;
  onCharacterCreated: () => void;
}

interface ValidationErrors {
  [key: string]: string;
}

const FACTIONS = [
  'Imperial',
  'Chaos',
  'Ork',
  'Death Korps of Krieg',
  'Aeldari',
  'T\'au Empire',
  'Necrons',
  'Tyranids',
  'Other',
];

const ROLES = [
  'Guardsman',
  'Space Marine',
  'Tech-Priest',
  'Commissar',
  'Psyker',
  'Warboss',
  'Ork Boy',
  'Chaos Marine',
  'Cultist',
  'Civilian',
  'Other',
];

const EQUIPMENT_TYPES = [
  'weapon',
  'armor',
  'tool',
  'accessory',
  'special',
];

export default function CharacterCreationDialog({ open, onClose, onCharacterCreated }: Props) {
  const [formData, setFormData] = useState<CharacterFormData>({
    name: '',
    description: '',
    faction: '',
    role: '',
    stats: {
      strength: 5,
      dexterity: 5,
      intelligence: 5,
      willpower: 5,
      perception: 5,
      charisma: 5,
    },
    equipment: [],
    relationships: [],
  });

  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({});
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [newEquipment, setNewEquipment] = useState({
    name: '',
    type: 'weapon' as Equipment['type'],
    description: '',
    condition: 1.0,
  });
  const [showEquipmentForm, setShowEquipmentForm] = useState(false);
  
  // Focus management for accessibility
  const dialogRef = useRef<HTMLDivElement>(null);
  useFocusTrap(open, dialogRef, {
    onEscape: onClose,
    restoreFocus: true,
  });

  const createCharacter = useCreateCharacter();

  // File upload configuration
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
      'application/json': ['.json'],
      'text/yaml': ['.yaml', '.yml'],
    },
    maxFiles: 5,
    maxSize: 10 * 1024 * 1024, // 10MB
    onDrop: (acceptedFiles) => {
      setUploadedFiles(prev => [...prev, ...acceptedFiles]);
    },
    onDropRejected: (rejectedFiles) => {
      const error = rejectedFiles[0]?.errors[0];
      setValidationErrors(prev => ({
        ...prev,
        files: error?.message || 'File upload failed',
      }));
    },
  });

  const validateForm = (): boolean => {
    const errors: ValidationErrors = {};

    // Name validation
    if (!formData.name.trim()) {
      errors.name = 'Character name is required';
    } else if (formData.name.length < 3) {
      errors.name = 'Name must be at least 3 characters';
    } else if (formData.name.length > 50) {
      errors.name = 'Name must be less than 50 characters';
    } else if (!/^[a-zA-Z0-9_\s]+$/.test(formData.name)) {
      errors.name = 'Name can only contain letters, numbers, underscores, and spaces';
    }

    // Description validation
    if (!formData.description.trim()) {
      errors.description = 'Description is required';
    } else if (formData.description.length < 10) {
      errors.description = 'Description must be at least 10 characters';
    } else if (formData.description.length > 2000) {
      errors.description = 'Description must be less than 2000 characters';
    }

    // Faction validation
    if (!formData.faction) {
      errors.faction = 'Please select a faction';
    }

    // Role validation
    if (!formData.role.trim()) {
      errors.role = 'Character role is required';
    }

    // Stats validation
    Object.entries(formData.stats).forEach(([stat, value]) => {
      if (value < 1 || value > 10) {
        errors[stat] = `${stat} must be between 1 and 10`;
      }
    });

    // Total stats validation (reasonable range)
    const totalStats = Object.values(formData.stats).reduce((sum, val) => sum + val, 0);
    if (totalStats < 18 || totalStats > 60) {
      errors.statsTotal = 'Total stats should be between 18 and 60 for balanced characters';
    }

    // Equipment validation
    formData.equipment.forEach((item, index) => {
      if (!item.name.trim()) {
        errors[`equipment_${index}_name`] = 'Equipment name is required';
      }
      if (item.condition < 0 || item.condition > 1) {
        errors[`equipment_${index}_condition`] = 'Condition must be between 0 and 1';
      }
    });

    // File validation
    if (uploadedFiles.length > 5) {
      errors.files = 'Maximum 5 files allowed';
    }

    const totalFileSize = uploadedFiles.reduce((sum, file) => sum + file.size, 0);
    if (totalFileSize > 10 * 1024 * 1024) {
      errors.files = 'Total file size must be less than 10MB';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleStatChange = (stat: keyof CharacterStats, value: number) => {
    setFormData(prev => ({
      ...prev,
      stats: { ...prev.stats, [stat]: value },
    }));
    // Clear stat-specific errors
    if (validationErrors[stat]) {
      setValidationErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[stat];
        delete newErrors.statsTotal;
        return newErrors;
      });
    }
  };

  const addEquipment = () => {
    if (!newEquipment.name.trim()) return;

    const equipment: Equipment = {
      id: `eq_${Date.now()}`,
      ...newEquipment,
    };

    setFormData(prev => ({
      ...prev,
      equipment: [...prev.equipment, equipment],
    }));

    setNewEquipment({
      name: '',
      type: 'weapon',
      description: '',
      condition: 1.0,
    });
    setShowEquipmentForm(false);
  };

  const removeEquipment = (index: number) => {
    setFormData(prev => ({
      ...prev,
      equipment: prev.equipment.filter((_, i) => i !== index),
    }));
  };

  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      await createCharacter.mutateAsync({
        data: formData,
        files: uploadedFiles,
      });

      // Reset form
      setFormData({
        name: '',
        description: '',
        faction: '',
        role: '',
        stats: {
          strength: 5,
          dexterity: 5,
          intelligence: 5,
          willpower: 5,
          perception: 5,
          charisma: 5,
        },
        equipment: [],
        relationships: [],
      });
      setUploadedFiles([]);
      setValidationErrors({});

      onCharacterCreated();
      onClose();
    } catch (error) {
      // Error is handled by the mutation
    }
  };

  const handleClose = () => {
    if (!createCharacter.isLoading) {
      onClose();
    }
  };

  const totalStats = Object.values(formData.stats).reduce((sum, val) => sum + val, 0);
  const statsColor = totalStats < 18 ? 'error' : totalStats > 60 ? 'warning' : 'success';

  return (
    <Dialog 
      open={open} 
      onClose={handleClose} 
      maxWidth="md" 
      fullWidth
      ref={dialogRef}
      aria-labelledby="character-creation-title"
      aria-describedby="character-creation-description"
      PaperProps={{
        sx: { minHeight: '80vh' }
      }}
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <PersonIcon color="primary" />
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h5" component="div" sx={{ fontWeight: 600 }}>
            Create New Character
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Design a character for your stories with AI-enhanced profiles
          </Typography>
        </Box>
        <IconButton onClick={handleClose} disabled={createCharacter.isLoading}>
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      {createCharacter.isLoading && <LinearProgress />}

      <form onSubmit={handleSubmit}>
        <DialogContent sx={{ pb: 1 }}>
          {createCharacter.isError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {createCharacter.error?.message || 'Failed to create character'}
            </Alert>
          )}

          {/* Basic Information */}
          <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
            Basic Information
          </Typography>

          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                autoFocus
                fullWidth
                label="Character Name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                error={!!validationErrors.name}
                helperText={validationErrors.name || 'Use letters, numbers, underscores, and spaces'}
                disabled={createCharacter.isLoading}
              />
            </Grid>

            <Grid item xs={12} sm={3}>
              <FormControl fullWidth error={!!validationErrors.faction}>
                <InputLabel>Faction</InputLabel>
                <Select
                  value={formData.faction}
                  label="Faction"
                  onChange={(e) => setFormData({ ...formData, faction: e.target.value })}
                  disabled={createCharacter.isLoading}
                >
                  {FACTIONS.map((faction) => (
                    <MenuItem key={faction} value={faction}>
                      {faction}
                    </MenuItem>
                  ))}
                </Select>
                {validationErrors.faction && (
                  <FormHelperText>{validationErrors.faction}</FormHelperText>
                )}
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={3}>
              <TextField
                fullWidth
                label="Role"
                value={formData.role}
                onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                error={!!validationErrors.role}
                helperText={validationErrors.role}
                placeholder="e.g., Guardsman, Warboss"
                disabled={createCharacter.isLoading}
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={4}
                label="Character Description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                error={!!validationErrors.description}
                helperText={
                  validationErrors.description || 
                  `Describe your character's background and personality (${formData.description.length}/2000)`
                }
                disabled={createCharacter.isLoading}
              />
            </Grid>
          </Grid>

          <Divider sx={{ my: 3 }} />

          {/* Character Stats */}
          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Character Stats
              </Typography>
              <Chip
                label={`Total: ${totalStats}`}
                color={statsColor}
                variant="outlined"
                size="small"
              />
            </Box>

            {validationErrors.statsTotal && (
              <Alert severity="warning" sx={{ mb: 2 }}>
                {validationErrors.statsTotal}
              </Alert>
            )}

            <Grid container spacing={3}>
              {Object.entries(formData.stats).map(([stat, value]) => (
                <Grid item xs={12} sm={6} md={4} key={stat}>
                  <Box>
                    <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
                      {stat.charAt(0).toUpperCase() + stat.slice(1)}: {value}
                    </Typography>
                    <Slider
                      value={value}
                      onChange={(_, newValue) => handleStatChange(stat as keyof CharacterStats, newValue as number)}
                      min={1}
                      max={10}
                      step={1}
                      marks
                      valueLabelDisplay="auto"
                      disabled={createCharacter.isLoading}
                      color={validationErrors[stat] ? 'error' : 'primary'}
                    />
                    {validationErrors[stat] && (
                      <Typography variant="caption" color="error">
                        {validationErrors[stat]}
                      </Typography>
                    )}
                  </Box>
                </Grid>
              ))}
            </Grid>
          </Box>

          <Divider sx={{ my: 3 }} />

          {/* Equipment */}
          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Equipment ({formData.equipment.length})
              </Typography>
              <Button
                startIcon={<AddIcon />}
                onClick={() => setShowEquipmentForm(true)}
                variant="outlined"
                size="small"
                disabled={createCharacter.isLoading}
              >
                Add Equipment
              </Button>
            </Box>

            {showEquipmentForm && (
              <Paper sx={{ p: 2, mb: 2, bgcolor: 'action.hover' }}>
                <Grid container spacing={2} alignItems="end">
                  <Grid item xs={12} sm={4}>
                    <TextField
                      fullWidth
                      size="small"
                      label="Equipment Name"
                      value={newEquipment.name}
                      onChange={(e) => setNewEquipment({ ...newEquipment, name: e.target.value })}
                    />
                  </Grid>
                  <Grid item xs={12} sm={3}>
                    <FormControl fullWidth size="small">
                      <InputLabel>Type</InputLabel>
                      <Select
                        value={newEquipment.type}
                        label="Type"
                        onChange={(e) => setNewEquipment({ 
                          ...newEquipment, 
                          type: e.target.value as Equipment['type'] 
                        })}
                      >
                        {EQUIPMENT_TYPES.map((type) => (
                          <MenuItem key={type} value={type}>
                            {type.charAt(0).toUpperCase() + type.slice(1)}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12} sm={3}>
                    <TextField
                      fullWidth
                      size="small"
                      label="Description"
                      value={newEquipment.description}
                      onChange={(e) => setNewEquipment({ ...newEquipment, description: e.target.value })}
                    />
                  </Grid>
                  <Grid item xs={6} sm={1}>
                    <Button
                      fullWidth
                      variant="contained"
                      onClick={addEquipment}
                      disabled={!newEquipment.name.trim()}
                      size="small"
                    >
                      Add
                    </Button>
                  </Grid>
                  <Grid item xs={6} sm={1}>
                    <Button
                      fullWidth
                      variant="outlined"
                      onClick={() => setShowEquipmentForm(false)}
                      size="small"
                    >
                      Cancel
                    </Button>
                  </Grid>
                </Grid>
              </Paper>
            )}

            {formData.equipment.length > 0 ? (
              <List dense>
                {formData.equipment.map((item, index) => (
                  <ListItem key={item.id} divider>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                            {item.name}
                          </Typography>
                          <Chip label={item.type} size="small" variant="outlined" />
                          <Chip 
                            label={`${Math.round(item.condition * 100)}%`} 
                            size="small" 
                            color={item.condition > 0.7 ? 'success' : item.condition > 0.3 ? 'warning' : 'error'}
                          />
                        </Box>
                      }
                      secondary={item.description || 'No description'}
                    />
                    <ListItemSecondaryAction>
                      <IconButton
                        edge="end"
                        onClick={() => removeEquipment(index)}
                        size="small"
                        color="error"
                      >
                        <DeleteIcon />
                      </IconButton>
                    </ListItemSecondaryAction>
                  </ListItem>
                ))}
              </List>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                No equipment added yet. Click "Add Equipment" to get started.
              </Typography>
            )}
          </Box>

          <Divider sx={{ my: 3 }} />

          {/* File Upload */}
          <Box sx={{ mb: 2 }}>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
              Supporting Files (Optional)
            </Typography>

            <Paper
              {...getRootProps()}
              sx={{
                p: 3,
                border: '2px dashed',
                borderColor: isDragActive ? 'primary.main' : 'divider',
                bgcolor: isDragActive ? 'action.hover' : 'transparent',
                cursor: 'pointer',
                textAlign: 'center',
                transition: 'all 0.2s ease',
                '&:hover': {
                  borderColor: 'primary.main',
                  bgcolor: 'action.hover',
                },
              }}
            >
              <input {...getInputProps()} />
              <UploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
              <Typography variant="body1" sx={{ mb: 1 }}>
                {isDragActive
                  ? 'Drop files here...'
                  : 'Drag & drop character files, or click to browse'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Supports .txt, .md, .json, .yaml files (max 5 files, 10MB total)
              </Typography>
            </Paper>

            {validationErrors.files && (
              <Alert severity="error" sx={{ mt: 1 }}>
                {validationErrors.files}
              </Alert>
            )}

            {uploadedFiles.length > 0 && (
              <List dense sx={{ mt: 2 }}>
                {uploadedFiles.map((file, index) => (
                  <ListItem key={`${file.name}-${index}`} divider>
                    <ListItemText
                      primary={file.name}
                      secondary={`${(file.size / 1024).toFixed(1)} KB`}
                    />
                    <ListItemSecondaryAction>
                      <IconButton
                        edge="end"
                        onClick={() => removeFile(index)}
                        size="small"
                        color="error"
                      >
                        <DeleteIcon />
                      </IconButton>
                    </ListItemSecondaryAction>
                  </ListItem>
                ))}
              </List>
            )}
          </Box>
        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 3 }}>
          <Button 
            onClick={handleClose} 
            disabled={createCharacter.isLoading}
            size="large"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={createCharacter.isLoading}
            size="large"
            sx={{ minWidth: 120 }}
          >
            {createCharacter.isLoading ? 'Creating...' : 'Create Character'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}