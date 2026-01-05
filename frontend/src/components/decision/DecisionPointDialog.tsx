import React, { useEffect, useRef, useCallback, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  TextField,
  Card,
  CardContent,
  CardActionArea,
  Grid,
  IconButton,
  LinearProgress,
  Alert,
  Chip,
  Fade,
  Collapse,
  CircularProgress,
} from '@mui/material';
import {
  Close as CloseIcon,
  Timer as TimerIcon,
  SkipNext as SkipIcon,
  Send as SendIcon,
  Autorenew as NegotiateIcon,
  Check as CheckIcon,
  Edit as EditIcon,
} from '@mui/icons-material';
import { useFocusTrap } from '../../utils/focusManagement';
import type { RootState, AppDispatch } from '../../store/store';
import {
  selectOption,
  setFreeTextInput,
  decrementCountdown,
} from '../../store/slices/decisionSlice';
import {
  submitDecisionResponse,
  confirmNegotiation,
  skipDecision,
} from '../../store/slices/decisionSlice';

type Decision = NonNullable<RootState['decision']['currentDecision']>;
type DecisionOption = Decision['options'][number];
type NegotiationResult = NonNullable<RootState['decision']['negotiationResult']>;

interface OptionCardProps {
  optionId: number;
  label: string;
  description: string;
  icon?: string;
  impactPreview?: string;
  isSelected: boolean;
  onSelect: (id: number) => void;
  disabled?: boolean;
}

function OptionCard({
  optionId,
  label,
  description,
  icon,
  impactPreview,
  isSelected,
  onSelect,
  disabled,
}: OptionCardProps) {
  return (
    <Card
      variant={isSelected ? 'elevation' : 'outlined'}
      sx={{
        borderColor: isSelected ? 'primary.main' : 'divider',
        borderWidth: isSelected ? 2 : 1,
        bgcolor: isSelected ? 'action.selected' : 'background.paper',
        transition: 'all 0.2s ease',
        opacity: disabled ? 0.5 : 1,
        '&:hover': {
          borderColor: disabled ? 'divider' : 'primary.light',
        },
      }}
    >
      <CardActionArea
        onClick={() => !disabled && onSelect(optionId)}
        disabled={disabled}
        sx={{ p: 2 }}
      >
        <Box display="flex" alignItems="flex-start" gap={1.5}>
          {icon && (
            <Typography variant="h5" component="span">
              {icon}
            </Typography>
          )}
          <Box flex={1}>
            <Typography variant="subtitle1" fontWeight="bold">
              {label}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {description}
            </Typography>
            {impactPreview && (
              <Typography
                variant="caption"
                color="primary.main"
                sx={{ mt: 1, display: 'block', fontStyle: 'italic' }}
              >
                {impactPreview}
              </Typography>
            )}
          </Box>
          {isSelected && (
            <CheckIcon color="primary" sx={{ ml: 'auto' }} />
          )}
        </Box>
      </CardActionArea>
    </Card>
  );
}

interface CountdownTimerProps {
  seconds: number;
  totalSeconds: number;
}

function CountdownTimer({ seconds, totalSeconds }: CountdownTimerProps) {
  const progress = (seconds / totalSeconds) * 100;
  const isUrgent = seconds <= 30;

  return (
    <Box display="flex" alignItems="center" gap={1}>
      <TimerIcon color={isUrgent ? 'error' : 'action'} fontSize="small" />
      <Typography
        variant="body2"
        color={isUrgent ? 'error.main' : 'text.secondary'}
        fontWeight={isUrgent ? 'bold' : 'normal'}
      >
        {Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, '0')}
      </Typography>
      <LinearProgress
        variant="determinate"
        value={progress}
        sx={{
          width: 60,
          height: 6,
          borderRadius: 1,
          bgcolor: isUrgent ? 'error.light' : 'action.hover',
          '& .MuiLinearProgress-bar': {
            bgcolor: isUrgent ? 'error.main' : 'primary.main',
          },
        }}
      />
    </Box>
  );
}

