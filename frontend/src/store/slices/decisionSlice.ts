import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import { decisionAPI } from '../../services/api/decisionAPI';

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

      // Calculate remaining seconds
      const expiresAt = new Date(action.payload.expiresAt).getTime();
      const now = Date.now();
      state.remainingSeconds = Math.max(0, Math.floor((expiresAt - now) / 1000));
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
        if (action.payload?.data) {
          const data = action.payload.data;
          state.pauseState = data.pause_state || 'running';
          if (data.pending_decision) {
            // Transform snake_case to camelCase
            state.currentDecision = {
              decisionId: data.pending_decision.decision_id,
              decisionType: data.pending_decision.decision_type,
              turnNumber: data.pending_decision.turn_number,
              title: data.pending_decision.title,
              description: data.pending_decision.description,
              narrativeContext: data.pending_decision.narrative_context,
              options: data.pending_decision.options.map((opt: Record<string, unknown>) => ({
                optionId: opt.option_id,
                label: opt.label,
                description: opt.description,
                icon: opt.icon,
                impactPreview: opt.impact_preview,
                isDefault: opt.is_default,
              })),
              defaultOptionId: data.pending_decision.default_option_id,
              timeoutSeconds: data.pending_decision.timeout_seconds,
              dramaticTension: data.pending_decision.dramatic_tension,
              emotionalIntensity: data.pending_decision.emotional_intensity,
              createdAt: data.pending_decision.created_at,
              expiresAt: data.pending_decision.expires_at,
            };
          }
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
        if (action.payload?.data?.needs_negotiation) {
          // Negotiation required
          const negData = action.payload.data.negotiation;
          state.isNegotiating = true;
          state.negotiationResult = {
            decisionId: negData.decision_id,
            feasibility: negData.feasibility,
            explanation: negData.explanation,
            adjustedAction: negData.adjusted_action,
            alternatives: negData.alternatives?.map((alt: Record<string, unknown>) => ({
              optionId: alt.option_id,
              label: alt.label,
              description: alt.description,
            })) || [],
          };
          state.pauseState = 'negotiating';
        } else {
          // Decision accepted
          if (state.currentDecision) {
            state.decisionHistory.unshift({
              decisionId: state.currentDecision.decisionId,
              turnNumber: state.currentDecision.turnNumber,
              inputType: state.selectedOptionId !== null ? 'option' : 'freetext',
              selectedOptionId: state.selectedOptionId ?? undefined,
              freeText: state.freeTextInput || undefined,
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
