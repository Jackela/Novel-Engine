import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import { dashboardAPI } from '@/services/api/dashboardAPI';

export interface PerformanceMetrics {
  responseTime: number;
  errorRate: number;
  requestsPerSecond: number;
  activeUsers: number;
  systemLoad: number;
  memoryUsage: number;
  storageUsage: number;
  networkLatency: number;
}

export interface SystemStatus {
  overall: 'healthy' | 'warning' | 'error';
  database: 'healthy' | 'warning' | 'error';
  aiService: 'healthy' | 'warning' | 'error';
  memoryService: 'healthy' | 'warning' | 'error';
}

export interface ActivityEvent {
  id: string;
  type: 'character' | 'story' | 'system' | 'interaction';
  title: string;
  description: string;
  timestamp: string;
  characterName?: string;
  severity: 'low' | 'medium' | 'high';
}

export interface TurnStep {
  id: string;
  name: string;
  status: 'queued' | 'processing' | 'completed' | 'error';
  progress: number;
  duration?: number;
  character?: string;
}

export interface PipelineData {
  currentTurn: number;
  totalTurns: number;
  queueLength: number;
  averageProcessingTime: number;
  steps: TurnStep[];
}

export interface WorldNode {
  id: string;
  name: string;
  position: [number, number, number];
  color: string;
  size: number;
  activity: number;
}

export interface AnalyticsMetrics {
  storyQuality: number;
  engagement: number;
  coherence: number;
  complexity: number;
  dataPoints: number;
  metricsTracked: number;
  status: string;
  lastUpdated: string;
}

export interface DashboardState {
  // Connection status
  connected: boolean;
  lastUpdate: string | null;

  // Performance metrics
  metrics: PerformanceMetrics;
  systemStatus: SystemStatus;

  // Analytics metrics
  analytics: AnalyticsMetrics;

  // Real-time activity
  activities: ActivityEvent[];
  unreadActivityCount: number;

  // Turn pipeline
  pipeline: PipelineData;

  // World state
  worldNodes: WorldNode[];

  // UI state
  expandedAnalytics: boolean;
  quickActionsState: {
    isRunning: boolean;
    isPaused: boolean;
  };

  // Notifications
  notifications: Array<{
    id: string;
    message: string;
    type: 'info' | 'success' | 'warning' | 'error';
    timestamp: string;
    read: boolean;
  }>;
}

// Initial state with empty/default values - data should come from API
const initialState: DashboardState = {
  connected: false,
  lastUpdate: null,

  // Empty metrics - will be populated from /api/meta/system-status or SSE events
  metrics: {
    responseTime: 0,
    errorRate: 0,
    requestsPerSecond: 0,
    activeUsers: 0,
    systemLoad: 0,
    memoryUsage: 0,
    storageUsage: 0,
    networkLatency: 0,
  },

  // Default to unknown/warning until API confirms status
  systemStatus: {
    overall: 'warning',
    database: 'warning',
    aiService: 'warning',
    memoryService: 'warning',
  },

  // Analytics metrics - will be populated from /api/analytics/metrics
  analytics: {
    storyQuality: 0,
    engagement: 0,
    coherence: 0,
    complexity: 0,
    dataPoints: 0,
    metricsTracked: 0,
    status: 'unknown',
    lastUpdated: '',
  },

  activities: [],
  unreadActivityCount: 0,

  // Empty pipeline - will be populated from real-time events
  pipeline: {
    currentTurn: 0,
    totalTurns: 0,
    queueLength: 0,
    averageProcessingTime: 0,
    steps: [],
  },

  // Empty world nodes - will be populated from API
  worldNodes: [],

  expandedAnalytics: false,
  quickActionsState: {
    isRunning: false,
    isPaused: false,
  },

  notifications: [],
};

