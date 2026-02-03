import { create } from 'zustand';

export interface DecisionOption {
  optionId: number;
  label: string;
  description: string;
  icon?: string;
  impactPreview?: string;
}

export interface DecisionPoint {
  decisionId: string;
  decisionType: string;
  turnNumber: number;
  title: string;
  description: string;
  narrativeContext?: string;
  options: DecisionOption[];
  defaultOptionId?: number | null;
  timeoutSeconds: number;
  createdAt?: string;
  expiresAt?: string;
}

export interface NegotiationResult {
  decisionId: string;
  feasibility: 'minor_adjustment' | 'not_possible' | 'accepted';
  explanation: string;
  adjustedAction?: string;
  alternatives?: string[];
}

type InputMode = 'options' | 'freeText';

interface DecisionState {
  currentDecision: DecisionPoint | null;
  pauseState: string;
  selectedOptionId: number | null;
  freeTextInput: string;
  remainingSeconds: number;
  inputMode: InputMode;
  submitting: boolean;
  errorMessage: string | null;
  negotiationResult: NegotiationResult | null;
  setDecisionPoint: (decision: DecisionPoint) => void;
  clearDecisionPoint: () => void;
  selectOption: (optionId: number | null) => void;
  setInputMode: (mode: InputMode) => void;
  setFreeText: (text: string) => void;
  setRemainingSeconds: (seconds: number) => void;
  setSubmitting: (value: boolean) => void;
  setErrorMessage: (message: string | null) => void;
  setNegotiationResult: (result: NegotiationResult | null) => void;
}

export const useDecisionStore = create<DecisionState>((set) => ({
  currentDecision: null,
  pauseState: 'idle',
  selectedOptionId: null,
  freeTextInput: '',
  remainingSeconds: 0,
  inputMode: 'options',
  submitting: false,
  errorMessage: null,
  negotiationResult: null,
  setDecisionPoint: (decision) => {
    set({
      currentDecision: decision,
      pauseState: 'decision_required',
      selectedOptionId: decision.defaultOptionId ?? null,
      freeTextInput: '',
      remainingSeconds: decision.timeoutSeconds,
      inputMode: 'options',
      submitting: false,
      errorMessage: null,
      negotiationResult: null,
    });
  },
  clearDecisionPoint: () => {
    set({
      currentDecision: null,
      pauseState: 'idle',
      selectedOptionId: null,
      freeTextInput: '',
      remainingSeconds: 0,
      inputMode: 'options',
      submitting: false,
      errorMessage: null,
      negotiationResult: null,
    });
  },
  selectOption: (optionId) => {
    set({ selectedOptionId: optionId, inputMode: 'options' });
  },
  setInputMode: (mode) => {
    set({ inputMode: mode });
  },
  setFreeText: (text) => {
    set({ freeTextInput: text, inputMode: 'freeText' });
  },
  setRemainingSeconds: (seconds) => {
    set({ remainingSeconds: Math.max(seconds, 0) });
  },
  setSubmitting: (value) => {
    set({ submitting: value });
  },
  setErrorMessage: (message) => {
    set({ errorMessage: message });
  },
  setNegotiationResult: (result) => {
    set({ negotiationResult: result });
  },
}));
