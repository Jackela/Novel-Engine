import { createSlice, PayloadAction } from '@reduxjs/toolkit';

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

export interface DashboardState {
  // Connection status
  connected: boolean;
  lastUpdate: string | null;
  
  // Performance metrics
  metrics: PerformanceMetrics;
  systemStatus: SystemStatus;
  
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

const initialState: DashboardState = {
  connected: false,
  lastUpdate: null,
  
  metrics: {
    responseTime: 145,
    errorRate: 0.2,
    requestsPerSecond: 23.5,
    activeUsers: 127,
    systemLoad: 68,
    memoryUsage: 74,
    storageUsage: 42,
    networkLatency: 12,
  },
  
  systemStatus: {
    overall: 'healthy',
    database: 'healthy',
    aiService: 'healthy',
    memoryService: 'healthy',
  },
  
  activities: [],
  unreadActivityCount: 0,
  
  pipeline: {
    currentTurn: 47,
    totalTurns: 150,
    queueLength: 3,
    averageProcessingTime: 2.3,
    steps: [
      {
        id: 'input',
        name: 'Input Processing',
        status: 'completed',
        progress: 100,
        duration: 0.5,
        character: 'Aria Shadowbane',
      },
      {
        id: 'context',
        name: 'Context Analysis',
        status: 'completed',
        progress: 100,
        duration: 1.2,
      },
      {
        id: 'ai_generation',
        name: 'AI Response Generation',
        status: 'processing',
        progress: 73,
        character: 'Merchant Aldric',
      },
      {
        id: 'validation',
        name: 'Response Validation',
        status: 'queued',
        progress: 0,
      },
      {
        id: 'output',
        name: 'Output Delivery',
        status: 'queued',
        progress: 0,
      },
    ],
  },
  
  worldNodes: [
    {
      id: 'hub',
      name: 'Central Hub',
      position: [0, 0, 0],
      color: '#FF6B6B',
      size: 0.3,
      activity: 1.0,
    },
    {
      id: 'forest',
      name: 'Forest Realm',
      position: [2, 1, -1],
      color: '#4ECDC4',
      size: 0.2,
      activity: 0.7,
    },
    {
      id: 'caves',
      name: 'Crystal Caves',
      position: [-1.5, -0.5, 2],
      color: '#45B7D1',
      size: 0.25,
      activity: 0.5,
    },
  ],
  
  expandedAnalytics: false,
  quickActionsState: {
    isRunning: false,
    isPaused: false,
  },
  
  notifications: [],
};

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
});

export const {
  setConnected,
  updateLastUpdate,
  updateMetrics,
  updateSystemStatus,
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