// Novel Engine Frontend Types
// Comprehensive type definitions for the creative platform

export interface Character {
  id: string;
  name: string;
  faction: string;
  role: string;
  description: string;
  stats: CharacterStats;
  equipment: Equipment[];
  relationships: Relationship[];
  createdAt: Date;
  updatedAt: Date;
}

export interface CharacterStats {
  strength: number;
  dexterity: number;
  intelligence: number;
  willpower: number;
  perception: number;
  charisma: number;
}

export interface Equipment {
  id: string;
  name: string;
  type: string;
  description: string;
  condition: number;
}

export interface Relationship {
  targetCharacterId: string;
  type: 'ally' | 'enemy' | 'neutral' | 'mentor' | 'rival';
  strength: number;
  description: string;
}

export interface StoryProject {
  id: string;
  title: string;
  description: string;
  characters: string[]; // character IDs
  settings: StorySettings;
  status: 'draft' | 'generating' | 'completed' | 'exported';
  createdAt: Date;
  updatedAt: Date;
  storyContent?: string;
  metadata: ProjectMetadata;
}

export interface StorySettings {
  turns: number;
  narrativeStyle: 'epic' | 'detailed' | 'concise';
  genre: string;
  tone: 'grimdark' | 'heroic' | 'tactical' | 'dramatic';
  environment: string;
  objectives: string[];
}

export interface ProjectMetadata {
  totalTurns: number;
  generationTime: number;
  wordCount: number;
  participantCount: number;
  tags: string[];
}

export interface AgentInteraction {
  id: string;
  characterId: string;
  timestamp: Date;
  actionType: string;
  content: string;
  reasoning: string;
  confidence: number;
}

export interface GenerationSession {
  id: string;
  projectId: string;
  status: 'initializing' | 'running' | 'paused' | 'completed' | 'error';
  currentTurn: number;
  totalTurns: number;
  interactions: AgentInteraction[];
  startTime: Date;
  endTime?: Date;
  performance: SessionPerformance;
}

export interface SessionPerformance {
  averageResponseTime: number;
  totalTokensUsed: number;
  cacheHitRate: number;
  errorRate: number;
}

export interface SystemStatus {
  api: 'healthy' | 'degraded' | 'offline';
  agents: AgentStatus[];
  performance: SystemPerformance;
  version: string;
  uptime: number;
}

export interface AgentStatus {
  name: string;
  status: 'active' | 'idle' | 'error';
  lastActivity: Date;
  taskQueue: number;
}

export interface SystemPerformance {
  memoryUsage: number;
  cpuUsage: number;
  activeConnections: number;
  requestsPerMinute: number;
}

export interface CreationTemplate {
  id: string;
  name: string;
  description: string;
  category: 'character' | 'story' | 'setting';
  template: any;
  isDefault: boolean;
}

export interface ExportOptions {
  format: 'markdown' | 'pdf' | 'docx' | 'epub';
  includeMetadata: boolean;
  includeCharacterSheets: boolean;
  includeGenerationLog: boolean;
}

// API Response Types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  errors?: string[];
  timestamp: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasNext: boolean;
  hasPrevious: boolean;
}

// UI State Types
export interface UIState {
  currentPage: string;
  isLoading: boolean;
  notifications: Notification[];
  selectedProject?: string;
  selectedCharacters: string[];
}

export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: Date;
  isRead: boolean;
  autoHide?: boolean;
}

// WebSocket Event Types
export interface WSEvent {
  type: string;
  payload: any;
  timestamp: Date;
}

export interface GenerationUpdate extends WSEvent {
  type: 'generation_update';
  payload: {
    sessionId: string;
    currentTurn: number;
    latestInteraction?: AgentInteraction;
    storyFragment?: string;
    performance: Partial<SessionPerformance>;
  };
}

export interface AgentStatusUpdate extends WSEvent {
  type: 'agent_status';
  payload: {
    agentId: string;
    status: AgentStatus['status'];
    message?: string;
  };
}

// Form Types for React Hook Form
export interface CharacterFormData {
  name: string;
  faction: string;
  role: string;
  description: string;
  stats: CharacterStats;
  equipment: Omit<Equipment, 'id'>[];
  relationships: Omit<Relationship, 'targetCharacterId'>[];
}

export interface StoryFormData {
  title: string;
  description: string;
  characters: string[];
  settings: StorySettings;
}

// Chart and Visualization Types
export interface PerformanceMetric {
  timestamp: Date;
  value: number;
  label: string;
}

export interface CharacterNetwork {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
}

export interface NetworkNode {
  id: string;
  label: string;
  type: 'character' | 'faction' | 'location';
  data: any;
  position?: { x: number; y: number };
}

export interface NetworkEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  weight: number;
  label?: string;
}