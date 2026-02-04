/**
 * Routing Configuration API
 *
 * BRAIN-028B: Model Routing Configuration
 * API client for model routing configuration endpoints
 */

interface TaskRoutingRuleSchema {
  task_type: string;
  provider: string;
  model_name: string;
  temperature: number | null;
  max_tokens: number | null;
  priority: number;
  enabled: boolean;
}

interface RoutingConstraintsSchema {
  max_cost_per_1m_tokens: number | null;
  max_latency_ms: number | null;
  preferred_providers: string[];
  blocked_providers: string[];
  require_capabilities: string[];
}

interface CircuitBreakerRuleSchema {
  model_key: string;
  failure_threshold: number;
  timeout_seconds: number;
  enabled: boolean;
}

export interface RoutingConfigResponse {
  workspace_id: string;
  scope: string;
  task_rules: TaskRoutingRuleSchema[];
  constraints: RoutingConstraintsSchema | null;
  circuit_breaker_rules: CircuitBreakerRuleSchema[];
  enable_circuit_breaker: boolean;
  enable_fallback: boolean;
  created_at: string;
  updated_at: string;
  version: number;
}

export interface RoutingStatsResponse {
  total_decisions: number;
  fallback_count: number;
  fallback_rate: number;
  reason_counts: Record<string, number>;
  provider_counts: Record<string, number>;
  avg_routing_time_ms: number;
  open_circuits: Array<{
    model: string;
    state: string;
    failure_count: number;
  }>;
  total_circuits: number;
}

interface RoutingConfigUpdateRequest {
  task_rules?: TaskRoutingRuleSchema[] | null;
  constraints?: RoutingConstraintsSchema | null;
  circuit_breaker_rules?: CircuitBreakerRuleSchema[] | null;
  enable_circuit_breaker?: boolean;
  enable_fallback?: boolean;
}

const API_BASE = '/api/routing';

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || error.message || 'Request failed');
  }
  return response.json();
}

export const routingApi = {
  /**
   * Get routing configuration for a workspace (or global if not specified)
   */
  async getConfig(workspaceId?: string): Promise<RoutingConfigResponse> {
    const params = workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : '';
    const response = await fetch(`${API_BASE}/config${params}`);
    return handleResponse<RoutingConfigResponse>(response);
  },

  /**
   * Get global routing configuration
   */
  async getGlobalConfig(): Promise<RoutingConfigResponse> {
    const response = await fetch(`${API_BASE}/config/global`);
    return handleResponse<RoutingConfigResponse>(response);
  },

  /**
   * List all workspace routing configurations
   */
  async listConfigs(): Promise<RoutingConfigResponse[]> {
    const response = await fetch(`${API_BASE}/config/list`);
    return handleResponse<RoutingConfigResponse[]>(response);
  },

  /**
   * Update routing configuration
   */
  async updateConfig(
    workspaceId: string | undefined,
    updates: RoutingConfigUpdateRequest
  ): Promise<RoutingConfigResponse> {
    const params = workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : '';
    const response = await fetch(`${API_BASE}/config${params}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    return handleResponse<RoutingConfigResponse>(response);
  },

  /**
   * Reset routing configuration to defaults
   */
  async resetConfig(workspaceId: string): Promise<RoutingConfigResponse> {
    const response = await fetch(`${API_BASE}/config/reset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workspace_id: workspaceId }),
    });
    return handleResponse<RoutingConfigResponse>(response);
  },

  /**
   * Delete routing configuration for a workspace
   */
  async deleteConfig(workspaceId: string): Promise<void> {
    const response = await fetch(`${API_BASE}/config?workspace_id=${encodeURIComponent(workspaceId)}`, {
      method: 'DELETE',
    });
    if (!response.ok && response.status !== 204) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || 'Delete failed');
    }
  },

  /**
   * Get routing statistics
   */
  async getStats(): Promise<RoutingStatsResponse> {
    const response = await fetch(`${API_BASE}/stats`);
    return handleResponse<RoutingStatsResponse>(response);
  },

  /**
   * Get circuit breaker state for a model
   */
  async getCircuitBreakerState(modelKey: string): Promise<Record<string, unknown>> {
    const response = await fetch(`${API_BASE}/circuit-breaker/${encodeURIComponent(modelKey)}`);
    return handleResponse<Record<string, unknown>>(response);
  },

  /**
   * Reset circuit breaker for a model
   */
  async resetCircuitBreaker(modelKey: string): Promise<{ status: string; model_key: string }> {
    const response = await fetch(`${API_BASE}/circuit-breaker/${encodeURIComponent(modelKey)}/reset`, {
      method: 'POST',
    });
    return handleResponse<{ status: string; model_key: string }>(response);
  },
};
