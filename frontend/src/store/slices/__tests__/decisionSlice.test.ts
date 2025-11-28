/**
 * Decision Slice Tests
 *
 * Tests for the Redux slice managing decision point state.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { configureStore } from '@reduxjs/toolkit';
import decisionReducer, {
  setDecisionPoint,
  clearDecisionPoint,
  selectOption,
  setFreeTextInput,
  decrementCountdown,
  setNegotiationResult,
  clearError,
  addToHistory,
  type DecisionPoint,
  type DecisionState,
} from '../decisionSlice';

// Mock decision data
const mockDecision: DecisionPoint = {
  decisionId: 'test-decision-001',
  decisionType: 'character_choice',
  turnNumber: 5,
  title: 'Critical Decision Point',
  description: 'The story has reached a pivotal moment.',
  narrativeContext: 'Aria stands at the crossroads...',
  options: [
    {
      optionId: 1,
      label: 'Investigate Signal',
      description: 'Proceed with caution',
      icon: '🔍',
    },
    {
      optionId: 2,
      label: 'Evacuate Area',
      description: 'Prioritize safety',
      icon: '⚠️',
    },
  ],
  defaultOptionId: 1,
  timeoutSeconds: 120,
  dramaticTension: 8,
  emotionalIntensity: 7,
  createdAt: new Date().toISOString(),
  expiresAt: new Date(Date.now() + 120000).toISOString(),
};

function createTestStore(preloadedState?: Partial<DecisionState>) {
  return configureStore({
    reducer: {
      decision: decisionReducer,
    },
    preloadedState: preloadedState
      ? { decision: { ...getInitialState(), ...preloadedState } }
      : undefined,
  });
}

function getInitialState(): DecisionState {
  return {
    currentDecision: null,
    pauseState: 'running',
    isNegotiating: false,
    negotiationResult: null,
    remainingSeconds: 0,
    selectedOptionId: null,
    freeTextInput: '',
    isSubmitting: false,
    error: null,
    decisionHistory: [],
  };
}

describe('decisionSlice', () => {
  describe('Initial State', () => {
    it('has correct initial state', () => {
      const store = createTestStore();
      const state = store.getState().decision;

      expect(state.currentDecision).toBeNull();
      expect(state.pauseState).toBe('running');
      expect(state.isNegotiating).toBe(false);
      expect(state.negotiationResult).toBeNull();
      expect(state.remainingSeconds).toBe(0);
      expect(state.selectedOptionId).toBeNull();
      expect(state.freeTextInput).toBe('');
      expect(state.isSubmitting).toBe(false);
      expect(state.error).toBeNull();
      expect(state.decisionHistory).toEqual([]);
    });
  });

  describe('setDecisionPoint', () => {
    it('sets current decision', () => {
      const store = createTestStore();
      store.dispatch(setDecisionPoint(mockDecision));

      const state = store.getState().decision;
      expect(state.currentDecision).toEqual(mockDecision);
    });

    it('sets pause state to awaiting_input', () => {
      const store = createTestStore();
      store.dispatch(setDecisionPoint(mockDecision));

      const state = store.getState().decision;
      expect(state.pauseState).toBe('awaiting_input');
    });

    it('initializes remaining seconds from expiresAt', () => {
      const store = createTestStore();
      // Create decision with expiresAt exactly 120 seconds in the future
      const futureDecision = {
        ...mockDecision,
        expiresAt: new Date(Date.now() + 120000).toISOString(),
      };
      store.dispatch(setDecisionPoint(futureDecision));

      const state = store.getState().decision;
      // remainingSeconds is calculated from expiresAt - now, allowing ±2 sec margin
      expect(state.remainingSeconds).toBeGreaterThanOrEqual(118);
      expect(state.remainingSeconds).toBeLessThanOrEqual(120);
    });

    it('resets selection state and sets default option', () => {
      const store = createTestStore({
        selectedOptionId: 5,
        freeTextInput: 'test',
      });
      store.dispatch(setDecisionPoint(mockDecision));

      const state = store.getState().decision;
      // Sets to defaultOptionId from decision, not null
      expect(state.selectedOptionId).toBe(mockDecision.defaultOptionId);
      expect(state.freeTextInput).toBe('');
    });

    it('clears any previous error', () => {
      const store = createTestStore({
        error: 'Previous error',
      });
      store.dispatch(setDecisionPoint(mockDecision));

      const state = store.getState().decision;
      expect(state.error).toBeNull();
    });
  });

  describe('clearDecisionPoint', () => {
    it('clears current decision', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
      });
      store.dispatch(clearDecisionPoint());

      const state = store.getState().decision;
      expect(state.currentDecision).toBeNull();
    });

    it('resets pause state to running', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
      });
      store.dispatch(clearDecisionPoint());

      const state = store.getState().decision;
      expect(state.pauseState).toBe('running');
    });

    it('resets all selection state', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        selectedOptionId: 1,
        freeTextInput: 'test input',
        remainingSeconds: 60,
      });
      store.dispatch(clearDecisionPoint());

      const state = store.getState().decision;
      expect(state.selectedOptionId).toBeNull();
      expect(state.freeTextInput).toBe('');
      expect(state.remainingSeconds).toBe(0);
    });

    it('clears negotiation state', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        isNegotiating: true,
        negotiationResult: {
          feasibility: 'accepted',
          explanation: 'OK',
          adjustedAction: null,
          alternatives: [],
        },
      });
      store.dispatch(clearDecisionPoint());

      const state = store.getState().decision;
      expect(state.isNegotiating).toBe(false);
      expect(state.negotiationResult).toBeNull();
    });
  });

  describe('selectOption', () => {
    it('updates selectedOptionId', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
      });
      store.dispatch(selectOption(2));

      const state = store.getState().decision;
      expect(state.selectedOptionId).toBe(2);
    });

    it('allows changing selection', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        selectedOptionId: 1,
      });
      store.dispatch(selectOption(2));

      const state = store.getState().decision;
      expect(state.selectedOptionId).toBe(2);
    });

    it('does not clear free text input when option selected', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        freeTextInput: 'some text',
      });
      store.dispatch(selectOption(1));

      const state = store.getState().decision;
      // selectOption doesn't clear freeTextInput - that's handled by UI logic
      expect(state.freeTextInput).toBe('some text');
    });
  });

  describe('setFreeTextInput', () => {
    it('updates freeTextInput', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
      });
      store.dispatch(setFreeTextInput('Make the character run'));

      const state = store.getState().decision;
      expect(state.freeTextInput).toBe('Make the character run');
    });

    it('does not clear selected option when free text entered', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        selectedOptionId: 1,
      });
      store.dispatch(setFreeTextInput('Custom action'));

      const state = store.getState().decision;
      // setFreeTextInput doesn't clear selectedOptionId - that's handled by UI logic
      expect(state.selectedOptionId).toBe(1);
    });

    it('handles empty string', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        freeTextInput: 'previous text',
      });
      store.dispatch(setFreeTextInput(''));

      const state = store.getState().decision;
      expect(state.freeTextInput).toBe('');
    });
  });

  describe('decrementCountdown', () => {
    it('decrements remaining seconds by 1', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        remainingSeconds: 120,
      });
      store.dispatch(decrementCountdown());

      const state = store.getState().decision;
      expect(state.remainingSeconds).toBe(119);
    });

    it('does not go below 0', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        remainingSeconds: 0,
      });
      store.dispatch(decrementCountdown());

      const state = store.getState().decision;
      expect(state.remainingSeconds).toBe(0);
    });

    it('handles decrement at 1 second', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        remainingSeconds: 1,
      });
      store.dispatch(decrementCountdown());

      const state = store.getState().decision;
      expect(state.remainingSeconds).toBe(0);
    });
  });

  describe('setNegotiationResult', () => {
    it('sets negotiation result', () => {
      const result = {
        feasibility: 'minor_adjustment' as const,
        explanation: 'The action needs adjustment',
        adjustedAction: 'Modified action',
        alternatives: [],
      };

      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
      });
      store.dispatch(setNegotiationResult(result));

      const state = store.getState().decision;
      expect(state.negotiationResult).toEqual(result);
      expect(state.isNegotiating).toBe(true);
    });

    it('updates pause state to negotiating', () => {
      const result = {
        feasibility: 'alternative_required' as const,
        explanation: 'Cannot perform this action',
        adjustedAction: null,
        alternatives: [
          { optionId: 10, label: 'Alt 1', description: 'Alternative' },
        ],
      };

      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
      });
      store.dispatch(setNegotiationResult(result));

      const state = store.getState().decision;
      expect(state.pauseState).toBe('negotiating');
    });
  });

  describe('clearError', () => {
    it('clears error message', () => {
      const store = createTestStore({
        error: 'Previous error',
      });
      store.dispatch(clearError());

      const state = store.getState().decision;
      expect(state.error).toBeNull();
    });

    it('handles clearing when no error exists', () => {
      const store = createTestStore({
        error: null,
      });
      store.dispatch(clearError());

      const state = store.getState().decision;
      expect(state.error).toBeNull();
    });
  });

  describe('Pause State Transitions', () => {
    it('running -> awaiting_input on setDecisionPoint', () => {
      const store = createTestStore({ pauseState: 'running' });
      store.dispatch(setDecisionPoint(mockDecision));

      expect(store.getState().decision.pauseState).toBe('awaiting_input');
    });

    it('awaiting_input -> running on clearDecisionPoint', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
      });
      store.dispatch(clearDecisionPoint());

      expect(store.getState().decision.pauseState).toBe('running');
    });

    it('negotiating -> running on clearDecisionPoint', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'negotiating',
        isNegotiating: true,
      });
      store.dispatch(clearDecisionPoint());

      expect(store.getState().decision.pauseState).toBe('running');
      expect(store.getState().decision.isNegotiating).toBe(false);
    });
  });

  describe('Decision History', () => {
    it('adds decision to history via addToHistory', () => {
      const store = createTestStore({
        decisionHistory: [],
      });

      store.dispatch(addToHistory({
        decisionId: mockDecision.decisionId,
        turnNumber: 5,
        inputType: 'option',
        selectedOptionId: 1,
      }));

      const state = store.getState().decision;
      expect(state.decisionHistory.length).toBe(1);
      expect(state.decisionHistory[0].decisionId).toBe(mockDecision.decisionId);
      expect(state.decisionHistory[0].inputType).toBe('option');
    });

    it('clearDecisionPoint does not auto-add to history', () => {
      const store = createTestStore({
        currentDecision: mockDecision,
        pauseState: 'awaiting_input',
        selectedOptionId: 1,
        decisionHistory: [],
      });

      store.dispatch(clearDecisionPoint());

      const state = store.getState().decision;
      // clearDecisionPoint doesn't auto-add to history - handled by async thunks
      expect(state.decisionHistory.length).toBe(0);
    });

    it('maintains history with newest first (unshift)', () => {
      const store = createTestStore({
        decisionHistory: [],
      });

      store.dispatch(addToHistory({
        decisionId: 'decision-1',
        turnNumber: 1,
        inputType: 'option',
        selectedOptionId: 1,
      }));

      store.dispatch(addToHistory({
        decisionId: 'decision-2',
        turnNumber: 2,
        inputType: 'freetext',
        freeText: 'custom action',
      }));

      const state = store.getState().decision;
      expect(state.decisionHistory.length).toBe(2);
      // unshift means newest first
      expect(state.decisionHistory[0].decisionId).toBe('decision-2');
      expect(state.decisionHistory[1].decisionId).toBe('decision-1');
    });
  });
});