const DecisionHeader: React.FC<{
  decision: Decision;
  remainingSeconds: number;
  isSubmitting: boolean;
  onSkip: () => void;
}> = ({ decision, remainingSeconds, isSubmitting, onSkip }) => (
  <DialogTitle
    id="decision-dialog-title"
    sx={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      bgcolor: 'primary.main',
      color: 'primary.contrastText',
      pb: 1,
    }}
  >
    <Box>
      <Typography variant="h6" component="span">
        {decision.title}
      </Typography>
      <Box display="flex" alignItems="center" gap={1} mt={0.5}>
        <Chip
          size="small"
          label={`Turn ${decision.turnNumber}`}
          sx={{ bgcolor: 'rgba(255,255,255,0.2)', color: 'inherit' }}
        />
        <Chip
          size="small"
          label={decision.decisionType.replace('_', ' ')}
          sx={{ bgcolor: 'rgba(255,255,255,0.2)', color: 'inherit' }}
        />
      </Box>
    </Box>
    <Box display="flex" alignItems="center" gap={2}>
      <CountdownTimer
        seconds={remainingSeconds}
        totalSeconds={decision.timeoutSeconds}
      />
      <IconButton
        onClick={onSkip}
        disabled={isSubmitting}
        size="small"
        sx={{ color: 'inherit' }}
        aria-label="Skip decision"
      >
        <CloseIcon />
      </IconButton>
    </Box>
  </DialogTitle>
);

const DecisionDescription: React.FC<{ description: string }> = ({ description }) => (
  <Typography
    id="decision-dialog-description"
    variant="body1"
    color="text.secondary"
    sx={{ mb: 3 }}
  >
    {description}
  </Typography>
);

const NarrativeContext: React.FC<{ narrativeContext: string }> = ({ narrativeContext }) => (
  <Box
    sx={{
      bgcolor: 'action.hover',
      borderRadius: 1,
      p: 2,
      mb: 3,
      borderLeft: 4,
      borderColor: 'primary.main',
    }}
  >
    <Typography variant="body2" fontStyle="italic">
      {narrativeContext}
    </Typography>
  </Box>
);

const NegotiationAlert: React.FC<{ result: NegotiationResult | null }> = ({ result }) => (
  <Collapse in={result !== null}>
    <Alert
      severity={
        result?.feasibility === 'accepted'
          ? 'success'
          : result?.feasibility === 'minor_adjustment'
            ? 'info'
            : 'warning'
      }
      icon={<NegotiateIcon />}
      sx={{ mb: 3 }}
    >
      <Typography variant="subtitle2" fontWeight="bold">
        {result?.feasibility === 'accepted'
          ? 'Action Accepted'
          : result?.feasibility === 'minor_adjustment'
            ? 'Adjustment Suggested'
            : 'Alternatives Required'}
      </Typography>
      <Typography variant="body2">
        {result?.explanation}
      </Typography>
      {result?.adjustedAction && (
        <Typography
          variant="body2"
          sx={{ mt: 1, fontStyle: 'italic', color: 'text.secondary' }}
        >
          Suggested: "{result.adjustedAction}"
        </Typography>
      )}
    </Alert>
  </Collapse>
);

const InputModeToggle: React.FC<{
  inputMode: 'options' | 'freetext';
  isNegotiating: boolean;
  onSelectMode: (mode: 'options' | 'freetext') => void;
}> = ({ inputMode, isNegotiating, onSelectMode }) => (
  <Box display="flex" gap={1} mb={2}>
    <Button
      variant={inputMode === 'options' ? 'contained' : 'outlined'}
      size="small"
      onClick={() => onSelectMode('options')}
      disabled={isNegotiating}
      startIcon={<CheckIcon />}
    >
      Choose Option
    </Button>
    <Button
      variant={inputMode === 'freetext' ? 'contained' : 'outlined'}
      size="small"
      onClick={() => onSelectMode('freetext')}
      disabled={isNegotiating}
      startIcon={<EditIcon />}
    >
      Custom Action
    </Button>
  </Box>
);

