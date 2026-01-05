import React, { useEffect, useState, useRef } from 'react';
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
  CircularProgress,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Upload as UploadIcon,
  Close as CloseIcon,
  Person as PersonIcon,
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import { useCreateCharacter, useUpdateCharacter } from '@/hooks/useCharacters';
import type { CharacterFormData, CharacterStats, Equipment } from '@/types';
import { useFocusTrap } from '@/utils/focusManagement';

interface Props {
  open: boolean;
  onClose: () => void;
  onCharacterCreated: () => void;
  mode?: 'create' | 'edit';
  characterId?: string;
  initialData?: CharacterFormData;
}

interface ValidationErrors {
  [key: string]: string;
}

const FACTIONS = [
  'Alliance Network',
  'Entropy Cult',
  'Freewind Collective',
  'Bastion Cohort',
  'Starborne Conclave',
  'Harmonic Assembly',
  'Synthetic Vanguard',
  'Adaptive Swarm',
  'Other',
];

const EQUIPMENT_TYPES = [
  'weapon',
  'armor',
  'tool',
  'accessory',
  'special',
];

const createInitialFormData = (): CharacterFormData => ({
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

const createTestFillData = (): CharacterFormData => ({
  ...createInitialFormData(),
  name: 'Test Operative',
  description: 'Automated test character.',
  faction: 'Freewind Collective',
  role: 'Tester',
});

const getStatsTotal = (stats: CharacterStats) =>
  Object.values(stats).reduce((sum, val) => sum + val, 0);

const getStatsColor = (totalStats: number) =>
  totalStats < 18 ? 'error' : totalStats > 60 ? 'warning' : 'success';

const getCharacterErrorMessage = (mode: 'create' | 'edit', errorMessage?: string) =>
  errorMessage || (mode === 'edit' ? 'Failed to update character' : 'Failed to create character');

const createFormValidator =
  (
    formData: CharacterFormData,
    uploadedFiles: File[],
    setValidationErrors: React.Dispatch<React.SetStateAction<ValidationErrors>>
  ) =>
  () => {
    const errors = validateCharacterForm(formData, uploadedFiles);
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

const createFileAppendHandler =
  (setUploadedFiles: React.Dispatch<React.SetStateAction<File[]>>) =>
  (acceptedFiles: File[]) => {
    setUploadedFiles((prev) => [...prev, ...acceptedFiles]);
  };

const createFileErrorHandler =
  (setValidationErrors: React.Dispatch<React.SetStateAction<ValidationErrors>>) =>
  (message: string) => {
    setValidationErrors((prev) => ({
      ...prev,
      files: message,
    }));
  };

const createSubmitHandler = (params: {
  mode: 'create' | 'edit';
  characterId?: string;
  formData: CharacterFormData;
  uploadedFiles: File[];
  validateForm: () => boolean;
  createCharacter: ReturnType<typeof useCreateCharacter>;
  updateCharacter: ReturnType<typeof useUpdateCharacter>;
  resetForm: () => void;
  onCharacterCreated: () => void;
  onClose: () => void;
}) => async (event: React.FormEvent) => {
  event.preventDefault();

  if (!params.validateForm()) {
    return;
  }

  try {
    if (params.mode === 'edit') {
      if (!params.characterId) {
        throw new Error('Missing character id for edit');
      }
      await params.updateCharacter.mutateAsync({
        characterId: params.characterId,
        data: params.formData,
        files: params.uploadedFiles,
      });
    } else {
      await params.createCharacter.mutateAsync({
        data: params.formData,
        files: params.uploadedFiles,
      });
    }

    if (params.mode === 'create') {
      params.resetForm();
    }

    params.onCharacterCreated();
    params.onClose();
  } catch {
    // Error is handled by the mutation
  }
};

const createCloseHandler = (isLoading: boolean, onClose: () => void) => () => {
  if (!isLoading) {
    onClose();
  }
};

const createTestFillHandler =
  (setFormData: React.Dispatch<React.SetStateAction<CharacterFormData>>) => () => {
    setFormData(createTestFillData());
  };

const useCharacterDialogFocus = (open: boolean, onClose: () => void) => {
  const dialogRef = useRef<HTMLDivElement>(null);
  useFocusTrap(open, dialogRef, {
    onEscape: onClose,
    restoreFocus: true,
  });

  return dialogRef;
};

const useCharacterMutationState = (mode: 'create' | 'edit', initialData?: CharacterFormData) => {
  const createCharacter = useCreateCharacter();
  const updateCharacter = useUpdateCharacter();
  const characterMutation = mode === 'edit' ? updateCharacter : createCharacter;
  const isBootstrappingEdit = mode === 'edit' && !initialData;

  return {
    createCharacter,
    updateCharacter,
    characterMutation,
    isBootstrappingEdit,
  };
};

const validateCharacterForm = (formData: CharacterFormData, uploadedFiles: File[]) => {
  const errors: ValidationErrors = {};

  if (!formData.name.trim()) {
    errors.name = 'Character name is required';
  } else if (formData.name.length < 3) {
    errors.name = 'Name must be at least 3 characters';
  } else if (formData.name.length > 50) {
    errors.name = 'Name must be less than 50 characters';
  } else if (!/^[a-zA-Z0-9_\s]+$/.test(formData.name)) {
    errors.name = 'Name can only contain letters, numbers, underscores, and spaces';
  }

  if (!formData.description.trim()) {
    errors.description = 'Description is required';
  } else if (formData.description.length < 10) {
    errors.description = 'Description must be at least 10 characters';
  } else if (formData.description.length > 2000) {
    errors.description = 'Description must be less than 2000 characters';
  }

  if (!formData.faction) {
    errors.faction = 'Please select a faction';
  }

  if (!formData.role.trim()) {
    errors.role = 'Character role is required';
  }

  Object.entries(formData.stats).forEach(([stat, value]) => {
    if (value < 1 || value > 10) {
      errors[stat] = `${stat} must be between 1 and 10`;
    }
  });

  const totalStats = getStatsTotal(formData.stats);
  if (totalStats < 18 || totalStats > 60) {
    errors.statsTotal = 'Total stats should be between 18 and 60 for balanced characters';
  }

  formData.equipment.forEach((item, index) => {
    if (!item.name.trim()) {
      errors[`equipment_${index}_name`] = 'Equipment name is required';
    }
    if (item.condition < 0 || item.condition > 1) {
      errors[`equipment_${index}_condition`] = 'Condition must be between 0 and 1';
    }
  });

  if (uploadedFiles.length > 5) {
    errors.files = 'Maximum 5 files allowed';
  }

  const totalFileSize = uploadedFiles.reduce((sum, file) => sum + file.size, 0);
  if (totalFileSize > 10 * 1024 * 1024) {
    errors.files = 'Total file size must be less than 10MB';
  }

  return errors;
};

const CharacterDialogHeader: React.FC<{
  mode: 'create' | 'edit';
  isLoading: boolean;
  onClose: () => void;
}> = ({ mode, isLoading, onClose }) => (
  <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
    <PersonIcon color="primary" />
    <Box sx={{ flexGrow: 1 }}>
      <Typography variant="h5" component="div" sx={{ fontWeight: 600 }}>
        {mode === 'edit' ? 'Edit Character' : 'Create New Character'}
      </Typography>
      <Typography variant="body2" color="text.secondary">
        {mode === 'edit'
          ? 'Update this character in your workspace'
          : 'Design a character for your stories with AI-enhanced profiles'}
      </Typography>
    </Box>
    <IconButton onClick={onClose} disabled={isLoading}>
      <CloseIcon />
    </IconButton>
  </DialogTitle>
);

const CharacterTestHelper: React.FC<{ onFill: () => void }> = ({ onFill }) => (
  <Box sx={{ px: 3, py: 1 }}>
    <Button
      size="small"
      variant="outlined"
      color="warning"
      onClick={onFill}
      data-testid="quick-fill-btn"
    >
      Quick Fill (Test)
    </Button>
  </Box>
);

const CharacterBootstrapping: React.FC<{ onCancel: () => void }> = ({ onCancel }) => (
  <>
    <DialogContent
      sx={{
        py: 6,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
        gap: 2,
      }}
    >
      <CircularProgress />
      <Typography variant="body2" color="text.secondary">
        Loading character…
      </Typography>
    </DialogContent>
    <DialogActions sx={{ px: 3, pb: 3 }}>
      <Button onClick={onCancel} size="large">
        Cancel
      </Button>
    </DialogActions>
  </>
);

const CharacterFormActions: React.FC<{
  isLoading: boolean;
  mode: 'create' | 'edit';
  onCancel: () => void;
}> = ({ isLoading, mode, onCancel }) => (
  <DialogActions sx={{ px: 3, pb: 3 }}>
    <Button onClick={onCancel} disabled={isLoading} size="large">
      Cancel
    </Button>
    <Button
      type="submit"
      variant="contained"
      disabled={isLoading}
      size="large"
      sx={{ minWidth: 120 }}
    >
      {isLoading
        ? mode === 'edit'
          ? 'Saving...'
          : 'Creating...'
        : mode === 'edit'
          ? 'Save Changes'
          : 'Create Character'}
    </Button>
  </DialogActions>
);

const CharacterBasicInfo: React.FC<{
  formData: CharacterFormData;
  validationErrors: ValidationErrors;
  isLoading: boolean;
  mode: 'create' | 'edit';
  setFormData: React.Dispatch<React.SetStateAction<CharacterFormData>>;
}> = ({ formData, validationErrors, isLoading, mode, onFormChange }) => (
  <>
    <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
      Basic Information
    </Typography>

    <Grid container spacing={2} sx={{ mb: 3 }}>
      <Grid item xs={12} sm={6}>
        <TextField
          fullWidth
          label="Character Name"
          value={formData.name}
          onChange={(event) => onFormChange({ ...formData, name: event.target.value })}
          error={!!validationErrors.name}
          helperText={validationErrors.name || 'Use letters, numbers, underscores, and spaces'}
          disabled={isLoading || mode === 'edit'}
        />
      </Grid>

      <Grid item xs={12} sm={3}>
        <FormControl fullWidth error={!!validationErrors.faction}>
          <InputLabel>Faction</InputLabel>
          <Select
            value={formData.faction}
            label="Faction"
            onChange={(event) => onFormChange({ ...formData, faction: event.target.value })}
            disabled={isLoading}
            data-testid="faction-select"
          >
            {FACTIONS.map((faction) => (
              <MenuItem key={faction} value={faction} data-testid={`faction-option-${faction}`}>
                {faction}
              </MenuItem>
            ))}
          </Select>
          {validationErrors.faction && <FormHelperText>{validationErrors.faction}</FormHelperText>}
        </FormControl>
      </Grid>

      <Grid item xs={12} sm={3}>
        <TextField
          fullWidth
          label="Role"
          value={formData.role}
          onChange={(event) => onFormChange({ ...formData, role: event.target.value })}
          error={!!validationErrors.role}
          helperText={validationErrors.role}
          placeholder="e.g., Sentinel, Collective Captain"
          disabled={isLoading}
        />
      </Grid>

      <Grid item xs={12}>
        <TextField
          fullWidth
          multiline
          rows={4}
          label="Character Description"
          value={formData.description}
          onChange={(event) => onFormChange({ ...formData, description: event.target.value })}
          error={!!validationErrors.description}
          helperText={
            validationErrors.description ||
            `Describe your character's background and personality (${formData.description.length}/2000)`
          }
          disabled={isLoading}
        />
      </Grid>
    </Grid>
  </>
);

const CharacterStatsSection: React.FC<{
  formData: CharacterFormData;
  validationErrors: ValidationErrors;
  totalStats: number;
  statsColor: 'success' | 'warning' | 'error';
  isLoading: boolean;
  onStatChange: (stat: keyof CharacterStats, value: number) => void;
}> = ({ formData, validationErrors, totalStats, statsColor, isLoading, onStatChange }) => (
  <Box sx={{ mb: 3 }}>
    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
      <Typography variant="h6" sx={{ fontWeight: 600 }}>
        Character Stats
      </Typography>
      <Chip label={`Total: ${totalStats}`} color={statsColor} variant="outlined" size="small" />
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
              onChange={(_, newValue) =>
                onStatChange(stat as keyof CharacterStats, newValue as number)
              }
              min={1}
              max={10}
              step={1}
              marks
              valueLabelDisplay="auto"
              disabled={isLoading}
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
);

const CharacterEquipmentSection: React.FC<{
  formData: CharacterFormData;
  newEquipment: { name: string; type: Equipment['type']; description: string; condition: number };
  showEquipmentForm: boolean;
  onToggleForm: (open: boolean) => void;
  onNewEquipmentChange: (next: {
    name: string;
    type: Equipment['type'];
    description: string;
    condition: number;
  }) => void;
  onAddEquipment: () => void;
  onRemoveEquipment: (index: number) => void;
  isLoading: boolean;
}> = ({
  formData,
  newEquipment,
  showEquipmentForm,
  onToggleForm,
  onNewEquipmentChange,
  onAddEquipment,
  onRemoveEquipment,
  isLoading,
}) => (
  <Box sx={{ mb: 3 }}>
    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
      <Typography variant="h6" sx={{ fontWeight: 600 }}>
        Equipment ({formData.equipment.length})
      </Typography>
      <Button
        startIcon={<AddIcon />}
        onClick={() => onToggleForm(true)}
        variant="outlined"
        size="small"
        disabled={isLoading}
      >
        Add Equipment
      </Button>
    </Box>

    {showEquipmentForm && (
      <CharacterEquipmentForm
        newEquipment={newEquipment}
        onNewEquipmentChange={onNewEquipmentChange}
        onAddEquipment={onAddEquipment}
        onCancel={() => onToggleForm(false)}
      />
    )}

    <CharacterEquipmentList
      equipment={formData.equipment}
      onRemoveEquipment={onRemoveEquipment}
    />
  </Box>
);

const CharacterEquipmentForm: React.FC<{
  newEquipment: { name: string; type: Equipment['type']; description: string; condition: number };
  onNewEquipmentChange: (next: {
    name: string;
    type: Equipment['type'];
    description: string;
    condition: number;
  }) => void;
  onAddEquipment: () => void;
  onCancel: () => void;
}> = ({ newEquipment, onNewEquipmentChange, onAddEquipment, onCancel }) => (
  <Paper sx={{ p: 2, mb: 2, bgcolor: 'action.hover' }}>
    <Grid container spacing={2} alignItems="end">
      <Grid item xs={12} sm={4}>
        <TextField
          fullWidth
          size="small"
          label="Equipment Name"
          value={newEquipment.name}
          onChange={(event) => onNewEquipmentChange({ ...newEquipment, name: event.target.value })}
        />
      </Grid>
      <Grid item xs={12} sm={3}>
        <FormControl fullWidth size="small">
          <InputLabel>Type</InputLabel>
          <Select
            value={newEquipment.type}
            label="Type"
            onChange={(event) =>
              onNewEquipmentChange({
                ...newEquipment,
                type: event.target.value as Equipment['type'],
              })
            }
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
          onChange={(event) =>
            onNewEquipmentChange({ ...newEquipment, description: event.target.value })
          }
        />
      </Grid>
      <Grid item xs={6} sm={1}>
        <Button
          fullWidth
          variant="contained"
          onClick={onAddEquipment}
          disabled={!newEquipment.name.trim()}
          size="small"
        >
          Add
        </Button>
      </Grid>
      <Grid item xs={6} sm={1}>
        <Button fullWidth variant="outlined" onClick={onCancel} size="small">
          Cancel
        </Button>
      </Grid>
    </Grid>
  </Paper>
);

const CharacterEquipmentList: React.FC<{
  equipment: Equipment[];
  onRemoveEquipment: (index: number) => void;
}> = ({ equipment, onRemoveEquipment }) =>
  equipment.length > 0 ? (
    <List dense>
      {equipment.map((item, index) => (
        <ListItem key={item.id || `${item.name}-${index}`} divider>
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
                  color={
                    item.condition > 0.7 ? 'success' : item.condition > 0.3 ? 'warning' : 'error'
                  }
                />
              </Box>
            }
            secondary={item.description || 'No description'}
          />
          <ListItemSecondaryAction>
            <IconButton
              edge="end"
              onClick={() => onRemoveEquipment(index)}
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
  );

const createStatChangeHandler = (
  setFormData: React.Dispatch<React.SetStateAction<CharacterFormData>>,
  setValidationErrors: React.Dispatch<React.SetStateAction<ValidationErrors>>
) => (stat: keyof CharacterStats, value: number) => {
  setFormData((prev) => ({
    ...prev,
    stats: { ...prev.stats, [stat]: value },
  }));

  setValidationErrors((prev) => {
    if (!prev[stat]) {
      return prev;
    }

    const nextErrors = { ...prev };
    delete nextErrors[stat];
    delete nextErrors.statsTotal;
    return nextErrors;
  });
};

const useCharacterEquipmentState = (
  setFormData: React.Dispatch<React.SetStateAction<CharacterFormData>>
) => {
  const [newEquipment, setNewEquipment] = useState({
    name: '',
    type: 'weapon' as Equipment['type'],
    description: '',
    condition: 1.0,
  });
  const [showEquipmentForm, setShowEquipmentForm] = useState(false);

  const addEquipment = () => {
    if (!newEquipment.name.trim()) return;

    const equipment: Equipment = {
      id: `eq_${Date.now()}`,
      ...newEquipment,
    };

    setFormData((prev) => ({
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
    setFormData((prev) => ({
      ...prev,
      equipment: prev.equipment.filter((_, i) => i !== index),
    }));
  };

  return {
    newEquipment,
    setNewEquipment,
    showEquipmentForm,
    setShowEquipmentForm,
    addEquipment,
    removeEquipment,
  };
};

const useCharacterFileState = () => {
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);

  const removeFile = (index: number) => {
    setUploadedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  return {
    uploadedFiles,
    setUploadedFiles,
    removeFile,
  };
};

const useCharacterFormState = (params: {
  open: boolean;
  mode: 'create' | 'edit';
  initialData?: CharacterFormData;
}) => {
  const [formData, setFormData] = useState<CharacterFormData>(createInitialFormData);
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({});
  const { uploadedFiles, setUploadedFiles, removeFile } = useCharacterFileState();
  const {
    newEquipment,
    setNewEquipment,
    showEquipmentForm,
    setShowEquipmentForm,
    addEquipment,
    removeEquipment,
  } = useCharacterEquipmentState(setFormData);

  useEffect(() => {
    if (!params.open) return;
    if (params.mode !== 'edit' || !params.initialData) return;

    setFormData(params.initialData);
    setUploadedFiles([]);
    setValidationErrors({});
  }, [params.open, params.mode, params.initialData, setUploadedFiles]);

  const handleStatChange = createStatChangeHandler(setFormData, setValidationErrors);

  const resetForm = () => {
    setFormData(createInitialFormData());
    setUploadedFiles([]);
    setValidationErrors({});
  };

  return {
    formData,
    setFormData,
    validationErrors,
    setValidationErrors,
    uploadedFiles,
    setUploadedFiles,
    newEquipment,
    setNewEquipment,
    showEquipmentForm,
    setShowEquipmentForm,
    handleStatChange,
    addEquipment,
    removeEquipment,
    removeFile,
    resetForm,
  };
};

const useCharacterDropzone = (params: {
  onFilesAdded: (files: File[]) => void;
  onDropError: (message: string) => void;
}) =>
  useDropzone({
    accept: {
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
      'application/json': ['.json'],
      'text/yaml': ['.yaml', '.yml'],
    },
    maxFiles: 5,
    maxSize: 10 * 1024 * 1024, // 10MB
    onDrop: params.onFilesAdded,
    onDropRejected: (rejectedFiles) => {
      const error = rejectedFiles[0]?.errors[0];
      const errorMessage =
        typeof error?.message === 'string' ? error.message : 'File upload failed';
      params.onDropError(errorMessage);
    },
  });

type CharacterFormBodyProps = {
  formData: CharacterFormData;
  validationErrors: ValidationErrors;
  uploadedFiles: File[];
  newEquipment: { name: string; type: Equipment['type']; description: string; condition: number };
  showEquipmentForm: boolean;
  isLoading: boolean;
  mode: 'create' | 'edit';
  getRootProps: ReturnType<typeof useDropzone>['getRootProps'];
  getInputProps: ReturnType<typeof useDropzone>['getInputProps'];
  isDragActive: boolean;
  totalStats: number;
  statsColor: 'success' | 'warning' | 'error';
  setFormData: React.Dispatch<React.SetStateAction<CharacterFormData>>;
  onStatChange: (stat: keyof CharacterStats, value: number) => void;
  onToggleEquipmentForm: (open: boolean) => void;
  onNewEquipmentChange: (next: {
    name: string;
    type: Equipment['type'];
    description: string;
    condition: number;
  }) => void;
  onAddEquipment: () => void;
  onRemoveEquipment: (index: number) => void;
  onRemoveFile: (index: number) => void;
};

const CharacterFormBody: React.FC<CharacterFormBodyProps> = ({
  formData,
  validationErrors,
  uploadedFiles,
  newEquipment,
  showEquipmentForm,
  isLoading,
  mode,
  getRootProps,
  getInputProps,
  isDragActive,
  totalStats,
  statsColor,
  onFormChange,
  onStatChange,
  onToggleEquipmentForm,
  onNewEquipmentChange,
  onAddEquipment,
  onRemoveEquipment,
  onRemoveFile,
}) => (
  <>
    <CharacterBasicInfo
      formData={formData}
      validationErrors={validationErrors}
      isLoading={isLoading}
      mode={mode}
      onFormChange={onFormChange}
    />
    <Divider sx={{ my: 3 }} />
    <CharacterStatsSection
      formData={formData}
      validationErrors={validationErrors}
      totalStats={totalStats}
      statsColor={statsColor}
      isLoading={isLoading}
      onStatChange={onStatChange}
    />
    <Divider sx={{ my: 3 }} />
    <CharacterEquipmentSection
      formData={formData}
      newEquipment={newEquipment}
      showEquipmentForm={showEquipmentForm}
      onToggleForm={onToggleEquipmentForm}
      onNewEquipmentChange={onNewEquipmentChange}
      onAddEquipment={onAddEquipment}
      onRemoveEquipment={onRemoveEquipment}
      isLoading={isLoading}
    />
    <Divider sx={{ my: 3 }} />
    <CharacterFileUpload
      getRootProps={getRootProps}
      getInputProps={getInputProps}
      isDragActive={isDragActive}
      uploadedFiles={uploadedFiles}
      validationErrors={validationErrors}
      onRemoveFile={onRemoveFile}
    />
  </>
);

type CharacterFileUploadProps = {
  getRootProps: ReturnType<typeof useDropzone>['getRootProps'];
  getInputProps: ReturnType<typeof useDropzone>['getInputProps'];
  isDragActive: boolean;
  uploadedFiles: File[];
  validationErrors: ValidationErrors;
  onRemoveFile: (index: number) => void;
};

const buildFormBodyProps = (params: {
  formData: CharacterFormData;
  validationErrors: ValidationErrors;
  uploadedFiles: File[];
  newEquipment: { name: string; type: Equipment['type']; description: string; condition: number };
  showEquipmentForm: boolean;
  isLoading: boolean;
  mode: 'create' | 'edit';
  getRootProps: ReturnType<typeof useDropzone>['getRootProps'];
  getInputProps: ReturnType<typeof useDropzone>['getInputProps'];
  isDragActive: boolean;
  totalStats: number;
  statsColor: 'success' | 'warning' | 'error';
  onFormChange: (next: CharacterFormData) => void;
  onStatChange: (stat: keyof CharacterStats, value: number) => void;
  onToggleEquipmentForm: (open: boolean) => void;
  onNewEquipmentChange: (next: {
    name: string;
    type: Equipment['type'];
    description: string;
    condition: number;
  }) => void;
  onAddEquipment: () => void;
  onRemoveEquipment: (index: number) => void;
  onRemoveFile: (index: number) => void;
}): CharacterFormBodyProps => ({
  formData: params.formData,
  validationErrors: params.validationErrors,
  uploadedFiles: params.uploadedFiles,
  newEquipment: params.newEquipment,
  showEquipmentForm: params.showEquipmentForm,
  isLoading: params.isLoading,
  mode: params.mode,
  getRootProps: params.getRootProps,
  getInputProps: params.getInputProps,
  isDragActive: params.isDragActive,
  totalStats: params.totalStats,
  statsColor: params.statsColor,
  onFormChange: params.onFormChange,
  onStatChange: params.onStatChange,
  onToggleEquipmentForm: params.onToggleEquipmentForm,
  onNewEquipmentChange: params.onNewEquipmentChange,
  onAddEquipment: params.onAddEquipment,
  onRemoveEquipment: params.onRemoveEquipment,
  onRemoveFile: params.onRemoveFile,
});

const buildDialogViewData = (params: {
  formData: CharacterFormData;
  validationErrors: ValidationErrors;
  uploadedFiles: File[];
  newEquipment: { name: string; type: Equipment['type']; description: string; condition: number };
  showEquipmentForm: boolean;
  isLoading: boolean;
  mode: 'create' | 'edit';
  getRootProps: ReturnType<typeof useDropzone>['getRootProps'];
  getInputProps: ReturnType<typeof useDropzone>['getInputProps'];
  isDragActive: boolean;
  onFormChange: (next: CharacterFormData) => void;
  onStatChange: (stat: keyof CharacterStats, value: number) => void;
  onToggleEquipmentForm: (open: boolean) => void;
  onNewEquipmentChange: (next: {
    name: string;
    type: Equipment['type'];
    description: string;
    condition: number;
  }) => void;
  onAddEquipment: () => void;
  onRemoveEquipment: (index: number) => void;
  onRemoveFile: (index: number) => void;
  error?: string;
}) => {
  const totalStats = getStatsTotal(params.formData.stats);
  const statsColor = getStatsColor(totalStats);
  const errorMessage = getCharacterErrorMessage(params.mode, params.error);
  const showTestHelper = params.mode === 'create' && process.env.NODE_ENV === 'development';
  const handleTestFill = createTestFillHandler(params.setFormData);
  const formBodyProps = buildFormBodyProps({
    formData: params.formData,
    validationErrors: params.validationErrors,
    uploadedFiles: params.uploadedFiles,
    newEquipment: params.newEquipment,
    showEquipmentForm: params.showEquipmentForm,
    isLoading: params.isLoading,
    mode: params.mode,
    getRootProps: params.getRootProps,
    getInputProps: params.getInputProps,
    isDragActive: params.isDragActive,
    totalStats,
    statsColor,
    onFormChange: params.setFormData,
    onStatChange: params.onStatChange,
    onToggleEquipmentForm: params.onToggleEquipmentForm,
    onNewEquipmentChange: params.onNewEquipmentChange,
    onAddEquipment: params.onAddEquipment,
    onRemoveEquipment: params.onRemoveEquipment,
    onRemoveFile: params.onRemoveFile,
  });

  return {
    errorMessage,
    showTestHelper,
    handleTestFill,
    formBodyProps,
  };
};

const CharacterFileUpload: React.FC<CharacterFileUploadProps> = ({
  getRootProps,
  getInputProps,
  isDragActive,
  uploadedFiles,
  validationErrors,
  onRemoveFile,
}) => (
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
        {isDragActive ? 'Drop files here...' : 'Drag & drop character files, or click to browse'}
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
                onClick={() => onRemoveFile(index)}
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
);

const useCharacterDialogState = (params: Props) => {
  const { open, onClose, onCharacterCreated, mode = 'create', characterId, initialData } = params;
  const {
    formData,
    setFormData,
    validationErrors,
    setValidationErrors,
    uploadedFiles,
    setUploadedFiles,
    newEquipment,
    setNewEquipment,
    showEquipmentForm,
    setShowEquipmentForm,
    handleStatChange,
    addEquipment,
    removeEquipment,
    removeFile,
    resetForm,
  } = useCharacterFormState({ open, mode, initialData });
  const dialogRef = useCharacterDialogFocus(open, onClose);
  const { createCharacter, updateCharacter, characterMutation, isBootstrappingEdit } =
    useCharacterMutationState(mode, initialData);
  const { getRootProps, getInputProps, isDragActive } = useCharacterDropzone({
    onFilesAdded: createFileAppendHandler(setUploadedFiles),
    onDropError: createFileErrorHandler(setValidationErrors),
  });
  const validateForm = createFormValidator(formData, uploadedFiles, setValidationErrors);
  const handleSubmit = createSubmitHandler({
    mode,
    characterId,
    formData,
    uploadedFiles,
    validateForm,
    createCharacter,
    updateCharacter,
    resetForm,
    onCharacterCreated,
    onClose,
  });
  const handleClose = createCloseHandler(characterMutation.isLoading, onClose);
  const { errorMessage, showTestHelper, handleTestFill, formBodyProps } = buildDialogViewData({
    formData,
    validationErrors,
    uploadedFiles,
    newEquipment,
    showEquipmentForm,
    isLoading: characterMutation.isLoading,
    mode,
    getRootProps,
    getInputProps,
    isDragActive,
    setFormData,
    onStatChange: handleStatChange,
    onToggleEquipmentForm: setShowEquipmentForm,
    onNewEquipmentChange: setNewEquipment,
    onAddEquipment: addEquipment,
    onRemoveEquipment: removeEquipment,
    onRemoveFile: removeFile,
    error: characterMutation.error?.message,
  });

  return {
    dialogRef,
    mode,
    isLoading: characterMutation.isLoading,
    isError: characterMutation.isError,
    errorMessage,
    showTestHelper,
    handleTestFill,
    isBootstrappingEdit,
    handleSubmit,
    handleClose,
    formBodyProps,
  };
};

export default function CharacterCreationDialog({
  open,
  onClose,
  onCharacterCreated,
  mode = 'create',
  characterId,
  initialData,
}: Props) {
  const {
    dialogRef,
    mode: dialogMode,
    isLoading,
    isError,
    errorMessage,
    showTestHelper,
    handleTestFill,
    isBootstrappingEdit,
    handleSubmit,
    handleClose,
    formBodyProps,
  } = useCharacterDialogState({
    open,
    onClose,
    onCharacterCreated,
    mode,
    characterId,
    initialData,
  });

  return (
    <CharacterDialogView
      open={open}
      dialogRef={dialogRef}
      mode={dialogMode}
      isLoading={isLoading}
      showTestHelper={showTestHelper}
      onTestFill={handleTestFill}
      isBootstrappingEdit={isBootstrappingEdit}
      onSubmit={handleSubmit}
      isError={isError}
      errorMessage={errorMessage}
      onClose={handleClose}
      formBodyProps={formBodyProps}
    />
  );
}

const CharacterDialogView: React.FC<{
  open: boolean;
  dialogRef: React.RefObject<HTMLDivElement>;
  mode: 'create' | 'edit';
  isLoading: boolean;
  showTestHelper: boolean;
  onTestFill: () => void;
  isBootstrappingEdit: boolean;
  onSubmit: (event: React.FormEvent) => void;
  isError: boolean;
  errorMessage: string;
  onClose: () => void;
  formBodyProps: CharacterFormBodyProps;
}> = ({
  open,
  dialogRef,
  mode,
  isLoading,
  showTestHelper,
  onTestFill,
  isBootstrappingEdit,
  onSubmit,
  isError,
  errorMessage,
  onClose,
  formBodyProps,
}) => (
  <Dialog
    open={open}
    onClose={onClose}
    maxWidth="md"
    fullWidth
    ref={dialogRef}
    aria-labelledby="character-creation-title"
    aria-describedby="character-creation-description"
    PaperProps={{
      sx: { minHeight: '80vh' },
    }}
  >
    <CharacterDialogHeader mode={mode} isLoading={isLoading} onClose={onClose} />

    {/* Test Helper Button */}
    {showTestHelper && <CharacterTestHelper onFill={onTestFill} />}

    {isLoading && <LinearProgress />}

    {isBootstrappingEdit ? (
      <CharacterBootstrapping onCancel={onClose} />
    ) : (
      <form onSubmit={onSubmit}>
        <DialogContent sx={{ pb: 1 }}>
          {isError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {errorMessage}
            </Alert>
          )}
          <CharacterFormBody {...formBodyProps} />
        </DialogContent>

        <CharacterFormActions isLoading={isLoading} mode={mode} onCancel={onClose} />
      </form>
    )}
  </Dialog>
);
