/**
 * Brain Settings API
 *
 * BRAIN-033: Frontend Brain Settings
 * BRAIN-035A: Token Usage Analytics
 * API client for brain settings endpoints
 */

export interface APIKeysResponse {
  openai_key: string;
  anthropic_key: string;
  gemini_key: string;
  ollama_base_url: string | null;
  has_openai: boolean;
  has_anthropic: boolean;
  has_gemini: boolean;
}

// BRAIN-035A: Token Usage Analytics Types

export interface UsageSummaryResponse {
  total_tokens: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost: number;
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  avg_latency_ms: number;
  period_start: string | null;
  period_end: string | null;
}

export interface DailyStatsResponse {
  date: string;
  total_tokens: number;
  total_cost: number;
  total_requests: number;
  providers: Record<string, { tokens: number; cost: number; requests: number }>;
}

export interface ModelUsageResponse {
  provider: string;
  model_name: string;
  model_identifier: string;
  total_tokens: number;
  total_cost: number;
  total_requests: number;
}

export interface APIKeysRequest {
  openai_key?: string | null;
  anthropic_key?: string | null;
  gemini_key?: string | null;
  ollama_base_url?: string | null;
}

export interface RAGConfigResponse {
  enabled: boolean;
  max_chunks: number;
  score_threshold: number;
  context_token_limit: number;
  include_sources: boolean;
  chunk_size: number;
  chunk_overlap: number;
  hybrid_search_weight: number;
}

export interface RAGConfigRequest {
  enabled?: boolean;
  max_chunks?: number;
  score_threshold?: number;
  context_token_limit?: number;
  include_sources?: boolean;
  chunk_size?: number;
  chunk_overlap?: number;
  hybrid_search_weight?: number;
}

export interface KnowledgeBaseStatusResponse {
  total_entries: number;
  characters_count: number;
  lore_count: number;
  scenes_count: number;
  plotlines_count: number;
  last_sync: string | null;
  is_healthy: boolean;
}

export interface BrainSettingsResponse {
  api_keys: APIKeysResponse;
  rag_config: RAGConfigResponse;
  knowledge_base: KnowledgeBaseStatusResponse;
}

// BRAIN-035B-01: Model Pricing Comparison

export interface ModelPricingResponse {
  provider: string;
  model_name: string;
  display_name: string;
  cost_per_1m_input_tokens: number;
  cost_per_1m_output_tokens: number;
  max_context_tokens: number;
  max_output_tokens: number;
  deprecated: boolean;
}

// BRAIN-035B-04: Real-time Usage Counter

export type RealtimeUsageEventType =
  | 'session_start'
  | 'token_update'
  | 'session_complete'
  | 'session_state'
  | 'error';

export interface BaseRealtimeUsageEvent {
  type: RealtimeUsageEventType;
  timestamp: string;
}

export interface SessionStartEvent extends BaseRealtimeUsageEvent {
  type: 'session_start';
  session_id: string;
  provider: string;
  model_name: string;
}

export interface TokenUpdateEvent extends BaseRealtimeUsageEvent {
  type: 'token_update';
  session_id: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost: number;
}

export interface SessionCompleteEvent extends BaseRealtimeUsageEvent {
  type: 'session_complete';
  session_id: string;
  provider: string;
  model_name: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost: number;
  start_time: string;
  is_complete: boolean;
}

export interface SessionStateEvent extends BaseRealtimeUsageEvent {
  type: 'session_state';
  session_id: string;
  provider: string;
  model_name: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost: number;
  start_time: string;
  is_complete: boolean;
}

export interface ErrorEvent extends BaseRealtimeUsageEvent {
  type: 'error';
  message: string;
}

export type RealtimeUsageEvent =
  | SessionStartEvent
  | TokenUpdateEvent
  | SessionCompleteEvent
  | SessionStateEvent
  | ErrorEvent;

/**
 * Subscribe to real-time usage events via SSE
 * BRAIN-035B-04: Real-time Usage Counter
 *
 * Returns an EventSource that can be used with onmessage callback
 * and should be closed when no longer needed.
 */
function streamRealtimeUsage(
  onEvent: (event: RealtimeUsageEvent) => void,
  onError?: (error: Error) => void,
): EventSource {
  const eventSource = new EventSource('/api/brain/usage/stream');

  eventSource.onmessage = (e) => {
    try {
      const event = JSON.parse(e.data) as RealtimeUsageEvent;
      onEvent(event);
    } catch (error) {
      onError?.(error as Error);
    }
  };

  eventSource.onerror = (e) => {
    onError?.(new Error('SSE connection error'));
    // EventSource will automatically attempt to reconnect
  };

  return eventSource;
}

