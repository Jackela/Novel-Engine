/**
 * Enhanced Agent Interface with Magic UI
 * =====================================
 * 
 * Modern agent management interface using Magic UI components:
 * - Advanced card-based layout
 * - Interactive status badges
 * - Performance optimized components
 * - Accessibility features
 * - Real-time animations
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useWebSocketContext } from '../../hooks/useWebSocket';
import { usePerformanceOptimizer } from '../../hooks/usePerformanceOptimizer';
import { Button } from '../ui/Button';
import { Card, CardHeader, CardTitle, CardContent, StatCard, ProgressCard } from '../ui/Card';
import { Badge, StatusBadge, NotificationBadge } from '../ui/Badge';
import { cn, formatRelativeTime, formatNumber, PerformanceMonitor } from '../../lib/utils';
import './EnhancedAgentInterface.css';

// Enhanced Agent types with additional UI properties
interface EnhancedAgent {
  id: string;
  name: string;
  type: 'director' | 'persona' | 'chronicler' | 'arbiter';
  status: 'idle' | 'thinking' | 'acting' | 'waiting' | 'error';
  currentAction?: string;
  lastActivity: number;
  parameters: AgentParameters;
  statistics: EnhancedAgentStatistics;
  capabilities: string[];
  relationships: { [agentId: string]: number };

  // Enhanced UI properties
  avatar?: string;
  color?: string;
  priority: 'low' | 'normal' | 'high' | 'critical';
  notifications: number;
  health: number; // 0-100
  load: number; // 0-100
  responseTime: number;
}

interface EnhancedAgentStatistics {
  actionsPerformed: number;
  averageResponseTime: number;
  successRate: number;
  collaborations: number;
  decisionsInfluenced: number;
  narrativeContributions: number;

  // Enhanced metrics
  uptime: number;
  errorRate: number;
  throughput: number;
  memoryUsage: number;
  processingPower: number;
}

interface AgentParameters {
  creativity: number;
  consistency: number;
  responsiveness: number;
  autonomy: number;
  collaboration: number;
  riskTolerance: number;
  memoryRetention: number;
  narrativeFocus: 'character' | 'plot' | 'world' | 'mixed';
  communicationStyle: 'formal' | 'casual' | 'descriptive' | 'concise';
}

interface EnhancedAgentInterfaceProps {
  sessionId: string;
  allowDirectControl?: boolean;
  showAdvancedControls?: boolean;
  maxAgents?: number;
  className?: string;
}

const STATUS_PRIORITY: Record<EnhancedAgent['status'], number> = {
  acting: 0,
  thinking: 1,
  waiting: 2,
  idle: 3,
  error: 4,
};

const generateAgentColor = (type: string) => {
  const colors = {
    director: 'var(--color-info)',
    persona: 'var(--color-success)',
    chronicler: 'var(--color-warning)',
    arbiter: 'var(--color-error)',
  } as const;
  return (colors as Record<string, string>)[type] ?? 'var(--color-text-secondary)';
};

const getDefaultParameters = (): AgentParameters => ({
  creativity: 0.7,
  consistency: 0.8,
  responsiveness: 0.6,
  autonomy: 0.5,
  collaboration: 0.7,
  riskTolerance: 0.4,
  memoryRetention: 0.8,
  narrativeFocus: 'mixed',
  communicationStyle: 'descriptive',
});

const getDefaultStatistics = (): EnhancedAgentStatistics => ({
  actionsPerformed: 0,
  averageResponseTime: 0,
  successRate: 1.0,
  collaborations: 0,
  decisionsInfluenced: 0,
  narrativeContributions: 0,
  uptime: 100,
  errorRate: 0,
  throughput: 0,
  memoryUsage: 0,
  processingPower: 0,
});

const getStatusBadge = (status: EnhancedAgent['status']) => {
  if (status === 'acting') return 'online';
  if (status === 'error') return 'offline';
  if (status === 'thinking') return 'busy';
  return 'idle';
};

const filterAgentsByStatus = (agents: EnhancedAgent[], filterStatus: string) => {
  if (filterStatus === 'all') return agents;
  return agents.filter((agent) => agent.status === filterStatus);
};

const sortAgents = (
  agents: EnhancedAgent[],
  sortBy: 'activity' | 'performance' | 'name' | 'status'
) => {
  const sorted = [...agents];
  sorted.sort((a, b) => {
    switch (sortBy) {
      case 'activity':
        return b.lastActivity - a.lastActivity;
      case 'performance':
        return b.statistics.successRate - a.statistics.successRate;
      case 'name':
        return a.name.localeCompare(b.name);
      case 'status':
        return STATUS_PRIORITY[a.status] - STATUS_PRIORITY[b.status];
      default:
        return 0;
    }
  });
  return sorted;
};

const updateAgentsFromStatus = (
  prevAgents: EnhancedAgent[],
  message: {
    data: {
      agentId: string;
      name?: string;
      type?: EnhancedAgent['type'];
      status?: EnhancedAgent['status'];
      parameters?: AgentParameters;
      statistics?: EnhancedAgentStatistics;
      capabilities?: string[];
      relationships?: { [agentId: string]: number };
    };
  },
  maxAgents: number
) => {
  const newAgents = [...prevAgents];
  const agentIndex = newAgents.findIndex((agent) => agent.id === message.data.agentId);

  if (agentIndex >= 0) {
    newAgents[agentIndex] = {
      ...newAgents[agentIndex],
      ...message.data,
      lastActivity: Date.now(),
      health: Math.random() * 30 + 70,
      load: Math.random() * 60 + 20,
      responseTime: Math.random() * 100 + 50,
    };
    return newAgents;
  }

  if (newAgents.length >= maxAgents) {
    return newAgents;
  }

  newAgents.push({
    id: message.data.agentId,
    name: message.data.name || `Agent ${message.data.agentId}`,
    type: message.data.type || 'persona',
    status: message.data.status || 'idle',
    lastActivity: Date.now(),
    parameters: message.data.parameters || getDefaultParameters(),
    statistics: message.data.statistics || getDefaultStatistics(),
    capabilities: message.data.capabilities || [],
    relationships: message.data.relationships || {},
    priority: 'normal',
    notifications: Math.floor(Math.random() * 5),
    health: Math.random() * 30 + 70,
    load: Math.random() * 60 + 20,
    responseTime: Math.random() * 100 + 50,
    color: generateAgentColor(message.data.type || 'persona'),
  });

  return newAgents;
};

const AgentCard: React.FC<{
  agent: EnhancedAgent;
  isSelected: boolean;
  allowDirectControl: boolean;
  onSelect: (agentId: string) => void;
  onPause: (agentId: string) => void;
  onResume: (agentId: string) => void;
}> = ({ agent, isSelected, allowDirectControl, onSelect, onPause, onResume }) => (
  <Card
    variant={isSelected ? 'interactive' : 'elevated'}
    className={cn(
      'cursor-pointer transition-all duration-200 agent-card',
      isSelected && 'ring-2 ring-primary border-primary'
    )}
    onClick={() => onSelect(agent.id)}
    glow={agent.status === 'acting'}
  >
    <AgentCardHeader agent={agent} />
    <CardContent>
      <div className="space-y-3">
        {agent.currentAction && (
          <div className="text-sm text-muted-foreground bg-muted p-2 rounded">
            <strong>Current:</strong> {agent.currentAction}
          </div>
        )}
        <AgentCardStats agent={agent} />
        <AgentCardCapabilities agent={agent} />
        {allowDirectControl && (
          <AgentCardActions agent={agent} onPause={onPause} onResume={onResume} />
        )}
      </div>
    </CardContent>
  </Card>
);

const AgentCardHeader: React.FC<{ agent: EnhancedAgent }> = ({ agent }) => (
  <CardHeader className="pb-2">
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div
          className="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold"
          style={{ backgroundColor: agent.color }}
        >
          {agent.name.charAt(0)}
        </div>
        <div>
          <CardTitle className="text-base">{agent.name}</CardTitle>
          <Badge variant="outline" size="sm" className="mt-1">
            {agent.type}
          </Badge>
        </div>
      </div>
      <NotificationBadge count={agent.notifications} position="top-right">
        <StatusBadge status={getStatusBadge(agent.status)} showLabel={false} />
      </NotificationBadge>
    </div>
  </CardHeader>
);

const AgentCardStats: React.FC<{ agent: EnhancedAgent }> = ({ agent }) => (
  <div className="grid grid-cols-2 gap-2 text-xs">
    <div className="flex justify-between">
      <span>Health:</span>
      <span
        className={cn(
          'font-medium',
          agent.health > 80 ? 'text-green-600' : agent.health > 50 ? 'text-yellow-600' : 'text-red-600'
        )}
      >
        {Math.round(agent.health)}%
      </span>
    </div>
    <div className="flex justify-between">
      <span>Load:</span>
      <span className="font-medium">{Math.round(agent.load)}%</span>
    </div>
    <div className="flex justify-between">
      <span>Success:</span>
      <span className="font-medium">{Math.round(agent.statistics.successRate * 100)}%</span>
    </div>
    <div className="flex justify-between">
      <span>RT:</span>
      <span className="font-medium">{Math.round(agent.responseTime)}ms</span>
    </div>
  </div>
);

const AgentCardCapabilities: React.FC<{ agent: EnhancedAgent }> = ({ agent }) => (
  <div className="flex gap-2">
    {agent.capabilities.slice(0, 2).map((capability) => (
      <Badge key={capability} variant="secondary" size="sm">
        {capability}
      </Badge>
    ))}
    {agent.capabilities.length > 2 && (
      <Badge variant="ghost" size="sm">
        +{agent.capabilities.length - 2}
      </Badge>
    )}
  </div>
);

const AgentCardActions: React.FC<{
  agent: EnhancedAgent;
  onPause: (agentId: string) => void;
  onResume: (agentId: string) => void;
}> = ({ agent, onPause, onResume }) => (
  <div className="flex gap-2 pt-2">
    {agent.status === 'idle' || agent.status === 'waiting' ? (
      <Button
        size="sm"
        variant="default"
        onClick={(event) => {
          event.stopPropagation();
          onResume(agent.id);
        }}
        className="flex-1"
      >
        Resume
      </Button>
    ) : (
      <Button
        size="sm"
        variant="outline"
        onClick={(event) => {
          event.stopPropagation();
          onPause(agent.id);
        }}
        className="flex-1"
      >
        Pause
      </Button>
    )}
    <Button
      size="sm"
      variant="ghost"
      onClick={(event) => {
        event.stopPropagation();
      }}
    >
      ⟲
    </Button>
  </div>
);

const AgentMetricsHeader: React.FC<{
  agentCount: number;
  maxAgents: number;
  metrics: { totalActions: number; avgResponseTime: number; systemLoad: number; activeAgents: number };
  isConnected: boolean;
  totalAgents: number;
}> = ({ agentCount, maxAgents, metrics, isConnected, totalAgents }) => (
  <div className="mb-6 space-y-4">
    <div className="flex items-center justify-between">
      <h2 className="text-2xl font-bold">Agent Management</h2>
      <div className="flex items-center gap-2">
        <Badge variant="glass" size="sm">
          {agentCount} / {maxAgents}
        </Badge>
        <StatusBadge status={isConnected ? 'online' : 'offline'} />
      </div>
    </div>

    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard
        title="Total Actions"
        value={formatNumber(metrics.totalActions)}
        color="info"
        icon={<span className="text-xl">⚡</span>}
      />
      <StatCard
        title="Active Agents"
        value={metrics.activeAgents}
        description={`of ${totalAgents} total`}
        color="success"
        icon={<span className="text-xl">🤖</span>}
      />
      <StatCard
        title="Avg Response"
        value={`${Math.round(metrics.avgResponseTime)}ms`}
        color="warning"
        icon={<span className="text-xl">⏱️</span>}
      />
      <ProgressCard
        title="System Load"
        progress={metrics.systemLoad}
        color={metrics.systemLoad > 80 ? 'error' : metrics.systemLoad > 60 ? 'warning' : 'success'}
      />
    </div>
  </div>
);

const AgentControls: React.FC<{
  filterStatus: string;
  sortBy: 'activity' | 'performance' | 'name' | 'status';
  viewMode: 'grid' | 'list' | 'detailed';
  onFilterChange: (value: string) => void;
  onSortChange: (value: 'activity' | 'performance' | 'name' | 'status') => void;
  onViewChange: (value: 'grid' | 'list' | 'detailed') => void;
}> = ({ filterStatus, sortBy, viewMode, onFilterChange, onSortChange, onViewChange }) => (
  <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
    <div className="flex items-center gap-2">
      <select
        value={filterStatus}
        onChange={(event) => onFilterChange(event.target.value)}
        className="px-3 py-2 bg-background border border-border rounded-md text-sm"
      >
        <option value="all">All Status</option>
        <option value="acting">Acting</option>
        <option value="thinking">Thinking</option>
        <option value="waiting">Waiting</option>
        <option value="idle">Idle</option>
        <option value="error">Error</option>
      </select>

      <select
        value={sortBy}
        onChange={(event) => onSortChange(event.target.value as 'activity' | 'performance' | 'name' | 'status')}
        className="px-3 py-2 bg-background border border-border rounded-md text-sm"
      >
        <option value="activity">Latest Activity</option>
        <option value="performance">Performance</option>
        <option value="name">Name</option>
        <option value="status">Status</option>
      </select>
    </div>

    <div className="flex items-center gap-2">
      <Button
        variant={viewMode === 'grid' ? 'default' : 'ghost'}
        size="sm"
        onClick={() => onViewChange('grid')}
      >
        ⊞ Grid
      </Button>
      <Button
        variant={viewMode === 'list' ? 'default' : 'ghost'}
        size="sm"
        onClick={() => onViewChange('list')}
      >
        ☰ List
      </Button>
      <Button
        variant={viewMode === 'detailed' ? 'default' : 'ghost'}
        size="sm"
        onClick={() => onViewChange('detailed')}
      >
        📊 Detailed
      </Button>
    </div>
  </div>
);

const AgentEmptyState: React.FC = () => (
  <Card className="p-8 text-center">
    <div className="text-muted-foreground">
      <span className="text-4xl block mb-4">🤖</span>
      <p>No agents found matching your filters.</p>
      <p className="text-sm mt-2">Try adjusting your filter settings or start a narrative session.</p>
    </div>
  </Card>
);

const AgentDetailPanel: React.FC<{ agent: EnhancedAgent }> = ({ agent }) => (
  <Card className="mt-6" variant="elevated">
    <CardHeader>
      <CardTitle>Agent Details: {agent.name}</CardTitle>
    </CardHeader>
    <CardContent>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <div>
            <h4 className="font-semibold mb-2">Performance Metrics</h4>
            <div className="space-y-2">
              <ProgressCard
                title="Success Rate"
                progress={agent.statistics.successRate * 100}
                color="success"
              />
              <ProgressCard
                title="Health"
                progress={agent.health}
                color={agent.health > 80 ? 'success' : 'warning'}
              />
              <ProgressCard
                title="Load"
                progress={agent.load}
                color={agent.load > 80 ? 'error' : 'info'}
              />
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <h4 className="font-semibold mb-2">Capabilities</h4>
            <div className="flex flex-wrap gap-2">
              {agent.capabilities.map((capability) => (
                <Badge key={capability} variant="secondary">
                  {capability}
                </Badge>
              ))}
            </div>
          </div>

          <div>
            <h4 className="font-semibold mb-2">Recent Activity</h4>
            <p className="text-sm text-muted-foreground">
              Last active: {formatRelativeTime(agent.lastActivity)}
            </p>
            {agent.currentAction && (
              <p className="text-sm mt-1">
                <strong>Current:</strong> {agent.currentAction}
              </p>
            )}
          </div>
        </div>
      </div>
    </CardContent>
  </Card>
);

const AgentList: React.FC<{
  agents: EnhancedAgent[];
  selectedAgentId: string | null;
  viewMode: 'grid' | 'list' | 'detailed';
  allowDirectControl: boolean;
  onSelect: (agentId: string) => void;
  onPause: (agentId: string) => void;
  onResume: (agentId: string) => void;
}> = ({ agents, selectedAgentId, viewMode, allowDirectControl, onSelect, onPause, onResume }) => (
  <div
    className={cn(
      'agents-container',
      viewMode === 'grid' && 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4',
      viewMode === 'list' && 'space-y-3',
      viewMode === 'detailed' && 'grid grid-cols-1 lg:grid-cols-2 gap-6'
    )}
  >
    {agents.map((agent) => (
      <AgentCard
        key={agent.id}
        agent={agent}
        isSelected={selectedAgentId === agent.id}
        allowDirectControl={allowDirectControl}
        onSelect={onSelect}
        onPause={onPause}
        onResume={onResume}
      />
    ))}
  </div>
);

const AgentInterfaceBody: React.FC<{
  agents: EnhancedAgent[];
  filteredAgents: EnhancedAgent[];
  selectedAgent: EnhancedAgent | null;
  selectedAgentId: string | null;
  viewMode: 'grid' | 'list' | 'detailed';
  filterStatus: string;
  sortBy: 'activity' | 'performance' | 'name' | 'status';
  allowDirectControl: boolean;
  maxAgents: number;
  metrics: { totalActions: number; avgResponseTime: number; systemLoad: number; activeAgents: number };
  isConnected: boolean;
  onFilterChange: (value: string) => void;
  onSortChange: (value: 'activity' | 'performance' | 'name' | 'status') => void;
  onViewChange: (value: 'grid' | 'list' | 'detailed') => void;
  onSelect: (agentId: string) => void;
  onPause: (agentId: string) => void;
  onResume: (agentId: string) => void;
}> = ({
  agents,
  filteredAgents,
  selectedAgent,
  selectedAgentId,
  viewMode,
  filterStatus,
  sortBy,
  allowDirectControl,
  maxAgents,
  metrics,
  isConnected,
  onFilterChange,
  onSortChange,
  onViewChange,
  onSelect,
  onPause,
  onResume,
}) => (
  <>
    <AgentMetricsHeader
      agentCount={filteredAgents.length}
      maxAgents={maxAgents}
      metrics={metrics}
      isConnected={isConnected}
      totalAgents={agents.length}
    />

    <AgentControls
      filterStatus={filterStatus}
      sortBy={sortBy}
      viewMode={viewMode}
      onFilterChange={onFilterChange}
      onSortChange={onSortChange}
      onViewChange={onViewChange}
    />

    <AgentList
      agents={filteredAgents}
      selectedAgentId={selectedAgentId}
      viewMode={viewMode}
      allowDirectControl={allowDirectControl}
      onSelect={onSelect}
      onPause={onPause}
      onResume={onResume}
    />

    {filteredAgents.length === 0 && <AgentEmptyState />}

    {selectedAgent && viewMode === 'detailed' && <AgentDetailPanel agent={selectedAgent} />}
  </>
);

const useFilteredAgents = (
  agents: EnhancedAgent[],
  filterStatus: string,
  sortBy: 'activity' | 'performance' | 'name' | 'status'
) =>
  useMemo(() => {
    PerformanceMonitor.start('agent-filtering');
    const filtered = filterAgentsByStatus(agents, filterStatus);
    const sorted = sortAgents(filtered, sortBy);
    PerformanceMonitor.end('agent-filtering');
    return sorted;
  }, [agents, filterStatus, sortBy]);

const useSelectedAgent = (agents: EnhancedAgent[], selectedAgentId: string | null) =>
  useMemo(() => agents.find((agent) => agent.id === selectedAgentId) || null, [agents, selectedAgentId]);

const useAutoSelectAgent = (
  selectedAgentId: string | null,
  agents: EnhancedAgent[],
  setSelectedAgentId: React.Dispatch<React.SetStateAction<string | null>>
) => {
  useEffect(() => {
    if (!selectedAgentId && agents.length > 0) {
      setSelectedAgentId(agents[0].id);
    }
  }, [selectedAgentId, agents, setSelectedAgentId]);
};

const useAgentWebSocket = (params: {
  agents: EnhancedAgent[];
  maxAgents: number;
  sessionId: string;
  wsState: { isConnected: boolean };
  sendMessage: (payload: { type: string; data: Record<string, unknown>; priority: 'normal' | 'high' }) => void;
  deferUpdate: (callback: () => void) => void;
  setAgents: React.Dispatch<React.SetStateAction<EnhancedAgent[]>>;
  setMetrics: React.Dispatch<
    React.SetStateAction<{ totalActions: number; avgResponseTime: number; systemLoad: number; activeAgents: number }>
  >;
}) => {
  const handleWebSocketMessage = useCallback((event: Event) => {
    const message = (event as CustomEvent).detail;

    switch (message.type) {
      case 'agent_status_update':
        params.deferUpdate(() => {
          params.setAgents((prev) => updateAgentsFromStatus(prev, message, params.maxAgents));
        });
        break;

      case 'system_metrics':
        params.setMetrics({
          totalActions: message.data.totalActions || 0,
          avgResponseTime: message.data.avgResponseTime || 0,
          systemLoad: message.data.systemLoad || 0,
          activeAgents: params.agents.filter((agent) => agent.status === 'acting').length,
        });
        break;
    }
  }, [params]);

  useEffect(() => {
    window.addEventListener('websocket-message', handleWebSocketMessage);

    if (params.wsState.isConnected) {
      params.sendMessage({
        type: 'get_agent_status',
        data: { sessionId: params.sessionId },
        priority: 'normal',
      });
    }

    return () => {
      window.removeEventListener('websocket-message', handleWebSocketMessage);
    };
  }, [handleWebSocketMessage, params]);
};

const EnhancedAgentInterface: React.FC<EnhancedAgentInterfaceProps> = ({
  sessionId,
  allowDirectControl = true,
  maxAgents = 10,
  className = ''
}) => {
  const { state: wsState, sendMessage } = useWebSocketContext();
  const { deferUpdate, measureInteractionDelay } = usePerformanceOptimizer();

  const [agents, setAgents] = useState<EnhancedAgent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list' | 'detailed'>('grid');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'activity' | 'performance' | 'name' | 'status'>('activity');
  const [_isConfigPanelOpen, _setIsConfigPanelOpen] = useState(false);

  // Performance metrics
  const [metrics, setMetrics] = useState({
    totalActions: 0,
    avgResponseTime: 0,
    systemLoad: 0,
    activeAgents: 0
  });

  // Selected agent data
  const selectedAgent = useSelectedAgent(agents, selectedAgentId);
  const filteredAndSortedAgents = useFilteredAgents(agents, filterStatus, sortBy);

  // Agent control functions
  const pauseAgent = useCallback((agentId: string) => {
    measureInteractionDelay(() => {
      sendMessage({
        type: 'pause_agent',
        data: { sessionId, agentId },
        priority: 'high'
      });
    });
  }, [measureInteractionDelay, sendMessage, sessionId]);

  const resumeAgent = useCallback((agentId: string) => {
    measureInteractionDelay(() => {
      sendMessage({
        type: 'resume_agent',
        data: { sessionId, agentId },
        priority: 'high'
      });
    });
  }, [measureInteractionDelay, sendMessage, sessionId]);

  useAgentWebSocket({
    agents,
    maxAgents,
    sessionId,
    wsState,
    sendMessage,
    deferUpdate,
    setAgents,
    setMetrics,
  });

  useAutoSelectAgent(selectedAgentId, filteredAndSortedAgents, setSelectedAgentId);

  return (
    <div className={cn("enhanced-agent-interface", className)}>
      <AgentInterfaceBody
        agents={agents}
        filteredAgents={filteredAndSortedAgents}
        selectedAgent={selectedAgent}
        selectedAgentId={selectedAgentId}
        viewMode={viewMode}
        filterStatus={filterStatus}
        sortBy={sortBy}
        allowDirectControl={allowDirectControl}
        maxAgents={maxAgents}
        metrics={metrics}
        isConnected={wsState.isConnected}
        onFilterChange={setFilterStatus}
        onSortChange={setSortBy}
        onViewChange={setViewMode}
        onSelect={setSelectedAgentId}
        onPause={pauseAgent}
        onResume={resumeAgent}
      />
    </div>
  );
};

export default React.memo(EnhancedAgentInterface);
