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
  clearDecisionPoint,
} from '../../store/slices/decisionSlice';
import {
  submitDecisionResponse,
  confirmNegotiation,
  skipDecision,
} from '../../store/slices/decisionSlice';

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

export default function DecisionPointDialog() {
  const dispatch = useDispatch<AppDispatch>();
  const dialogRef = useRef<HTMLDivElement>(null);
  const [inputMode, setInputMode] = useState<'options' | 'freetext'>('options');

  // Redux state
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
  } = useSelector((state: RootState) => state.decision);

  const isOpen = currentDecision !== null && pauseState !== 'running';

  // Countdown timer
  useEffect(() => {
    if (!isOpen || remainingSeconds <= 0) return;

    const timer = setInterval(() => {
      dispatch(decrementCountdown());
    }, 1000);

    return () => clearInterval(timer);
  }, [isOpen, remainingSeconds, dispatch]);

  // Auto-skip when timeout
  useEffect(() => {
    if (isOpen && remainingSeconds === 0 && currentDecision) {
      dispatch(skipDecision(currentDecision.decisionId));
    }
  }, [remainingSeconds, isOpen, currentDecision, dispatch]);

  // Focus trap for accessibility
  useFocusTrap(isOpen, dialogRef, {
    onEscape: () => {
      if (currentDecision && !isSubmitting) {
        dispatch(skipDecision(currentDecision.decisionId));
      }
    },
  });

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

  if (!currentDecision) return null;

  const canSubmit =
    (inputMode === 'options' && selectedOptionId !== null) ||
    (inputMode === 'freetext' && freeTextInput.trim().length >= 5);

  return (
    <Dialog
      ref={dialogRef}
      open={isOpen}
      maxWidth="md"
      fullWidth
      disableEscapeKeyDown={isSubmitting}
      aria-labelledby="decision-dialog-title"
      aria-describedby="decision-dialog-description"
      PaperProps={{
        sx: {
          borderRadius: 2,
          maxHeight: '90vh',
        },
      }}
    >
      {/* Header */}
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
            {currentDecision.title}
          </Typography>
          <Box display="flex" alignItems="center" gap={1} mt={0.5}>
            <Chip
              size="small"
              label={`Turn ${currentDecision.turnNumber}`}
              sx={{ bgcolor: 'rgba(255,255,255,0.2)', color: 'inherit' }}
            />
            <Chip
              size="small"
              label={currentDecision.decisionType.replace('_', ' ')}
              sx={{ bgcolor: 'rgba(255,255,255,0.2)', color: 'inherit' }}
            />
          </Box>
        </Box>
        <Box display="flex" alignItems="center" gap={2}>
          <CountdownTimer
            seconds={remainingSeconds}
            totalSeconds={currentDecision.timeoutSeconds}
          />
          <IconButton
            onClick={handleSkip}
            disabled={isSubmitting}
            size="small"
            sx={{ color: 'inherit' }}
            aria-label="Skip decision"
          >
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent dividers sx={{ p: 3 }}>
        {/* Error display */}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Description */}
        <Typography
          id="decision-dialog-description"
          variant="body1"
          color="text.secondary"
          sx={{ mb: 3 }}
        >
          {currentDecision.description}
        </Typography>

        {/* Narrative context */}
        {currentDecision.narrativeContext && (
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
              {currentDecision.narrativeContext}
            </Typography>
          </Box>
        )}

        {/* Negotiation result */}
        <Collapse in={isNegotiating && negotiationResult !== null}>
          <Alert
            severity={
              negotiationResult?.feasibility === 'accepted'
                ? 'success'
                : negotiationResult?.feasibility === 'minor_adjustment'
                  ? 'info'
                  : 'warning'
            }
            icon={<NegotiateIcon />}
            sx={{ mb: 3 }}
          >
            <Typography variant="subtitle2" fontWeight="bold">
              {negotiationResult?.feasibility === 'accepted'
                ? 'Action Accepted'
                : negotiationResult?.feasibility === 'minor_adjustment'
                  ? 'Adjustment Suggested'
                  : 'Alternatives Required'}
            </Typography>
            <Typography variant="body2">
              {negotiationResult?.explanation}
            </Typography>
            {negotiationResult?.adjustedAction && (
              <Typography
                variant="body2"
                sx={{ mt: 1, fontStyle: 'italic', color: 'text.secondary' }}
              >
                Suggested: "{negotiationResult.adjustedAction}"
              </Typography>
            )}
          </Alert>
        </Collapse>

        {/* Input mode toggle */}
        <Box display="flex" gap={1} mb={2}>
          <Button
            variant={inputMode === 'options' ? 'contained' : 'outlined'}
            size="small"
            onClick={() => setInputMode('options')}
            disabled={isNegotiating}
            startIcon={<CheckIcon />}
          >
            Choose Option
          </Button>
          <Button
            variant={inputMode === 'freetext' ? 'contained' : 'outlined'}
            size="small"
            onClick={() => setInputMode('freetext')}
            disabled={isNegotiating}
            startIcon={<EditIcon />}
          >
            Custom Action
          </Button>
        </Box>

        {/* Options grid */}
        <Fade in={inputMode === 'options' && !isNegotiating}>
          <Box sx={{ display: inputMode === 'options' && !isNegotiating ? 'block' : 'none' }}>
            <Grid container spacing={2}>
              {currentDecision.options.map((option) => (
                <Grid item xs={12} sm={6} key={option.optionId}>
                  <OptionCard
                    optionId={option.optionId}
                    label={option.label}
                    description={option.description}
                    icon={option.icon}
                    impactPreview={option.impactPreview}
                    isSelected={selectedOptionId === option.optionId}
                    onSelect={handleOptionSelect}
                    disabled={isSubmitting}
                  />
                </Grid>
              ))}
            </Grid>
          </Box>
        </Fade>

        {/* Free text input */}
        <Fade in={inputMode === 'freetext' && !isNegotiating}>
          <Box sx={{ display: inputMode === 'freetext' && !isNegotiating ? 'block' : 'none' }}>
            <TextField
              fullWidth
              multiline
              rows={3}
              variant="outlined"
              placeholder="Describe what you want the characters to do..."
              value={freeTextInput}
              onChange={handleFreeTextChange}
              disabled={isSubmitting}
              inputProps={{
                'aria-label': 'Custom action input',
                maxLength: 500,
              }}
              helperText={`${freeTextInput.length}/500 characters (minimum 5)`}
            />
          </Box>
        </Fade>

        {/* Negotiation alternatives */}
        <Collapse in={isNegotiating && negotiationResult?.alternatives?.length > 0}>
          <Box mt={2}>
            <Typography variant="subtitle2" gutterBottom>
              Alternative Actions:
            </Typography>
            <Grid container spacing={2}>
              {negotiationResult?.alternatives?.map((alt) => (
                <Grid item xs={12} sm={6} key={alt.optionId}>
                  <OptionCard
                    optionId={alt.optionId}
                    label={alt.label}
                    description={alt.description}
                    isSelected={selectedOptionId === alt.optionId}
                    onSelect={handleOptionSelect}
                    disabled={isSubmitting}
                  />
                </Grid>
              ))}
            </Grid>
          </Box>
        </Collapse>
      </DialogContent>

      {/* Actions */}
      <DialogActions sx={{ p: 2, gap: 1 }}>
        <Button
          onClick={handleSkip}
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
              onClick={handleInsistOriginal}
              disabled={isSubmitting}
            >
              Keep Original
            </Button>
            <Button
              variant="contained"
              onClick={handleAcceptNegotiation}
              disabled={isSubmitting}
              startIcon={isSubmitting ? <CircularProgress size={16} /> : <CheckIcon />}
            >
              Accept Suggestion
            </Button>
          </>
        ) : (
          <Button
            variant="contained"
            onClick={handleSubmit}
            disabled={!canSubmit || isSubmitting}
            startIcon={isSubmitting ? <CircularProgress size={16} /> : <SendIcon />}
          >
            Confirm
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