const OptionsGrid: React.FC<{
  options: DecisionOption[];
  selectedOptionId: number | null;
  onSelect: (id: number) => void;
  isSubmitting: boolean;
  hidden: boolean;
}> = ({ options, selectedOptionId, onSelect, isSubmitting, hidden }) => (
  <Fade in={!hidden}>
    <Box sx={{ display: hidden ? 'none' : 'block' }}>
      <Grid container spacing={2}>
        {options.map((option) => (
          <Grid item xs={12} sm={6} key={option.optionId}>
            <OptionCard
              optionId={option.optionId}
              label={option.label}
              description={option.description}
              icon={option.icon}
              impactPreview={option.impactPreview}
              isSelected={selectedOptionId === option.optionId}
              onSelect={onSelect}
              disabled={isSubmitting}
            />
          </Grid>
        ))}
      </Grid>
    </Box>
  </Fade>
);

const FreeTextInput: React.FC<{
  value: string;
  onChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  isSubmitting: boolean;
  hidden: boolean;
}> = ({ value, onChange, isSubmitting, hidden }) => (
  <Fade in={!hidden}>
    <Box sx={{ display: hidden ? 'none' : 'block' }}>
      <TextField
        fullWidth
        multiline
        rows={3}
        variant="outlined"
        placeholder="Describe what you want the characters to do..."
        value={value}
        onChange={onChange}
        disabled={isSubmitting}
        inputProps={{
          'aria-label': 'Custom action input',
          maxLength: 500,
        }}
        helperText={`${value.length}/500 characters (minimum 5)`}
      />
    </Box>
  </Fade>
);

const NegotiationAlternatives: React.FC<{
  alternatives: DecisionOption[] | undefined;
  selectedOptionId: number | null;
  onSelect: (id: number) => void;
  isSubmitting: boolean;
  isNegotiating: boolean;
}> = ({ alternatives, selectedOptionId, onSelect, isSubmitting, isNegotiating }) => (
  <Collapse in={isNegotiating && !!alternatives?.length}>
    <Box mt={2}>
      <Typography variant="subtitle2" gutterBottom>
        Alternative Actions:
      </Typography>
      <Grid container spacing={2}>
        {alternatives?.map((alt) => (
          <Grid item xs={12} sm={6} key={alt.optionId}>
            <OptionCard
              optionId={alt.optionId}
              label={alt.label}
              description={alt.description}
              isSelected={selectedOptionId === alt.optionId}
              onSelect={onSelect}
              disabled={isSubmitting}
            />
          </Grid>
        ))}
      </Grid>
    </Box>
  </Collapse>
);

const DecisionActions: React.FC<{
  isNegotiating: boolean;
  isSubmitting: boolean;
  canSubmit: boolean;
  onSkip: () => void;
  onSubmit: () => void;
  onAcceptNegotiation: () => void;
  onInsistOriginal: () => void;
}> = ({
  isNegotiating,
  isSubmitting,
  canSubmit,
  onSkip,
  onSubmit,
  onAcceptNegotiation,
  onInsistOriginal,
}) => (
  <DialogActions sx={{ p: 2, gap: 1 }}>
    <Button
      onClick={onSkip}
      disabled={isSubmitting}
      startIcon={<SkipIcon />}
      color="inherit"
    >
      Skip (Default)
    </Button>

    <Box flex={1} />

    {isNegotiating ? (
      <>
        <Button
          variant="outlined"
          onClick={onInsistOriginal}
          disabled={isSubmitting}
        >
          Keep Original
        </Button>
        <Button
          variant="contained"
          onClick={onAcceptNegotiation}
          disabled={isSubmitting}
          startIcon={isSubmitting ? <CircularProgress size={16} /> : <CheckIcon />}
        >
          Accept Suggestion
        </Button>
      </>
    ) : (
      <Button
        variant="contained"
        onClick={onSubmit}
        disabled={!canSubmit || isSubmitting}
        startIcon={isSubmitting ? <CircularProgress size={16} /> : <SendIcon />}
      >
        Confirm
      </Button>
    )}
  </DialogActions>
);

