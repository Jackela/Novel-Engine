/**
 * Brain Settings API
 *
 * BRAIN-033: Frontend Brain Settings
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
};
