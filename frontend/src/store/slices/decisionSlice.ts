import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import { decisionAPI } from '@/services/api/decisionAPI';

// Decision point types from backend
export type DecisionPointType =
  | 'turning_point'
  | 'crisis'
  | 'climax'
  | 'revelation'
  | 'character_choice'
  | 'relationship_change'
  | 'conflict_escalation'
  | 'transformation';

export type FeasibilityResult =
  | 'accepted'
  | 'minor_adjustment'
  | 'alternative_required'
  | 'rejected';

export type PauseState = 'running' | 'paused' | 'awaiting_input' | 'negotiating';

export interface DecisionOption {
  optionId: number;
  label: string;
  description: string;
  icon?: string;
  impactPreview?: string;
  isDefault?: boolean;
}

export interface DecisionPoint {
  decisionId: string;
  decisionType: DecisionPointType;
  turnNumber: number;
  title: string;
  description: string;
  narrativeContext: string;
  options: DecisionOption[];
  defaultOptionId?: number;
  timeoutSeconds: number;
  dramaticTension: number;
  emotionalIntensity: number;
  createdAt: string;
  expiresAt: string;
}

export interface NegotiationResult {
  decisionId: string;
  feasibility: FeasibilityResult;
  explanation: string;
  adjustedAction?: string;
  alternatives: DecisionOption[];
}

export interface DecisionState {
  // Current decision point (if any)
  currentDecision: DecisionPoint | null;

  // Pause state
  pauseState: PauseState;

  // Negotiation state
  isNegotiating: boolean;
  negotiationResult: NegotiationResult | null;

  // Countdown
  remainingSeconds: number;

  // User input
  selectedOptionId: number | null;
  freeTextInput: string;

  // History
  decisionHistory: Array<{
    decisionId: string;
    turnNumber: number;
    inputType: 'option' | 'freetext' | 'skipped';
    selectedOptionId?: number;
    freeText?: string;
    timestamp: string;
  }>;

  // Loading states
  isSubmitting: boolean;
  isLoading: boolean;
  error: string | null;
}

const DECISION_TYPES: DecisionPointType[] = [
  'turning_point',
  'crisis',
  'climax',
  'revelation',
  'character_choice',
  'relationship_change',
  'conflict_escalation',
  'transformation',
];

const PAUSE_STATES: PauseState[] = ['running', 'paused', 'awaiting_input', 'negotiating'];

const FEASIBILITY_RESULTS: FeasibilityResult[] = [
  'accepted',
  'minor_adjustment',
  'alternative_required',
  'rejected',
];

const asString = (value: unknown, fallback = ''): string =>
  typeof value === 'string' ? value : fallback;

const asNumber = (value: unknown, fallback = 0): number => {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return fallback;
};

const asPauseState = (value: unknown): PauseState =>
  PAUSE_STATES.includes(value as PauseState) ? (value as PauseState) : 'running';

const asDecisionPointType = (value: unknown): DecisionPointType =>
  DECISION_TYPES.includes(value as DecisionPointType)
    ? (value as DecisionPointType)
    : 'turning_point';

const asFeasibilityResult = (value: unknown): FeasibilityResult =>
  FEASIBILITY_RESULTS.includes(value as FeasibilityResult)
    ? (value as FeasibilityResult)
    : 'accepted';

const normalizeDecisionOption = (opt: unknown, fallbackIndex: number): DecisionOption | null => {
  if (!opt || typeof opt !== 'object') return null;

  const option = opt as Record<string, unknown>;
  const optionId = asNumber(option.option_id, fallbackIndex);
  const label = asString(option.label, `Option ${fallbackIndex}`);
  const description = asString(option.description);

  return {
    optionId,
    label,
    description,
    ...(typeof option.icon === 'string' ? { icon: option.icon } : {}),
    ...(typeof option.impact_preview === 'string' ? { impactPreview: option.impact_preview } : {}),
    ...(typeof option.is_default === 'boolean' ? { isDefault: option.is_default } : {}),
  };
};

const initialState: DecisionState = {
  currentDecision: null,
  pauseState: 'running',
  isNegotiating: false,
  negotiationResult: null,
  remainingSeconds: 0,
  selectedOptionId: null,
  freeTextInput: '',
  decisionHistory: [],
  isSubmitting: false,
  isLoading: false,
  error: null,
};

// Async thunks
export const fetchDecisionStatus = createAsyncThunk(
  'decision/fetchStatus',
  async (_, { rejectWithValue }) => {
    try {
      const response = await decisionAPI.getStatus();
      return response.data;
    } catch (error) {
      return rejectWithValue(
        error instanceof Error ? error.message : 'Failed to fetch decision status'
      );
    }
  }
);

