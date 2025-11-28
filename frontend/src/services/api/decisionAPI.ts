import type { AxiosResponse } from 'axios';
import { apiClient, handleAPIError } from './apiClient';
import type { BaseAPIResponse } from './apiClient';

// API Response types for decision endpoints
interface DecisionStatusResponse {
  success: boolean;
  data: {
    pause_state: string;
    pending_decision?: {
      decision_id: string;
      decision_type: string;
      turn_number: number;
      title: string;
      description: string;
      narrative_context: string;
      options: Array<{
        option_id: number;
        label: string;
        description: string;
        icon?: string;
        impact_preview?: string;
        is_default?: boolean;
      }>;
      default_option_id?: number;
      timeout_seconds: number;
      dramatic_tension: number;
      emotional_intensity: number;
      created_at: string;
      expires_at: string;
    };
    negotiation_result?: {
      decision_id: string;
      feasibility: string;
      explanation: string;
      adjusted_action?: string;
      alternatives: Array<{
        option_id: number;
        label: string;
        description: string;
      }>;
    };
  };
}

interface DecisionResponseResult {
  success: boolean;
  message: string;
  data?: {
    needs_negotiation: boolean;
    negotiation?: {
      decision_id: string;
      feasibility: string;
      explanation: string;
      adjusted_action?: string;
      alternatives: Array<{
        option_id: number;
        label: string;
        description: string;
      }>;
    };
  };
}

interface DecisionHistoryResponse {
  success: boolean;
  data: {
    total_decisions: number;
  };
}

// Request payload types
interface SubmitDecisionPayload {
  decisionId: string;
  inputType: 'option' | 'freetext';
  selectedOptionId?: number;
  freeText?: string;
}

interface ConfirmNegotiationPayload {
  decisionId: string;
  accepted: boolean;
  insistOriginal: boolean;
}

/**
 * Decision API service for user participatory interaction
 *
 * Endpoints:
 * - GET  /api/decision/status   - Get current decision system status
 * - POST /api/decision/respond  - Submit a decision response
 * - POST /api/decision/confirm  - Confirm/reject negotiation result
 * - POST /api/decision/skip     - Skip the current decision
 * - GET  /api/decision/history  - Get decision history
 */
export const decisionAPI = {
  /**
   * Get the current status of the decision system
   * Returns pause state, pending decision (if any), and negotiation state
   */
  getStatus: async (): Promise<AxiosResponse<DecisionStatusResponse>> => {
    try {
      return await apiClient.get('/api/decision/status');
    } catch (error) {
      return handleAPIError(error);
    }
  },

  /**
   * Submit a response to a pending decision point
   *
   * @param payload - Decision response with input type and value
   * @returns Response indicating if negotiation is needed
   */
  submitResponse: async (
    payload: SubmitDecisionPayload
  ): Promise<AxiosResponse<DecisionResponseResult>> => {
    try {
      return await apiClient.post('/api/decision/respond', {
        decision_id: payload.decisionId,
        input_type: payload.inputType,
        selected_option_id: payload.selectedOptionId,
        free_text: payload.freeText,
      });
    } catch (error) {
      return handleAPIError(error);
    }
  },

  /**
   * Confirm or reject a negotiation result
   *
   * @param payload - Negotiation confirmation with acceptance status
   */
  confirmNegotiation: async (
    payload: ConfirmNegotiationPayload
  ): Promise<AxiosResponse<BaseAPIResponse>> => {
    try {
      return await apiClient.post('/api/decision/confirm', {
        decision_id: payload.decisionId,
        accepted: payload.accepted,
        insist_original: payload.insistOriginal,
      });
    } catch (error) {
      return handleAPIError(error);
    }
  },

  /**
   * Skip the current decision point, using the default option
   *
   * @param decisionId - ID of the decision to skip
   */
  skipDecision: async (
    decisionId: string
  ): Promise<AxiosResponse<BaseAPIResponse>> => {
    try {
      return await apiClient.post('/api/decision/skip', {
        decision_id: decisionId,
      });
    } catch (error) {
      return handleAPIError(error);
    }
  },

  /**
   * Get the history of decision points in the current session
   */
  getHistory: async (): Promise<AxiosResponse<DecisionHistoryResponse>> => {
    try {
      return await apiClient.get('/api/decision/history');
    } catch (error) {
      return handleAPIError(error);
    }
  },
};

export default decisionAPI;