const DecisionDialogContent: React.FC<{
  error: string | null;
  decision: Decision;
  isNegotiating: boolean;
  negotiationResult: NegotiationResult | null;
  inputMode: 'options' | 'freetext';
  onSelectMode: (mode: 'options' | 'freetext') => void;
  selectedOptionId: number | null;
  onOptionSelect: (id: number) => void;
  freeTextInput: string;
  onFreeTextChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  isSubmitting: boolean;
}> = ({
  error,
  decision,
  isNegotiating,
  negotiationResult,
  inputMode,
  onSelectMode,
  selectedOptionId,
  onOptionSelect,
  freeTextInput,
  onFreeTextChange,
  isSubmitting,
}) => (
  <DialogContent dividers sx={{ p: 3 }}>
    {error && (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    )}

    <DecisionDescription description={decision.description} />

    {decision.narrativeContext && (
      <NarrativeContext narrativeContext={decision.narrativeContext} />
    )}

    <NegotiationAlert result={isNegotiating ? negotiationResult : null} />

    <InputModeToggle
      inputMode={inputMode}
      isNegotiating={isNegotiating}
      onSelectMode={onSelectMode}
    />

    <OptionsGrid
      options={decision.options}
      selectedOptionId={selectedOptionId}
      onSelect={onOptionSelect}
      isSubmitting={isSubmitting}
      hidden={inputMode !== 'options' || isNegotiating}
    />

    <FreeTextInput
      value={freeTextInput}
      onChange={onFreeTextChange}
      isSubmitting={isSubmitting}
      hidden={inputMode !== 'freetext' || isNegotiating}
    />

    <NegotiationAlternatives
      alternatives={negotiationResult?.alternatives}
      selectedOptionId={selectedOptionId}
      onSelect={onOptionSelect}
      isSubmitting={isSubmitting}
      isNegotiating={isNegotiating}
    />
  </DialogContent>
);

const DecisionDialog: React.FC<{
  dialogRef: React.RefObject<HTMLDivElement>;
  isOpen: boolean;
  isSubmitting: boolean;
  onClose: (_event: unknown, reason?: 'backdropClick' | 'escapeKeyDown') => void;
  decision: Decision;
  remainingSeconds: number;
  onSkip: () => void;
  error: string | null;
  isNegotiating: boolean;
  negotiationResult: NegotiationResult | null;
  inputMode: 'options' | 'freetext';
  onSelectMode: (mode: 'options' | 'freetext') => void;
  selectedOptionId: number | null;
  onOptionSelect: (id: number) => void;
  freeTextInput: string;
  onFreeTextChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  canSubmit: boolean;
  onSubmit: () => void;
  onAcceptNegotiation: () => void;
  onInsistOriginal: () => void;
}> = ({
  dialogRef,
  isOpen,
  isSubmitting,
  onClose,
  decision,
  remainingSeconds,
  onSkip,
  error,
  isNegotiating,
  negotiationResult,
  inputMode,
  onSelectMode,
  selectedOptionId,
  onOptionSelect,
  freeTextInput,
  onFreeTextChange,
  canSubmit,
  onSubmit,
  onAcceptNegotiation,
  onInsistOriginal,
}) => (
  <Dialog
    ref={dialogRef}
    open={isOpen}
    maxWidth="md"
    fullWidth
    disableEscapeKeyDown={isSubmitting}
    onClose={onClose}
    aria-labelledby="decision-dialog-title"
    aria-describedby="decision-dialog-description"
    PaperProps={{
      sx: {
        borderRadius: 2,
        maxHeight: '90vh',
      },
    }}
  >
    <DecisionHeader
      decision={decision}
      remainingSeconds={remainingSeconds}
      isSubmitting={isSubmitting}
      onSkip={onSkip}
    />

    <DecisionDialogContent
      error={error}
      decision={decision}
      isNegotiating={isNegotiating}
      negotiationResult={negotiationResult}
      inputMode={inputMode}
      onSelectMode={onSelectMode}
      selectedOptionId={selectedOptionId}
      onOptionSelect={onOptionSelect}
      freeTextInput={freeTextInput}
      onFreeTextChange={onFreeTextChange}
      isSubmitting={isSubmitting}
    />

    <DecisionActions
      isNegotiating={isNegotiating}
      isSubmitting={isSubmitting}
      canSubmit={canSubmit}
      onSkip={onSkip}
      onSubmit={onSubmit}
      onAcceptNegotiation={onAcceptNegotiation}
      onInsistOriginal={onInsistOriginal}
    />
  </Dialog>
);

