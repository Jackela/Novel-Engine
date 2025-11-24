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

const EnhancedAgentInterface: React.FC<EnhancedAgentInterfaceProps> = ({
  sessionId: _sessionId,
  allowDirectControl = true,
  showAdvancedControls: _showAdvancedControls = false,
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
  const selectedAgent = useMemo(() => 
    agents.find(agent => agent.id === selectedAgentId) || null,
    [agents, selectedAgentId]
  );

  // Filtered and sorted agents
  const filteredAndSortedAgents = useMemo(() => {
    PerformanceMonitor.start('agent-filtering');
    
    let filtered = agents;
    
    // Apply status filter
    if (filterStatus !== 'all') {
      filtered = filtered.filter(agent => agent.status === filterStatus);
    }
    
    // Apply sorting
    const sorted = filtered.sort((a, b) => {
      switch (sortBy) {
        case 'activity':
          return b.lastActivity - a.lastActivity;
        case 'performance':
          return b.statistics.successRate - a.statistics.successRate;
        case 'name':
          return a.name.localeCompare(b.name);
        case 'status': {
          const statusPriority = { acting: 0, thinking: 1, waiting: 2, idle: 3, error: 4 };
          return statusPriority[a.status] - statusPriority[b.status];
        }
        default:
          return 0;
      }
    });
    
    PerformanceMonitor.end('agent-filtering');
    return sorted;
  }, [agents, filterStatus, sortBy]);

  // WebSocket message handling
  const handleWebSocketMessage = useCallback((event: CustomEvent) => {
    const message = event.detail;
    
    switch (message.type) {
      case 'agent_status_update':
        deferUpdate(() => {
          setAgents(prev => {
            const newAgents = [...prev];
            const agentIndex = newAgents.findIndex(a => a.id === message.data.agentId);
            
            if (agentIndex >= 0) {
              newAgents[agentIndex] = { 
                ...newAgents[agentIndex], 
                ...message.data,
                lastActivity: Date.now(),
                // Generate some enhanced properties for demo
                health: Math.random() * 30 + 70,
                load: Math.random() * 60 + 20,
                responseTime: Math.random() * 100 + 50
              };
            } else if (newAgents.length < maxAgents) {
              // Add new agent with enhanced properties
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
                color: generateAgentColor(message.data.type || 'persona')
              });
            }
            
            return newAgents;
          });
        });
        break;
        
      case 'system_metrics':
        setMetrics({
          totalActions: message.data.totalActions || 0,
          avgResponseTime: message.data.avgResponseTime || 0,
          systemLoad: message.data.systemLoad || 0,
          activeAgents: agents.filter(a => a.status === 'acting').length
        });
        break;
    }
  }, [deferUpdate, maxAgents, agents]);

  // Generate agent color based on type
  const generateAgentColor = (type: string) => {
    const colors = {
      director: 'var(--color-info)',
      persona: 'var(--color-success)',
      chronicler: 'var(--color-warning)',
      arbiter: 'var(--color-error)'
    } as const;
    return (colors as Record<string, string>)[type] ?? 'var(--color-text-secondary)';
  };

  // Default values
  const getDefaultParameters = (): AgentParameters => ({
    creativity: 0.7,
    consistency: 0.8,
    responsiveness: 0.6,
    autonomy: 0.5,
    collaboration: 0.7,
    riskTolerance: 0.4,
    memoryRetention: 0.8,
    narrativeFocus: 'mixed',
    communicationStyle: 'descriptive'
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
    processingPower: 0
  });

  // Agent control functions
  const pauseAgent = useCallback((agentId: string) => {
    measureInteractionDelay(() => {
      sendMessage({
        type: 'pause_agent',
        data: { sessionId, agentId },
        priority: 'high'
      });
    });
  }, [measureInteractionDelay, sendMessage]);

  const resumeAgent = useCallback((agentId: string) => {
    measureInteractionDelay(() => {
      sendMessage({
        type: 'resume_agent',
        data: { sessionId, agentId },
        priority: 'high'
      });
    });
  }, [measureInteractionDelay, sendMessage]);

  // Event listeners
  useEffect(() => {
    window.addEventListener('websocket-message', handleWebSocketMessage);
    
    // Request initial agent status
    if (wsState.isConnected) {
      sendMessage({
        type: 'get_agent_status',
        data: { sessionId },
        priority: 'normal'
      });
    }
    
    return () => {
      window.removeEventListener('websocket-message', handleWebSocketMessage);
    };
  }, [handleWebSocketMessage, wsState.isConnected, sendMessage]);

  // Auto-select first agent if none selected
  useEffect(() => {
    if (!selectedAgentId && filteredAndSortedAgents.length > 0) {
      setSelectedAgentId(filteredAndSortedAgents[0].id);
    }
  }, [selectedAgentId, filteredAndSortedAgents]);

  // Render agent card
  const renderAgentCard = (agent: EnhancedAgent) => (
    <Card
      key={agent.id}
      variant={selectedAgentId === agent.id ? "interactive" : "elevated"}
      className={cn(
        "cursor-pointer transition-all duration-200 agent-card",
        selectedAgentId === agent.id && "ring-2 ring-primary border-primary"
      )}
      onClick={() => setSelectedAgentId(agent.id)}
      glow={agent.status === 'acting'}
    >
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
            <StatusBadge status={
              agent.status === 'acting' ? 'online' : 
              agent.status === 'error' ? 'offline' :
              agent.status === 'thinking' ? 'busy' : 'idle'
            } showLabel={false} />
          </NotificationBadge>
        </div>
      </CardHeader>

      <CardContent>
        <div className="space-y-3">
          {agent.currentAction && (
            <div className="text-sm text-muted-foreground bg-muted p-2 rounded">
              <strong>Current:</strong> {agent.currentAction}
            </div>
          )}

          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="flex justify-between">
              <span>Health:</span>
              <span className={cn(
                "font-medium",
                agent.health > 80 ? "text-green-600" : agent.health > 50 ? "text-yellow-600" : "text-red-600"
              )}>
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

          <div className="flex gap-2">
            {agent.capabilities.slice(0, 2).map(capability => (
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

          {allowDirectControl && (
            <div className="flex gap-2 pt-2">
              {agent.status === 'idle' || agent.status === 'waiting' ? (
                <Button
                  size="sm"
                  variant="default"
                  onClick={(e) => {
                    e.stopPropagation();
                    resumeAgent(agent.id);
                  }}
                  className="flex-1"
                >
                  Resume
                </Button>
              ) : (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={(e) => {
                    e.stopPropagation();
                    pauseAgent(agent.id);
                  }}
                  className="flex-1"
                >
                  Pause
                </Button>
              )}
              <Button
                size="sm"
                variant="ghost"
                onClick={(e) => {
                  e.stopPropagation();
                  // Add restart logic
                }}
              >
                ⟲
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className={cn("enhanced-agent-interface", className)}>
      {/* Header with metrics */}
      <div className="mb-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">Agent Management</h2>
          <div className="flex items-center gap-2">
            <Badge variant="glass" size="sm">
              {filteredAndSortedAgents.length} / {maxAgents}
            </Badge>
            <StatusBadge status={wsState.isConnected ? 'online' : 'offline'} />
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
            description={`of ${agents.length} total`}
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
            color={metrics.systemLoad > 80 ? "error" : metrics.systemLoad > 60 ? "warning" : "success"}
          />
        </div>
      </div>

      {/* Controls */}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
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
            onChange={(e) => setSortBy(e.target.value as 'activity' | 'performance' | 'name' | 'status')}
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
            onClick={() => setViewMode('grid')}
          >
            ⊞ Grid
          </Button>
          <Button
            variant={viewMode === 'list' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setViewMode('list')}
          >
            ☰ List
          </Button>
          <Button
            variant={viewMode === 'detailed' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setViewMode('detailed')}
          >
            📊 Detailed
          </Button>
        </div>
      </div>

      {/* Agent Grid/List */}
      <div className={cn(
        "agents-container",
        viewMode === 'grid' && "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4",
        viewMode === 'list' && "space-y-3",
        viewMode === 'detailed' && "grid grid-cols-1 lg:grid-cols-2 gap-6"
      )}>
        {filteredAndSortedAgents.map(agent => renderAgentCard(agent))}
      </div>

      {filteredAndSortedAgents.length === 0 && (
        <Card className="p-8 text-center">
          <div className="text-muted-foreground">
            <span className="text-4xl block mb-4">🤖</span>
            <p>No agents found matching your filters.</p>
            <p className="text-sm mt-2">Try adjusting your filter settings or start a narrative session.</p>
          </div>
        </Card>
      )}

      {/* Selected Agent Detail Panel */}
      {selectedAgent && viewMode === 'detailed' && (
        <Card className="mt-6" variant="elevated">
          <CardHeader>
            <CardTitle>Agent Details: {selectedAgent.name}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div>
                  <h4 className="font-semibold mb-2">Performance Metrics</h4>
                  <div className="space-y-2">
                    <ProgressCard
                      title="Success Rate"
                      progress={selectedAgent.statistics.successRate * 100}
                      color="success"
                    />
                    <ProgressCard
                      title="Health"
                      progress={selectedAgent.health}
                      color={selectedAgent.health > 80 ? "success" : "warning"}
                    />
                    <ProgressCard
                      title="Load"
                      progress={selectedAgent.load}
                      color={selectedAgent.load > 80 ? "error" : "info"}
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <h4 className="font-semibold mb-2">Capabilities</h4>
                  <div className="flex flex-wrap gap-2">
                    {selectedAgent.capabilities.map(capability => (
                      <Badge key={capability} variant="secondary">
                        {capability}
                      </Badge>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="font-semibold mb-2">Recent Activity</h4>
                  <p className="text-sm text-muted-foreground">
                    Last active: {formatRelativeTime(selectedAgent.lastActivity)}
                  </p>
                  {selectedAgent.currentAction && (
                    <p className="text-sm mt-1">
                      <strong>Current:</strong> {selectedAgent.currentAction}
                    </p>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default React.memo(EnhancedAgentInterface);