// Async thunk to fetch dashboard data from real API
export const fetchDashboardData = createAsyncThunk(
  'dashboard/fetchData',
  async (_, { rejectWithValue }) => {
    try {
      const [systemStatusRes, healthRes, orchestrationRes, analyticsRes] = await Promise.all([
        dashboardAPI.getSystemStatus(),
        dashboardAPI.getHealth(),
        dashboardAPI.getOrchestrationStatus(),
        dashboardAPI.getAnalyticsMetrics(),
      ]);

      // Try to get cache metrics, but don't fail if unavailable
      let cacheMetrics;
      try {
        const cacheRes = await dashboardAPI.getCacheMetrics();
        cacheMetrics = cacheRes.data;
      } catch {
        // Cache metrics are optional
      }

      const transformed = dashboardAPI.transformToMetrics(
        systemStatusRes.data,
        healthRes.data,
        cacheMetrics
      );

      // Transform orchestration response to pipeline data
      const orchestrationData = orchestrationRes.data;
      const pipelineData: PipelineData = orchestrationData.success && orchestrationData.data ? {
        currentTurn: orchestrationData.data.current_turn,
        totalTurns: orchestrationData.data.total_turns,
        queueLength: orchestrationData.data.queue_length,
        averageProcessingTime: orchestrationData.data.average_processing_time,
        steps: orchestrationData.data.steps.map((step) => ({
          id: step.id,
          name: step.name,
          status: step.status,
          progress: step.progress,
          ...(step.duration !== undefined ? { duration: step.duration } : {}),
          ...(step.character !== undefined ? { character: step.character } : {}),
        })),
      } : {
        currentTurn: 0,
        totalTurns: 0,
        queueLength: 0,
        averageProcessingTime: 0,
        steps: [],
      };

      // Transform analytics response
      const analyticsData = analyticsRes.data;
      const analytics: AnalyticsMetrics = analyticsData.success && analyticsData.data ? {
        storyQuality: analyticsData.data.story_quality,
        engagement: analyticsData.data.engagement,
        coherence: analyticsData.data.coherence,
        complexity: analyticsData.data.complexity,
        dataPoints: analyticsData.data.data_points,
        metricsTracked: analyticsData.data.metrics_tracked,
        status: analyticsData.data.status,
        lastUpdated: analyticsData.data.last_updated,
      } : {
        storyQuality: 0,
        engagement: 0,
        coherence: 0,
        complexity: 0,
        dataPoints: 0,
        metricsTracked: 0,
        status: 'unknown',
        lastUpdated: '',
      };

      return {
        ...transformed,
        connected: true,
        pipeline: pipelineData,
        analytics,
        orchestrationStatus: orchestrationData.data?.status || 'idle',
      };
    } catch (error) {
      return rejectWithValue(
        error instanceof Error ? error.message : 'Failed to fetch dashboard data'
      );
    }
  }
);