const API_BASE = '/api/brain/settings';

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || error.message || 'Request failed');
  }
  return response.json();
}

export const brainSettingsApi = {
  /**
   * Get all brain settings
   */
  async getSettings(): Promise<BrainSettingsResponse> {
    const response = await fetch(API_BASE);
    return handleResponse<BrainSettingsResponse>(response);
  },

  /**
   * Get API keys (masked)
   */
  async getAPIKeys(): Promise<APIKeysResponse> {
    const response = await fetch(`${API_BASE}/api-keys`);
    return handleResponse<APIKeysResponse>(response);
  },

  /**
   * Update API keys
   */
  async updateAPIKeys(request: APIKeysRequest): Promise<APIKeysResponse> {
    const response = await fetch(`${API_BASE}/api-keys`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    return handleResponse<APIKeysResponse>(response);
  },

  /**
   * Get RAG configuration
   */
  async getRAGConfig(): Promise<RAGConfigResponse> {
    const response = await fetch(`${API_BASE}/rag-config`);
    return handleResponse<RAGConfigResponse>(response);
  },

  /**
   * Update RAG configuration
   */
  async updateRAGConfig(request: RAGConfigRequest): Promise<RAGConfigResponse> {
    const response = await fetch(`${API_BASE}/rag-config`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    return handleResponse<RAGConfigResponse>(response);
  },

  /**
   * Get knowledge base status
   */
  async getKnowledgeBaseStatus(): Promise<KnowledgeBaseStatusResponse> {
    const response = await fetch(`${API_BASE}/knowledge-base`);
    return handleResponse<KnowledgeBaseStatusResponse>(response);
  },

  /**
   * Test API key connections
   */
  async testConnection(): Promise<Record<string, string>> {
    const response = await fetch(`${API_BASE}/test-connection`, {
      method: 'POST',
    });
    return handleResponse<Record<string, string>>(response);
  },

  // BRAIN-035A: Token Usage Analytics

  /**
   * Get token usage summary
   */
  async getUsageSummary(days: number = 30): Promise<UsageSummaryResponse> {
    const response = await fetch(`/api/brain/usage/summary?days=${days}`);
    return handleResponse<UsageSummaryResponse>(response);
  },

  /**
   * Get daily usage statistics
   */
  async getDailyUsage(days: number = 30): Promise<DailyStatsResponse[]> {
    const response = await fetch(`/api/brain/usage/daily?days=${days}`);
    return handleResponse<DailyStatsResponse[]>(response);
  },

  /**
   * Get usage breakdown by model
   */
  async getUsageByModel(): Promise<ModelUsageResponse[]> {
    const response = await fetch('/api/brain/usage/by-model');
    return handleResponse<ModelUsageResponse[]>(response);
  },

  /**
   * Get model pricing information
   * BRAIN-035B-01: Model Comparison Table
   */
  async getModelPricing(includeDeprecated = false, provider?: string): Promise<ModelPricingResponse[]> {
    const params = new URLSearchParams();
    if (includeDeprecated) params.append('include_deprecated', 'true');
    if (provider) params.append('provider', provider);

    const url = `/api/brain/models${params.toString() ? `?${params.toString()}` : ''}`;
    const response = await fetch(url);
    return handleResponse<ModelPricingResponse[]>(response);
  },

  /**
   * Export usage data as CSV file
   * BRAIN-035B-03: CSV Export for usage analytics
   */
  async exportUsageCsv(days: number = 30): Promise<void> {
    const url = `/api/brain/usage/export?days=${days}`;
    const response = await fetch(url);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || error.message || 'Export failed');
    }

    // Download the CSV file
    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = response.headers.get('Content-Disposition')?.match(/filename="(.+)"/)?.[1] || `usage_export_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  },

  /**
   * Subscribe to real-time usage events via SSE
   * BRAIN-035B-04: Real-time Usage Counter
   *
   * @param onEvent Callback for each usage event
   * @param onError Optional callback for errors
   * @returns EventSource that should be closed when done
   */
  streamRealtimeUsage(
    onEvent: (event: RealtimeUsageEvent) => void,
    onError?: (error: Error) => void,
  ): EventSource {
    return streamRealtimeUsage(onEvent, onError);
  },
};
