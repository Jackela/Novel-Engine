import { apiClient } from './apiClient';
import type { AxiosResponse } from 'axios';

// Types matching backend responses
export interface SystemStatusResponse {
  status: string;
  uptime: number;
  version: string;
  components: {
    api: string;
    simulation: string;
    cache: string;
  };
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  environment: string;
  version: string;
  config: {
    simulation_turns: number;
    max_agents: number;
    api_timeout: number;
  };
}

export interface CacheMetricsResponse {
  cache_hits: number;
  cache_misses: number;
  cache_size: number;
  cache_max_size: number;
  evictions: number;
  hit_rate: number;
}

// Analytics metrics types
export interface AnalyticsMetricsResponse {
  success: boolean;
  data: {
    story_quality: number;
    engagement: number;
    coherence: number;
    complexity: number;
    data_points: number;
    metrics_tracked: number;
    status: string;
    last_updated: string;
  };
}

// Orchestration/Pipeline types
export interface PipelineStep {
  id: string;
  name: string;
  status: 'queued' | 'processing' | 'completed' | 'error';
  progress: number;
  duration?: number;
  character?: string;
}

export interface OrchestrationStatusResponse {
  success: boolean;
  data: {
    current_turn: number;
    total_turns: number;
    queue_length: number;
    average_processing_time: number;
    status: 'idle' | 'running' | 'paused' | 'stopped';
    steps: PipelineStep[];
    last_updated?: string;
  };
}

// Dashboard API client
export const dashboardAPI = {
  /**
   * Get system status from /meta/system-status
   */
  getSystemStatus: async (): Promise<AxiosResponse<SystemStatusResponse>> => {
    return apiClient.get('/meta/system-status');
  },

  /**
   * Get health check from /health
   */
  getHealth: async (): Promise<AxiosResponse<HealthResponse>> => {
    return apiClient.get('/health');
  },

  /**
   * Get cache metrics from /cache/metrics
   */
  getCacheMetrics: async (): Promise<AxiosResponse<CacheMetricsResponse>> => {
    return apiClient.get('/cache/metrics');
  },

  /**
   * Get orchestration/pipeline status from /api/orchestration/status
   */
  getOrchestrationStatus: async (): Promise<AxiosResponse<OrchestrationStatusResponse>> => {
    return apiClient.get('/api/orchestration/status');
  },

  /**
   * Start orchestration pipeline
   */
  startOrchestration: async (params?: { start_turn?: number; total_turns?: number }): Promise<AxiosResponse<OrchestrationStatusResponse>> => {
    return apiClient.post('/api/orchestration/start', params);
  },

  /**
   * Stop orchestration pipeline
   */
  stopOrchestration: async (): Promise<AxiosResponse<OrchestrationStatusResponse>> => {
    return apiClient.post('/api/orchestration/stop');
  },

  /**
   * Get analytics metrics from /api/analytics/metrics
   */
  getAnalyticsMetrics: async (): Promise<AxiosResponse<AnalyticsMetricsResponse>> => {
    return apiClient.get('/api/analytics/metrics');
  },

  /**
   * Transform system status to dashboard metrics
   */
  transformToMetrics: (
    systemStatus: SystemStatusResponse,
    health: HealthResponse,
    cacheMetrics?: CacheMetricsResponse
  ) => {
    const isHealthy = systemStatus.status === 'operational';
    const components = systemStatus.components;

    return {
      metrics: {
        responseTime: systemStatus.uptime > 0 ? Math.min(200, Math.random() * 100 + 50) : 0, // Placeholder until real metrics
        errorRate: isHealthy ? 0 : 5,
        requestsPerSecond: systemStatus.uptime > 0 ? Math.random() * 30 + 10 : 0, // Placeholder
        activeUsers: 1, // Single user system for now
        systemLoad: components.simulation === 'running' ? 80 : 30,
        memoryUsage: cacheMetrics ? (cacheMetrics.cache_size / cacheMetrics.cache_max_size) * 100 : 50,
        storageUsage: 30, // Placeholder
        networkLatency: Math.random() * 20 + 5, // Placeholder
      },
      systemStatus: {
        overall: isHealthy ? 'healthy' as const : 'warning' as const,
        database: 'healthy' as const, // File-based, always available
        aiService: components.api === 'online' ? 'healthy' as const : 'error' as const,
        memoryService: components.cache === 'available' ? 'healthy' as const : 'warning' as const,
      },
    };
  },
};

export default dashboardAPI;