const dashboardSlice = createSlice({
  name: 'dashboard',
  initialState,
  reducers: {
    // Connection management
    setConnected: (state, action: PayloadAction<boolean>) => {
      state.connected = action.payload;
      state.lastUpdate = new Date().toISOString();
    },

    updateLastUpdate: (state) => {
      state.lastUpdate = new Date().toISOString();
    },

    // Performance metrics
    updateMetrics: (state, action: PayloadAction<Partial<PerformanceMetrics>>) => {
      state.metrics = { ...state.metrics, ...action.payload };
      state.lastUpdate = new Date().toISOString();
    },

    updateSystemStatus: (state, action: PayloadAction<Partial<SystemStatus>>) => {
      state.systemStatus = { ...state.systemStatus, ...action.payload };
    },

    // Analytics metrics
    updateAnalytics: (state, action: PayloadAction<Partial<AnalyticsMetrics>>) => {
      state.analytics = { ...state.analytics, ...action.payload };
    },

    // Activity management
    addActivity: (state, action: PayloadAction<ActivityEvent>) => {
      state.activities.unshift(action.payload);
      state.activities = state.activities.slice(0, 50); // Keep only 50 most recent
      state.unreadActivityCount += 1;
    },

    markActivitiesAsRead: (state) => {
      state.unreadActivityCount = 0;
    },

    // Pipeline management
    updatePipeline: (state, action: PayloadAction<Partial<PipelineData>>) => {
      state.pipeline = { ...state.pipeline, ...action.payload };
    },

    updatePipelineStep: (
      state,
      action: PayloadAction<{ stepId: string; updates: Partial<TurnStep> }>
    ) => {
      const step = state.pipeline.steps.find((s) => s.id === action.payload.stepId);
      if (step) {
        Object.assign(step, action.payload.updates);
      }
    },

    // World state management
    updateWorldNodes: (state, action: PayloadAction<WorldNode[]>) => {
      state.worldNodes = action.payload;
    },

    updateWorldNodeActivity: (
      state,
      action: PayloadAction<{ nodeId: string; activity: number }>
    ) => {
      const node = state.worldNodes.find((n) => n.id === action.payload.nodeId);
      if (node) {
        node.activity = action.payload.activity;
      }
    },

    // UI state management
    toggleAnalytics: (state) => {
      state.expandedAnalytics = !state.expandedAnalytics;
    },

    setAnalyticsExpanded: (state, action: PayloadAction<boolean>) => {
      state.expandedAnalytics = action.payload;
    },

    updateQuickActionsState: (
      state,
      action: PayloadAction<Partial<DashboardState['quickActionsState']>>
    ) => {
      state.quickActionsState = { ...state.quickActionsState, ...action.payload };
    },

    // Notifications
    addNotification: (
      state,
      action: PayloadAction<{
        message: string;
        type: 'info' | 'success' | 'warning' | 'error';
      }>
    ) => {
      const notification = {
        id: Date.now().toString(),
        message: action.payload.message,
        type: action.payload.type,
        timestamp: new Date().toISOString(),
        read: false,
      };
      state.notifications.unshift(notification);
      state.notifications = state.notifications.slice(0, 20); // Keep only 20 most recent
    },

    markNotificationAsRead: (state, action: PayloadAction<string>) => {
      const notification = state.notifications.find((n) => n.id === action.payload);
      if (notification) {
        notification.read = true;
      }
    },

    clearNotifications: (state) => {
      state.notifications = [];
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchDashboardData.pending, (state) => {
        // Keep existing data while loading, just update timestamp
        state.lastUpdate = new Date().toISOString();
      })
      .addCase(fetchDashboardData.fulfilled, (state, action) => {

        state.connected = action.payload.connected;
        state.metrics = action.payload.metrics;
        state.systemStatus = action.payload.systemStatus;
        state.lastUpdate = new Date().toISOString();

        // Update pipeline data from orchestration status
        if (action.payload.pipeline) {
          state.pipeline = action.payload.pipeline;
        }

        // Update analytics metrics
        if (action.payload.analytics) {
          state.analytics = action.payload.analytics;
        }

        // Update quick actions state based on orchestration status
        if (action.payload.orchestrationStatus) {
          state.quickActionsState.isRunning = action.payload.orchestrationStatus === 'running';
          state.quickActionsState.isPaused = action.payload.orchestrationStatus === 'paused';
        }
      })
      .addCase(fetchDashboardData.rejected, (state, action) => {
        state.connected = false;
        state.systemStatus = {
          overall: 'error',
          database: 'warning',
          aiService: 'error',
          memoryService: 'warning',
        };
        // Add notification about the error
        state.notifications.unshift({
          id: Date.now().toString(),
          message: `Failed to fetch dashboard data: ${action.payload || 'Unknown error'}`,
          type: 'error',
          timestamp: new Date().toISOString(),
          read: false,
        });
      });
  },
});

export const {
  setConnected,
  updateLastUpdate,
  updateMetrics,
  updateSystemStatus,
  updateAnalytics,
  addActivity,
  markActivitiesAsRead,
  updatePipeline,
  updatePipelineStep,
  updateWorldNodes,
  updateWorldNodeActivity,
  toggleAnalytics,
  setAnalyticsExpanded,
  updateQuickActionsState,
  addNotification,
  markNotificationAsRead,
  clearNotifications,
} = dashboardSlice.actions;

export default dashboardSlice.reducer;
