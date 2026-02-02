import type { DecisionPoint, NegotiationResult } from './decisionStore';
import { useDecisionStore } from './decisionStore';

type DecisionAction =
  | { type: 'decision/setDecisionPoint'; payload: unknown }
  | { type: 'decision/selectOption'; payload: number | null }
  | { type: 'decision/setFreeText'; payload: string }
  | { type: 'decision/clearDecisionPoint' }
  | { type: 'decision/submitResponse/pending' }
  | { type: 'decision/submitResponse/rejected'; payload: string }
  | { type: 'decision/setNegotiationResult'; payload: unknown };

export function exposeDecisionStoreForE2E() {
  if (typeof window === 'undefined') {
    return;
  }

  const store = useDecisionStore;

  window.__REDUX_STORE__ = {
    dispatch: (action: { type: string; payload?: unknown }) => {
      const state = store.getState();
      switch (action.type as DecisionAction['type']) {
        case 'decision/setDecisionPoint':
          state.setDecisionPoint(action.payload as DecisionPoint);
          break;
        case 'decision/selectOption': {
          const payload = action.payload;
          state.selectOption(typeof payload === 'number' ? payload : null);
          break;
        }
        case 'decision/setFreeText': {
          const payload = action.payload;
          if (typeof payload === 'string') {
            state.setFreeText(payload);
          }
          break;
        }
        case 'decision/submitResponse/pending':
          state.setSubmitting(true);
          break;
        case 'decision/submitResponse/rejected': {
          state.setSubmitting(false);
          const payload = action.payload;
          state.setErrorMessage(typeof payload === 'string' ? payload : null);
          break;
        }
        case 'decision/setNegotiationResult':
          state.setNegotiationResult(action.payload as NegotiationResult | null);
          break;
        case 'decision/clearDecisionPoint':
          state.clearDecisionPoint();
          break;
        default:
          break;
      }
    },
    getState: () => {
      const decision = store.getState();
      return {
        decision: {
          currentDecision: decision.currentDecision,
          pauseState: decision.pauseState,
          selectedOptionId: decision.selectedOptionId,
          freeTextInput: decision.freeTextInput,
          remainingSeconds: decision.remainingSeconds,
        },
      };
    },
  };
}