export const submitDecisionResponse = createAsyncThunk(
  'decision/submitResponse',
  async (
    payload: {
      decisionId: string;
      inputType: 'option' | 'freetext';
      selectedOptionId?: number;
      freeText?: string;
    },
    { rejectWithValue }
  ) => {
    try {
      const response = await decisionAPI.submitResponse(payload);
      return response.data;
    } catch (error) {
      return rejectWithValue(
        error instanceof Error ? error.message : 'Failed to submit decision'
      );
    }
  }
);

export const confirmNegotiation = createAsyncThunk(
  'decision/confirmNegotiation',
  async (
    payload: {
      decisionId: string;
      accepted: boolean;
      insistOriginal: boolean;
    },
    { rejectWithValue }
  ) => {
    try {
      const response = await decisionAPI.confirmNegotiation(payload);
      return response.data;
    } catch (error) {
      return rejectWithValue(
        error instanceof Error ? error.message : 'Failed to confirm negotiation'
      );
    }
  }
);

export const skipDecision = createAsyncThunk(
  'decision/skip',
  async (decisionId: string, { rejectWithValue }) => {
    try {
      const response = await decisionAPI.skipDecision(decisionId);
      return response.data;
    } catch (error) {
      return rejectWithValue(
        error instanceof Error ? error.message : 'Failed to skip decision'
      );
    }
  }
);

