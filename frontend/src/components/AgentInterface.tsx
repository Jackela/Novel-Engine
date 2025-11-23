/**
 * Agent Interface Component
 * =========================
 * 
 * Interactive interface for managing and communicating with AI agents:
 * - Agent status monitoring
 * - Direct agent communication
 * - Agent parameter configuration
 * - Real-time agent action tracking
 * - Multi-agent coordination controls
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useWebSocketContext } from '../hooks/useWebSocket';
import { usePerformanceOptimizer } from '../hooks/usePerformanceOptimizer';
import './AgentInterface.css';

// Agent-related types
interface Agent {
  id: string;
  name: string;
  type: 'director' | 'persona' | 'chronicler' | 'arbiter';
  status: 'idle' | 'thinking' | 'acting' | 'waiting' | 'error';
  currentAction?: string;
  lastActivity: number;
  parameters: AgentParameters;
  statistics: AgentStatistics;
  capabilities: string[];
  relationships: { [agentId: string]: number }; // Relationship weights
}

interface AgentParameters {
  creativity: number; // 0-1
  consistency: number; // 0-1
  responsiveness: number; // 0-1
  autonomy: number; // 0-1
  collaboration: number; // 0-1
  riskTolerance: number; // 0-1
  memoryRetention: number; // 0-1
  narrativeFocus: 'character' | 'plot' | 'world' | 'mixed';
  communicationStyle: 'formal' | 'casual' | 'descriptive' | 'concise';
}

interface AgentStatistics {
  actionsPerformed: number;
  averageResponseTime: number;
  successRate: number;
  collaborations: number;
  decisionsInfluenced: number;
  narrativeContributions: number;
}

interface AgentMessage {
  id: string;
  fromAgentId: string;
  toAgentId?: string; // null for broadcast
  content: string;
  type: 'instruction' | 'question' | 'suggestion' | 'status' | 'coordination';
  timestamp: number;
  priority: 'low' | 'normal' | 'high' | 'urgent';
  requiresResponse: boolean;
}

interface AgentInterfaceProps {
  sessionId: string;
  allowDirectControl?: boolean;
  showAdvancedControls?: boolean;
  maxAgents?: number;
  className?: string;
}

const AgentInterface: React.FC<AgentInterfaceProps> = ({
  sessionId,
  allowDirectControl = true,
  showAdvancedControls = false,
  maxAgents = 10,
  className = ''
}) => {
  const { state: wsState, sendMessage } = useWebSocketContext();
  const { deferUpdate, measureInteractionDelay } = usePerformanceOptimizer();

  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [, setMessages] = useState<AgentMessage[]>([]);
  const [messageInput, setMessageInput] = useState('');
  const [messageType, setMessageType] = useState<AgentMessage['type']>('instruction');
  const [isConfigPanelOpen, setIsConfigPanelOpen] = useState(false);
  const [coordinationMode, setCoordinationMode] = useState<'autonomous' | 'guided' | 'manual'>('autonomous');

  // Selected agent data
  const selectedAgent = useMemo(() => 
    agents.find(agent => agent.id === selectedAgentId) || null,
    [agents, selectedAgentId]
  );

  // Agent filtering and sorting
  const sortedAgents = useMemo(() => 
    agents.sort((a, b) => {
      // Sort by status priority, then by last activity
      const statusPriority = { acting: 0, thinking: 1, waiting: 2, idle: 3, error: 4 };
      const aPriority = statusPriority[a.status];
      const bPriority = statusPriority[b.status];
      
      if (aPriority !== bPriority) return aPriority - bPriority;
      return b.lastActivity - a.lastActivity;
    }),
    [agents]
  );

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
                lastActivity: Date.now()
              };
            } else if (newAgents.length < maxAgents) {
              // Add new agent
              newAgents.push({
                id: message.data.agentId,
                name: message.data.name || `Agent ${message.data.agentId}`,
                type: message.data.type || 'persona',
                status: message.data.status || 'idle',
                lastActivity: Date.now(),
                parameters: message.data.parameters || getDefaultParameters(),
                statistics: message.data.statistics || getDefaultStatistics(),
                capabilities: message.data.capabilities || [],
                relationships: message.data.relationships || {}
              });
            }
            
            return newAgents;
          });
        });
        break;
        
      case 'agent_message':
        setMessages(prev => {
          const newMessages = [...prev, message.data];
          return newMessages.slice(-100); // Keep last 100 messages
        });
        break;
        
      case 'agent_removed':
        setAgents(prev => prev.filter(a => a.id !== message.data.agentId));
        if (selectedAgentId === message.data.agentId) {
          setSelectedAgentId(null);
        }
        break;
    }
  }, [deferUpdate, maxAgents, selectedAgentId]);

  // Default parameter values
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

  const getDefaultStatistics = (): AgentStatistics => ({
    actionsPerformed: 0,
    averageResponseTime: 0,
    successRate: 1.0,
    collaborations: 0,
    decisionsInfluenced: 0,
    narrativeContributions: 0
  });

  // Agent control functions
  const sendAgentMessage = useCallback(() => {
    if (!messageInput.trim() || !wsState.isConnected) return;
    
    measureInteractionDelay(() => {
      const message: Omit<AgentMessage, 'id' | 'timestamp'> = {
        fromAgentId: 'user',
        toAgentId: selectedAgentId ?? undefined,
        content: messageInput.trim(),
        type: messageType,
        priority: 'normal',
        requiresResponse: messageType === 'question'
      };
      
      sendMessage({
        type: 'agent_message',
        data: {
          sessionId,
          ...message
        },
        priority: 'normal'
      });
      
      setMessageInput('');
    });
  }, [messageInput, messageType, selectedAgentId, wsState.isConnected, measureInteractionDelay, sendMessage, sessionId]);

  const updateAgentParameters = useCallback((agentId: string, parameters: Partial<AgentParameters>) => {
    if (!wsState.isConnected) return;
    
    sendMessage({
      type: 'update_agent_parameters',
      data: {
        sessionId,
        agentId,
        parameters
      },
      priority: 'normal'
    });
  }, [wsState.isConnected, sendMessage, sessionId]);

  const pauseAgent = useCallback((agentId: string) => {
    sendMessage({
      type: 'pause_agent',
      data: { sessionId, agentId },
      priority: 'high'
    });
  }, [sendMessage, sessionId]);

  const resumeAgent = useCallback((agentId: string) => {
    sendMessage({
      type: 'resume_agent',
      data: { sessionId, agentId },
      priority: 'high'
    });
  }, [sendMessage, sessionId]);

  const restartAgent = useCallback((agentId: string) => {
    sendMessage({
      type: 'restart_agent',
      data: { sessionId, agentId },
      priority: 'high'
    });
  }, [sendMessage, sessionId]);

  // Event listeners
  useEffect(() => {
    window.addEventListener('websocket-message', handleWebSocketMessage as EventListener);

    // Request initial agent status
    if (wsState.isConnected) {
      sendMessage({
        type: 'get_agent_status',
        data: { sessionId },
        priority: 'normal'
      });
    }

    return () => {
      window.removeEventListener('websocket-message', handleWebSocketMessage as EventListener);
    };
  }, [handleWebSocketMessage, wsState.isConnected, sendMessage, sessionId]);

  // Auto-select first agent if none selected
  useEffect(() => {
    if (!selectedAgentId && sortedAgents.length > 0) {
      setSelectedAgentId(sortedAgents[0].id);
    }
  }, [selectedAgentId, sortedAgents]);

  // Render agent status indicator
  const renderAgentStatus = (status: Agent['status']) => {
    const statusConfig = {
      idle: { color: 'var(--color-text-secondary)', icon: '⏸️', label: 'Idle' },
      thinking: { color: 'var(--color-warning)', icon: '🤔', label: 'Thinking' },
      acting: { color: 'var(--color-success)', icon: '⚡', label: 'Acting' },
      waiting: { color: 'var(--color-info)', icon: '⏳', label: 'Waiting' },
      error: { color: 'var(--color-error)', icon: '❌', label: 'Error' }
    } as const;
    
    const config = statusConfig[status];
    return (
      <span 
        className={`agent-status agent-status--${status}`}
        style={{ color: config.color }}
        title={config.label}
      >
        {config.icon} {config.label}
      </span>
    );
  };

  // Render agent parameters panel
  const renderParametersPanel = () => {
    if (!selectedAgent) return null;
    
    const handleParameterChange = (param: keyof AgentParameters, value: number | string) => {
      const newParameters = { ...selectedAgent.parameters, [param]: value };
      updateAgentParameters(selectedAgent.id, newParameters);
    };
    
    return (
      <div className="agent-parameters">
        <h4>Agent Parameters</h4>
        
        <div className="parameter-group">
          <h5>Core Attributes</h5>
          {(['creativity', 'consistency', 'responsiveness', 'autonomy'] as const).map(param => {
            const sliderId = `${selectedAgent.id}-${param}`;
            return (
              <div key={param} className="parameter-control">
                <label htmlFor={sliderId}>{param.charAt(0).toUpperCase() + param.slice(1)}</label>
                <input
                  id={sliderId}
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={selectedAgent.parameters[param]}
                  onChange={(e) => handleParameterChange(param, parseFloat(e.target.value))}
                  className="parameter-slider"
                />
                <span className="parameter-value">
                  {(selectedAgent.parameters[param] * 100).toFixed(0)}%
                </span>
              </div>
            );
          })}
        </div>
        
        <div className="parameter-group">
          <h5>Social Attributes</h5>
          {(['collaboration', 'riskTolerance', 'memoryRetention'] as const).map(param => {
            const sliderId = `${selectedAgent.id}-${param}-slider`;
            return (
              <div key={param} className="parameter-control">
                <label htmlFor={sliderId}>{param.replace(/([A-Z])/g, ' $1').toLowerCase()}</label>
                <input
                  id={sliderId}
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={selectedAgent.parameters[param]}
                  onChange={(e) => handleParameterChange(param, parseFloat(e.target.value))}
                  className="parameter-slider"
                />
                <span className="parameter-value">
                  {(selectedAgent.parameters[param] * 100).toFixed(0)}%
                </span>
              </div>
            );
          })}
        </div>
        
        <div className="parameter-group">
          <h5>Behavior Settings</h5>
          <div className="parameter-control">
            <label htmlFor={`narrative-focus-${selectedAgent.id}`}>Narrative Focus</label>
            <select
              id={`narrative-focus-${selectedAgent.id}`}
              value={selectedAgent.parameters.narrativeFocus}
              onChange={(e) => handleParameterChange('narrativeFocus', e.target.value)}
              className="parameter-select"
            >
              <option value="character">Character-focused</option>
              <option value="plot">Plot-focused</option>
              <option value="world">World-building</option>
              <option value="mixed">Mixed approach</option>
            </select>
          </div>
          
          <div className="parameter-control">
            <label htmlFor={`communication-style-${selectedAgent.id}`}>Communication Style</label>
            <select
              id={`communication-style-${selectedAgent.id}`}
              value={selectedAgent.parameters.communicationStyle}
              onChange={(e) => handleParameterChange('communicationStyle', e.target.value)}
              className="parameter-select"
            >
              <option value="formal">Formal</option>
              <option value="casual">Casual</option>
              <option value="descriptive">Descriptive</option>
              <option value="concise">Concise</option>
            </select>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className={`agent-interface ${className}`}>
      <div className="agent-interface__header">
        <h3>Agent Management</h3>
        <div className="agent-controls">
          <select
            value={coordinationMode}
            onChange={(e) => setCoordinationMode(e.target.value as 'autonomous' | 'guided' | 'manual')}
            className="coordination-select"
          >
            <option value="autonomous">Autonomous</option>
            <option value="guided">Guided</option>
            <option value="manual">Manual</option>
          </select>
          
          {showAdvancedControls && (
            <button
              onClick={() => setIsConfigPanelOpen(!isConfigPanelOpen)}
              className={`control-btn ${isConfigPanelOpen ? 'active' : ''}`}
            >
              Config
            </button>
          )}
        </div>
      </div>
      
      <div className="agent-interface__content">
        <div className="agent-list">
          <h4>Active Agents ({sortedAgents.length})</h4>
          {sortedAgents.map(agent => (
            <div
              key={agent.id}
              className={`agent-item ${selectedAgentId === agent.id ? 'selected' : ''}`}
              onClick={() => setSelectedAgentId(agent.id)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault();
                  setSelectedAgentId(agent.id);
                }
              }}
              role="button"
              tabIndex={0}
            >
              <div className="agent-item__header">
                <span className="agent-name">{agent.name}</span>
                <span className="agent-type">{agent.type}</span>
              </div>
              
              <div className="agent-item__status">
                {renderAgentStatus(agent.status)}
                {agent.currentAction && (
                  <span className="agent-action">{agent.currentAction}</span>
                )}
              </div>
              
              <div className="agent-item__stats">
                <span>Actions: {agent.statistics.actionsPerformed}</span>
                <span>Success: {(agent.statistics.successRate * 100).toFixed(0)}%</span>
                <span>Avg RT: {agent.statistics.averageResponseTime.toFixed(0)}ms</span>
              </div>
              
              {allowDirectControl && (
                <div className="agent-item__controls">
                  {agent.status === 'idle' ? (
                    <button onClick={(e) => { e.stopPropagation(); resumeAgent(agent.id); }} className="control-btn">
                      Resume
                    </button>
                  ) : (
                    <button onClick={(e) => { e.stopPropagation(); pauseAgent(agent.id); }} className="control-btn">
                      Pause
                    </button>
                  )}
                  <button onClick={(e) => { e.stopPropagation(); restartAgent(agent.id); }} className="control-btn">
                    Restart
                  </button>
                </div>
              )}
            </div>
          ))}
          
          {sortedAgents.length === 0 && (
            <div className="empty-agents">
              <p>No agents active. Start a narrative session to see agents here.</p>
            </div>
          )}
        </div>
        
        {selectedAgent && (
          <div className="agent-details">
            <div className="agent-details__header">
              <h4>{selectedAgent.name}</h4>
              {renderAgentStatus(selectedAgent.status)}
            </div>
            
            <div className="agent-capabilities">
              <h5>Capabilities</h5>
              <div className="capability-tags">
                {selectedAgent.capabilities.map(capability => (
                  <span key={capability} className="capability-tag">
                    {capability}
                  </span>
                ))}
              </div>
            </div>
            
            <div className="agent-relationships">
              <h5>Agent Relationships</h5>
              {Object.entries(selectedAgent.relationships).map(([agentId, weight]) => {
                const relatedAgent = agents.find(a => a.id === agentId);
                return relatedAgent ? (
                  <div key={agentId} className="relationship-item">
                    <span>{relatedAgent.name}</span>
                    <div className="relationship-strength">
                      <div 
                        className="relationship-bar" 
                        style={{ width: `${Math.abs(weight) * 100}%` }}
                      />
                      <span>{weight > 0 ? 'Positive' : 'Negative'}</span>
                    </div>
                  </div>
                ) : null;
              })}
            </div>
            
            {allowDirectControl && (
              <div className="agent-communication">
                <h5>Send Message</h5>
                <div className="message-controls">
                  <select
                    value={messageType}
                    onChange={(e) => setMessageType(e.target.value as AgentMessage['type'])}
                    className="message-type-select"
                  >
                    <option value="instruction">Instruction</option>
                    <option value="question">Question</option>
                    <option value="suggestion">Suggestion</option>
                    <option value="coordination">Coordination</option>
                  </select>
                  
                  <textarea
                    value={messageInput}
                    onChange={(e) => setMessageInput(e.target.value)}
                    placeholder={`Send ${messageType} to ${selectedAgent.name}...`}
                    className="message-input"
                    rows={3}
                  />
                  
                  <button
                    onClick={sendAgentMessage}
                    disabled={!messageInput.trim() || !wsState.isConnected}
                    className="send-message-btn"
                  >
                    Send {messageType}
                  </button>
                </div>
              </div>
            )}
            
            {isConfigPanelOpen && showAdvancedControls && renderParametersPanel()}
          </div>
        )}
      </div>
      
      <div className="agent-interface__footer">
        <div className="connection-status">
          {wsState.isConnected ? '🟢 Connected' : '🔴 Disconnected'}
        </div>
        <div className="coordination-status">
          Mode: {coordinationMode}
        </div>
      </div>
    </div>
  );
};

export default React.memo(AgentInterface);