const useDecisionCountdown = (
  isOpen: boolean,
  remainingSeconds: number,
  dispatch: AppDispatch
) => {
  useEffect(() => {
    if (!isOpen || remainingSeconds <= 0) return;

    const timer = setInterval(() => {
      dispatch(decrementCountdown());
    }, 1000);

    return () => clearInterval(timer);
  }, [isOpen, remainingSeconds, dispatch]);
};

const useDecisionAutoSkip = (
  isOpen: boolean,
  remainingSeconds: number,
  currentDecision: Decision | null,
  dispatch: AppDispatch
) => {
  useEffect(() => {
    if (isOpen && remainingSeconds === 0 && currentDecision) {
      dispatch(skipDecision(currentDecision.decisionId));
    }
  }, [remainingSeconds, isOpen, currentDecision, dispatch]);
};

const useDecisionFocus = (
  isOpen: boolean,
  dialogRef: React.RefObject<HTMLDivElement>,
  currentDecision: Decision | null,
  isSubmitting: boolean,
  dispatch: AppDispatch
) => {
  useFocusTrap(isOpen, dialogRef, {
    onEscape: () => {
      if (currentDecision && !isSubmitting) {
        dispatch(skipDecision(currentDecision.decisionId));
      }
    },
  });
};

const useDecisionHandlers = (
  dispatch: AppDispatch,
  currentDecision: Decision | null,
  inputMode: 'options' | 'freetext',
  selectedOptionId: number | null,
  freeTextInput: string
) => {
  const handleOptionSelect = useCallback(
    (id: number) => {
      dispatch(selectOption(id));
    },
    [dispatch]
  );

  const handleFreeTextChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      dispatch(setFreeTextInput(e.target.value));
    },
    [dispatch]
  );

  const handleSubmit = useCallback(() => {
    if (!currentDecision) return;

    if (inputMode === 'options' && selectedOptionId !== null) {
      dispatch(
        submitDecisionResponse({
          decisionId: currentDecision.decisionId,
          inputType: 'option',
          selectedOptionId,
        })
      );
    } else if (inputMode === 'freetext' && freeTextInput.trim()) {
      dispatch(
        submitDecisionResponse({
          decisionId: currentDecision.decisionId,
          inputType: 'freetext',
          freeText: freeTextInput,
        })
      );
    }
  }, [currentDecision, inputMode, selectedOptionId, freeTextInput, dispatch]);

  const handleSkip = useCallback(() => {
    if (currentDecision) {
      dispatch(skipDecision(currentDecision.decisionId));
    }
  }, [currentDecision, dispatch]);

  return {
    handleOptionSelect,
    handleFreeTextChange,
    handleSubmit,
    handleSkip,
  };
};