const decisionSlice = createSlice({
  name: 'decision',
  initialState,
  reducers: {
    // Set decision point from SSE event
    setDecisionPoint: (state, action: PayloadAction<DecisionPoint>) => {
      state.currentDecision = action.payload;
      state.pauseState = 'awaiting_input';
      state.selectedOptionId = action.payload.defaultOptionId ?? null;
      state.freeTextInput = '';
      state.isNegotiating = false;
      state.negotiationResult = null;
      state.error = null;

      // Calculate remaining seconds with validation
      const expiresAt = new Date(action.payload.expiresAt);
      const expiresAtMs = expiresAt.getTime();
      const now = Date.now();

      // Handle invalid expiresAt by falling back to timeoutSeconds
      if (isNaN(expiresAtMs)) {
        state.remainingSeconds = action.payload.timeoutSeconds || 30;
      } else {
        state.remainingSeconds = Math.max(0, Math.floor((expiresAtMs - now) / 1000));
      }
    },

    // Clear decision point (resolved/expired)
    clearDecisionPoint: (state) => {
      state.currentDecision = null;
      state.pauseState = 'running';
      state.selectedOptionId = null;
      state.freeTextInput = '';
      state.isNegotiating = false;
      state.negotiationResult = null;
      state.remainingSeconds = 0;
    },

    // Update countdown
    decrementCountdown: (state) => {
      if (state.remainingSeconds > 0) {
        state.remainingSeconds -= 1;
      }
    },

    // Set remaining seconds directly
    setRemainingSeconds: (state, action: PayloadAction<number>) => {
      state.remainingSeconds = action.payload;
    },

    // User selects an option
    selectOption: (state, action: PayloadAction<number>) => {
      state.selectedOptionId = action.payload;
    },

    // User updates free text input
    setFreeTextInput: (state, action: PayloadAction<string>) => {
      state.freeTextInput = action.payload;
    },

    // Set negotiation result from API response
    setNegotiationResult: (state, action: PayloadAction<NegotiationResult>) => {
      state.isNegotiating = true;
      state.negotiationResult = action.payload;
      state.pauseState = 'negotiating';
    },

    // Update pause state
    setPauseState: (state, action: PayloadAction<PauseState>) => {
      state.pauseState = action.payload;
    },

    // Add to decision history
    addToHistory: (
      state,
      action: PayloadAction<{
        decisionId: string;
        turnNumber: number;
        inputType: 'option' | 'freetext' | 'skipped';
        selectedOptionId?: number;
        freeText?: string;
      }>
    ) => {
      state.decisionHistory.unshift({
        ...action.payload,
        timestamp: new Date().toISOString(),
      });
      // Keep only last 20 decisions
      state.decisionHistory = state.decisionHistory.slice(0, 20);
    },

    // Clear error
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // fetchDecisionStatus
      .addCase(fetchDecisionStatus.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(fetchDecisionStatus.fulfilled, (state, action) => {
        state.isLoading = false;
        const payloadData = action.payload?.data as Record<string, unknown> | undefined;
        state.pauseState = asPauseState(payloadData?.pause_state);

        const pending = payloadData?.pending_decision as Record<string, unknown> | undefined;
        if (pending) {
          const options = Array.isArray(pending.options)
            ? pending.options
                .map((opt, index) => normalizeDecisionOption(opt, index + 1))
                .filter((opt): opt is DecisionOption => !!opt)
            : [];
          const defaultOptionId =
            typeof pending.default_option_id === 'number' ? pending.default_option_id : undefined;

          state.currentDecision = {
            decisionId: asString(pending.decision_id),
            decisionType: asDecisionPointType(pending.decision_type),
            turnNumber: asNumber(pending.turn_number),
            title: asString(pending.title, 'Decision'),
            description: asString(pending.description),
            narrativeContext: asString(pending.narrative_context),
            options,
            ...(defaultOptionId !== undefined ? { defaultOptionId } : {}),
            timeoutSeconds: asNumber(pending.timeout_seconds),
            dramaticTension: asNumber(pending.dramatic_tension),
            emotionalIntensity: asNumber(pending.emotional_intensity),
            createdAt: asString(pending.created_at),
            expiresAt: asString(pending.expires_at),
          };
        }
      })
      .addCase(fetchDecisionStatus.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })

      // submitDecisionResponse
      .addCase(submitDecisionResponse.pending, (state) => {
        state.isSubmitting = true;
        state.error = null;
      })
      .addCase(submitDecisionResponse.fulfilled, (state, action) => {
        state.isSubmitting = false;
        const payloadData = action.payload?.data as Record<string, unknown> | undefined;
        const negotiation = payloadData?.negotiation as Record<string, unknown> | undefined;

        if (payloadData?.needs_negotiation && negotiation) {
          // Negotiation required
          state.isNegotiating = true;
          state.negotiationResult = {
            decisionId: asString(negotiation.decision_id),
            feasibility: asFeasibilityResult(negotiation.feasibility),
            explanation: asString(negotiation.explanation),
            ...(typeof negotiation.adjusted_action === 'string'
              ? { adjustedAction: negotiation.adjusted_action }
              : {}),
            alternatives: Array.isArray(negotiation.alternatives)
              ? negotiation.alternatives
                  .map((alt, index) => normalizeDecisionOption(alt, index + 1))
                  .filter((opt): opt is DecisionOption => !!opt)
              : [],
          };
          state.pauseState = 'negotiating';
        } else {
          // Decision accepted
          if (state.currentDecision) {
            state.decisionHistory.unshift({
              decisionId: state.currentDecision.decisionId,
              turnNumber: state.currentDecision.turnNumber,
              inputType: state.selectedOptionId !== null ? 'option' : 'freetext',
              ...(state.selectedOptionId !== null ? { selectedOptionId: state.selectedOptionId } : {}),
              ...(state.freeTextInput ? { freeText: state.freeTextInput } : {}),
              timestamp: new Date().toISOString(),
            });
          }
          state.currentDecision = null;
          state.pauseState = 'running';
          state.selectedOptionId = null;
          state.freeTextInput = '';
          state.remainingSeconds = 0;
        }
      })
      .addCase(submitDecisionResponse.rejected, (state, action) => {
        state.isSubmitting = false;
        state.error = action.payload as string;
      })

      // confirmNegotiation
      .addCase(confirmNegotiation.pending, (state) => {
        state.isSubmitting = true;
      })
      .addCase(confirmNegotiation.fulfilled, (state) => {
        state.isSubmitting = false;
        if (state.currentDecision) {
          state.decisionHistory.unshift({
            decisionId: state.currentDecision.decisionId,
            turnNumber: state.currentDecision.turnNumber,
            inputType: 'freetext',
            freeText: state.freeTextInput,
            timestamp: new Date().toISOString(),
          });
        }
        state.currentDecision = null;
        state.pauseState = 'running';
        state.isNegotiating = false;
        state.negotiationResult = null;
        state.freeTextInput = '';
        state.remainingSeconds = 0;
      })
      .addCase(confirmNegotiation.rejected, (state, action) => {
        state.isSubmitting = false;
        state.error = action.payload as string;
      })

      // skipDecision
      .addCase(skipDecision.pending, (state) => {
        state.isSubmitting = true;
      })
      .addCase(skipDecision.fulfilled, (state) => {
        state.isSubmitting = false;
        if (state.currentDecision) {
          state.decisionHistory.unshift({
            decisionId: state.currentDecision.decisionId,
            turnNumber: state.currentDecision.turnNumber,
            inputType: 'skipped',
            timestamp: new Date().toISOString(),
          });
        }
        state.currentDecision = null;
        state.pauseState = 'running';
        state.selectedOptionId = null;
        state.freeTextInput = '';
        state.remainingSeconds = 0;
      })
      .addCase(skipDecision.rejected, (state, action) => {
        state.isSubmitting = false;
        state.error = action.payload as string;
      });
  },
});

export const {
  setDecisionPoint,
  clearDecisionPoint,
  decrementCountdown,
  setRemainingSeconds,
  selectOption,
  setFreeTextInput,
  setNegotiationResult,
  setPauseState,
  addToHistory,
  clearError,
} = decisionSlice.actions;

export default decisionSlice.reducer;