const useNegotiationHandlers = (
  dispatch: AppDispatch,
  currentDecision: Decision | null
) => {
  const handleAcceptNegotiation = useCallback(() => {
    if (currentDecision) {
      dispatch(
        confirmNegotiation({
          decisionId: currentDecision.decisionId,
          accepted: true,
          insistOriginal: false,
        })
      );
    }
  }, [currentDecision, dispatch]);

  const handleInsistOriginal = useCallback(() => {
    if (currentDecision) {
      dispatch(
        confirmNegotiation({
          decisionId: currentDecision.decisionId,
          accepted: false,
          insistOriginal: true,
        })
      );
    }
  }, [currentDecision, dispatch]);

  return { handleAcceptNegotiation, handleInsistOriginal };
};

const useDecisionDialogState = () => {
  const dispatch = useDispatch<AppDispatch>();
  const dialogRef = useRef<HTMLDivElement>(null);
  const [inputMode, setInputMode] = useState<'options' | 'freetext'>('options');

  const decisionState = useSelector((state: RootState) => state.decision);
  const {
    currentDecision,
    pauseState,
    isNegotiating,
    negotiationResult,
    remainingSeconds,
    selectedOptionId,
    freeTextInput,
    isSubmitting,
    error,
  } = decisionState;

  const isOpen = currentDecision !== null && pauseState !== 'running';

  useDecisionCountdown(isOpen, remainingSeconds, dispatch);
  useDecisionAutoSkip(isOpen, remainingSeconds, currentDecision, dispatch);
  useDecisionFocus(isOpen, dialogRef, currentDecision, isSubmitting, dispatch);

  const {
    handleOptionSelect,
    handleFreeTextChange,
    handleSubmit,
    handleSkip,
  } = useDecisionHandlers(
    dispatch,
    currentDecision,
    inputMode,
    selectedOptionId,
    freeTextInput
  );

  const { handleAcceptNegotiation, handleInsistOriginal } = useNegotiationHandlers(
    dispatch,
    currentDecision
  );

  return {
    dialogRef,
    inputMode,
    setInputMode,
    currentDecision,
    isOpen,
    isNegotiating,
    negotiationResult,
    remainingSeconds,
    selectedOptionId,
    freeTextInput,
    isSubmitting,
    error,
    handleOptionSelect,
    handleFreeTextChange,
    handleSubmit,
    handleSkip,
    handleAcceptNegotiation,
    handleInsistOriginal,
  };
};

export default function DecisionPointDialog() {
  const {
    dialogRef,
    inputMode,
    setInputMode,
    currentDecision,
    isOpen,
    isNegotiating,
    negotiationResult,
    remainingSeconds,
    selectedOptionId,
    freeTextInput,
    isSubmitting,
    error,
    handleOptionSelect,
    handleFreeTextChange,
    handleSubmit,
    handleSkip,
    handleAcceptNegotiation,
    handleInsistOriginal,
  } = useDecisionDialogState();

  const handleDialogClose = useCallback(
    (_event: unknown, reason?: 'backdropClick' | 'escapeKeyDown') => {
      if (isSubmitting) return;
      if (reason === 'escapeKeyDown' || reason === 'backdropClick') {
        handleSkip();
      }
    },
    [handleSkip, isSubmitting]
  );

  if (!currentDecision) return null;

  const canSubmit =
    (inputMode === 'options' && selectedOptionId !== null) ||
    (inputMode === 'freetext' && freeTextInput.trim().length >= 5);

  return (
    <DecisionDialog
      dialogRef={dialogRef}
      isOpen={isOpen}
      isSubmitting={isSubmitting}
      onClose={handleDialogClose}
      decision={currentDecision}
      remainingSeconds={remainingSeconds}
      onSkip={handleSkip}
      error={error}
      isNegotiating={isNegotiating}
      negotiationResult={negotiationResult}
      inputMode={inputMode}
      onSelectMode={setInputMode}
      selectedOptionId={selectedOptionId}
      onOptionSelect={handleOptionSelect}
      freeTextInput={freeTextInput}
      onFreeTextChange={handleFreeTextChange}
      canSubmit={canSubmit}
      onSubmit={handleSubmit}
      onAcceptNegotiation={handleAcceptNegotiation}
      onInsistOriginal={handleInsistOriginal}
    />
  );
}
