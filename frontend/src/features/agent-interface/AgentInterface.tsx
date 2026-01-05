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
import { useWebSocketContext } from '@/hooks/useWebSocket';
import { usePerformanceOptimizer } from '@/hooks/usePerformanceOptimizer';
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

const STATUS_PRIORITY: Record<Agent['status'], number> = {
  acting: 0,
  thinking: 1,
  waiting: 2,
  idle: 3,
  error: 4,
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

const getDefaultStatistics = (): AgentStatistics => ({
  actionsPerformed: 0,
  averageResponseTime: 0,
  successRate: 1.0,
  collaborations: 0,
  decisionsInfluenced: 0,
  narrativeContributions: 0,
});

const updateAgentsFromStatus = (
  prevAgents: Agent[],
  message: { data: Partial<Agent> & { agentId: string } },
  maxAgents: number
) => {
  const newAgents = [...prevAgents];
  const agentIndex = newAgents.findIndex((agent) => agent.id === message.data.agentId);

  if (agentIndex >= 0) {
    newAgents[agentIndex] = {
      ...newAgents[agentIndex],
      ...message.data,
      lastActivity: Date.now(),
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
  });

  return newAgents;
};

const sortAgentsByStatus = (agents: Agent[]) =>
  [...agents].sort((a, b) => {
    const aPriority = STATUS_PRIORITY[a.status];
    const bPriority = STATUS_PRIORITY[b.status];
    if (aPriority !== bPriority) return aPriority - bPriority;
    return b.lastActivity - a.lastActivity;
  });

const AgentStatusIndicator: React.FC<{ status: Agent['status'] }> = ({ status }) => {
  const statusConfig = {
    idle: { color: 'var(--color-text-secondary)', icon: '⏸️', label: 'Idle' },
    thinking: { color: 'var(--color-warning)', icon: '🤔', label: 'Thinking' },
    acting: { color: 'var(--color-success)', icon: '⚡', label: 'Acting' },
    waiting: { color: 'var(--color-info)', icon: '⏳', label: 'Waiting' },
    error: { color: 'var(--color-error)', icon: '❌', label: 'Error' },
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

const useSortedAgents = (agents: Agent[]) =>
  useMemo(() => sortAgentsByStatus(agents), [agents]);

const useSelectedAgent = (agents: Agent[], selectedAgentId: string | null) =>
  useMemo(() => agents.find((agent) => agent.id === selectedAgentId) || null, [agents, selectedAgentId]);

const useAutoSelectAgent = (
  selectedAgentId: string | null,
  agents: Agent[],
  setSelectedAgentId: React.Dispatch<React.SetStateAction<string | null>>
) => {
  useEffect(() => {
    if (!selectedAgentId && agents.length > 0) {
      setSelectedAgentId(agents[0].id);
    }
  }, [selectedAgentId, agents, setSelectedAgentId]);
};

const useAgentWebSocket = (params: {
  deferUpdate: (callback: () => void) => void;
  maxAgents: number;
  sessionId: string;
  wsState: { isConnected: boolean };
  sendMessage: (payload: { type: string; data: Record<string, unknown>; priority: 'normal' }) => void;
  setAgents: React.Dispatch<React.SetStateAction<Agent[]>>;
  setMessages: React.Dispatch<React.SetStateAction<AgentMessage[]>>;
  selectedAgentId: string | null;
  setSelectedAgentId: React.Dispatch<React.SetStateAction<string | null>>;
}) => {
  const {
    deferUpdate,
    maxAgents,
    sessionId,
    wsState,
    sendMessage,
    setAgents,
    setMessages,
    selectedAgentId,
    setSelectedAgentId,
  } = params;

  const handleWebSocketMessage = useCallback(
    (event: CustomEvent) => {
      const message = event.detail;

      switch (message.type) {
        case 'agent_status_update':
          deferUpdate(() => {
            setAgents((prev) => updateAgentsFromStatus(prev, message, maxAgents));
          });
          break;

        case 'agent_message':
          setMessages((prev) => {
            const newMessages = [...prev, message.data];
            return newMessages.slice(-100);
          });
          break;

        case 'agent_removed':
          setAgents((prev) => prev.filter((agent) => agent.id !== message.data.agentId));
          if (selectedAgentId === message.data.agentId) {
            setSelectedAgentId(null);
          }
          break;
      }
    },
    [deferUpdate, maxAgents, selectedAgentId, setAgents, setMessages, setSelectedAgentId]
  );

  useEffect(() => {
    window.addEventListener('websocket-message', handleWebSocketMessage as EventListener);

    if (wsState.isConnected) {
      sendMessage({
        type: 'get_agent_status',
        data: { sessionId },
        priority: 'normal',
      });
    }

    return () => {
      window.removeEventListener('websocket-message', handleWebSocketMessage as EventListener);
    };
  }, [handleWebSocketMessage, wsState.isConnected, sendMessage, sessionId]);
};

const AgentParameterSliders: React.FC<{
  title: string;
  agentId: string;
  parameters: AgentParameters;
  fields: ReadonlyArray<keyof AgentParameters>;
  onChange: (param: keyof AgentParameters, value: number | string) => void;
  idSuffix?: string;
}> = ({ title, agentId, parameters, fields, onChange, idSuffix = '' }) => (
  <div className="parameter-group">
    <h5>{title}</h5>
    {fields.map((param) => {
      const sliderId = `${agentId}-${param}${idSuffix}`;
      return (
        <div key={param} className="parameter-control">
          <label htmlFor={sliderId}>{param.replace(/([A-Z])/g, ' $1').trim()}</label>
          <input
            id={sliderId}
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={parameters[param] as number}
            onChange={(event) => onChange(param, parseFloat(event.target.value))}
            className="parameter-slider"
          />
          <span className="parameter-value">{((parameters[param] as number) * 100).toFixed(0)}%</span>
        </div>
      );
    })}
  </div>
);

const AgentBehaviorSettings: React.FC<{
  agentId: string;
  parameters: AgentParameters;
  onChange: (param: keyof AgentParameters, value: number | string) => void;
}> = ({ agentId, parameters, onChange }) => (
  <div className="parameter-group">
    <h5>Behavior Settings</h5>
    <div className="parameter-control">
      <label htmlFor={`narrative-focus-${agentId}`}>Narrative Focus</label>
      <select
        id={`narrative-focus-${agentId}`}
        value={parameters.narrativeFocus}
        onChange={(event) => onChange('narrativeFocus', event.target.value)}
        className="parameter-select"
      >
        <option value="character">Character-focused</option>
        <option value="plot">Plot-focused</option>
        <option value="world">World-building</option>
        <option value="mixed">Mixed approach</option>
      </select>
    </div>

    <div className="parameter-control">
      <label htmlFor={`communication-style-${agentId}`}>Communication Style</label>
      <select
        id={`communication-style-${agentId}`}
        value={parameters.communicationStyle}
        onChange={(event) => onChange('communicationStyle', event.target.value)}
        className="parameter-select"
      >
        <option value="formal">Formal</option>
        <option value="casual">Casual</option>
        <option value="descriptive">Descriptive</option>
        <option value="concise">Concise</option>
      </select>
    </div>
  </div>
);

const AgentParametersPanel: React.FC<{
  selectedAgent: Agent;
  onUpdateParameters: (agentId: string, parameters: Partial<AgentParameters>) => void;
}> = ({ selectedAgent, onUpdateParameters }) => {
  const handleParameterChange = (param: keyof AgentParameters, value: number | string) => {
    const newParameters = { ...selectedAgent.parameters, [param]: value };
    onUpdateParameters(selectedAgent.id, newParameters);
  };

  return (
    <div className="agent-parameters">
      <h4>Agent Parameters</h4>
      <AgentParameterSliders
        title="Core Attributes"
        agentId={selectedAgent.id}
        parameters={selectedAgent.parameters}
        fields={['creativity', 'consistency', 'responsiveness', 'autonomy']}
        onChange={handleParameterChange}
      />
      <AgentParameterSliders
        title="Social Attributes"
        agentId={selectedAgent.id}
        parameters={selectedAgent.parameters}
        fields={['collaboration', 'riskTolerance', 'memoryRetention']}
        onChange={handleParameterChange}
        idSuffix="-slider"
      />
      <AgentBehaviorSettings
        agentId={selectedAgent.id}
        parameters={selectedAgent.parameters}
        onChange={handleParameterChange}
      />
    </div>
  );
};

const AgentRelationships: React.FC<{ selectedAgent: Agent; agents: Agent[] }> = ({ selectedAgent, agents }) => (
  <div className="agent-relationships">
    <h5>Agent Relationships</h5>
    {Object.entries(selectedAgent.relationships).map(([agentId, weight]) => {
      const relatedAgent = agents.find((agent) => agent.id === agentId);
      return relatedAgent ? (
        <div key={agentId} className="relationship-item">
          <span>{relatedAgent.name}</span>
          <div className="relationship-strength">
            <div className="relationship-bar" style={{ width: `${Math.abs(weight) * 100}%` }} />
            <span>{weight > 0 ? 'Positive' : 'Negative'}</span>
          </div>
        </div>
      ) : null;
    })}
  </div>
);

const AgentMessageComposer: React.FC<{
  selectedAgent: Agent;
  messageType: AgentMessage['type'];
  messageInput: string;
  onMessageTypeChange: (value: AgentMessage['type']) => void;
  onMessageInputChange: (value: string) => void;
  onSend: () => void;
  isConnected: boolean;
}> = ({
  selectedAgent,
  messageType,
  messageInput,
  onMessageTypeChange,
  onMessageInputChange,
  onSend,
  isConnected,
}) => (
  <div className="agent-communication">
    <h5>Send Message</h5>
    <div className="message-controls">
      <select
        value={messageType}
        onChange={(event) => onMessageTypeChange(event.target.value as AgentMessage['type'])}
        className="message-type-select"
      >
        <option value="instruction">Instruction</option>
        <option value="question">Question</option>
        <option value="suggestion">Suggestion</option>
        <option value="coordination">Coordination</option>
      </select>

      <textarea
        value={messageInput}
        onChange={(event) => onMessageInputChange(event.target.value)}
        placeholder={`Send ${messageType} to ${selectedAgent.name}...`}
        className="message-input"
        rows={3}
      />

      <button
        onClick={onSend}
        disabled={!messageInput.trim() || !isConnected}
        className="send-message-btn"
      >
        Send {messageType}
      </button>
    </div>
  </div>
);

const AgentList: React.FC<{
  agents: Agent[];
  selectedAgentId: string | null;
  allowDirectControl: boolean;
  onSelect: (agentId: string) => void;
  onPause: (agentId: string) => void;
  onResume: (agentId: string) => void;
  onRestart: (agentId: string) => void;
}> = ({ agents, selectedAgentId, allowDirectControl, onSelect, onPause, onResume, onRestart }) => (
  <div className="agent-list">
    <h4>Active Agents ({agents.length})</h4>
    {agents.map((agent) => (
      <div
        key={agent.id}
        className={`agent-item ${selectedAgentId === agent.id ? 'selected' : ''}`}
        onClick={() => onSelect(agent.id)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            onSelect(agent.id);
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
          <AgentStatusIndicator status={agent.status} />
          {agent.currentAction && <span className="agent-action">{agent.currentAction}</span>}
        </div>

        <div className="agent-item__stats">
          <span>Actions: {agent.statistics.actionsPerformed}</span>
          <span>Success: {(agent.statistics.successRate * 100).toFixed(0)}%</span>
          <span>Avg RT: {agent.statistics.averageResponseTime.toFixed(0)}ms</span>
        </div>

        {allowDirectControl && (
          <div className="agent-item__controls">
            {agent.status === 'idle' ? (
              <button onClick={(event) => { event.stopPropagation(); onResume(agent.id); }} className="control-btn">
                Resume
              </button>
            ) : (
              <button onClick={(event) => { event.stopPropagation(); onPause(agent.id); }} className="control-btn">
                Pause
              </button>
            )}
            <button onClick={(event) => { event.stopPropagation(); onRestart(agent.id); }} className="control-btn">
              Restart
            </button>
          </div>
        )}
      </div>
    ))}

    {agents.length === 0 && (
      <div className="empty-agents">
        <p>No agents active. Start a narrative session to see agents here.</p>
      </div>
    )}
  </div>
);

const AgentInterfaceBody: React.FC<{
  className: string;
  coordinationMode: 'autonomous' | 'guided' | 'manual';
  showAdvancedControls: boolean;
  isConfigPanelOpen: boolean;
  setCoordinationMode: (value: 'autonomous' | 'guided' | 'manual') => void;
  setIsConfigPanelOpen: (value: boolean) => void;
  sortedAgents: Agent[];
  selectedAgentId: string | null;
  allowDirectControl: boolean;
  onSelectAgent: (agentId: string) => void;
  onPauseAgent: (agentId: string) => void;
  onResumeAgent: (agentId: string) => void;
  onRestartAgent: (agentId: string) => void;
  selectedAgent: Agent | null;
  agents: Agent[];
  messageType: AgentMessage['type'];
  messageInput: string;
  onMessageTypeChange: (value: AgentMessage['type']) => void;
  onMessageInputChange: (value: string) => void;
  onSendMessage: () => void;
  isConnected: boolean;
  onUpdateParameters: (agentId: string, parameters: Partial<AgentParameters>) => void;
}> = ({
  className,
  coordinationMode,
  showAdvancedControls,
  isConfigPanelOpen,
  setCoordinationMode,
  setIsConfigPanelOpen,
  sortedAgents,
  selectedAgentId,
  allowDirectControl,
  onSelectAgent,
  onPauseAgent,
  onResumeAgent,
  onRestartAgent,
  selectedAgent,
  agents,
  messageType,
  messageInput,
  onMessageTypeChange,
  onMessageInputChange,
  onSendMessage,
  isConnected,
  onUpdateParameters,
}) => (
  <div className={`agent-interface ${className}`}>
    <AgentInterfaceHeader
      coordinationMode={coordinationMode}
      showAdvancedControls={showAdvancedControls}
      isConfigPanelOpen={isConfigPanelOpen}
      setCoordinationMode={setCoordinationMode}
      setIsConfigPanelOpen={setIsConfigPanelOpen}
    />
    <AgentInterfaceContent
      sortedAgents={sortedAgents}
      selectedAgentId={selectedAgentId}
      allowDirectControl={allowDirectControl}
      onSelectAgent={onSelectAgent}
      onPauseAgent={onPauseAgent}
      onResumeAgent={onResumeAgent}
      onRestartAgent={onRestartAgent}
      selectedAgent={selectedAgent}
      agents={agents}
      messageType={messageType}
      messageInput={messageInput}
      onMessageTypeChange={onMessageTypeChange}
      onMessageInputChange={onMessageInputChange}
      onSendMessage={onSendMessage}
      isConnected={isConnected}
      isConfigPanelOpen={isConfigPanelOpen}
      showAdvancedControls={showAdvancedControls}
      onUpdateParameters={onUpdateParameters}
    />
    <AgentInterfaceFooter isConnected={isConnected} coordinationMode={coordinationMode} />
  </div>
);

const AgentInterfaceHeader: React.FC<{
  coordinationMode: 'autonomous' | 'guided' | 'manual';
  showAdvancedControls: boolean;
  isConfigPanelOpen: boolean;
  setCoordinationMode: (value: 'autonomous' | 'guided' | 'manual') => void;
  setIsConfigPanelOpen: (value: boolean) => void;
}> = ({ coordinationMode, showAdvancedControls, isConfigPanelOpen, setCoordinationMode, setIsConfigPanelOpen }) => (
  <div className="agent-interface__header">
    <h3>Agent Management</h3>
    <div className="agent-controls">
      <select
        value={coordinationMode}
        onChange={(event) => setCoordinationMode(event.target.value as 'autonomous' | 'guided' | 'manual')}
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
);

const AgentInterfaceContent: React.FC<{
  sortedAgents: Agent[];
  selectedAgentId: string | null;
  allowDirectControl: boolean;
  onSelectAgent: (agentId: string) => void;
  onPauseAgent: (agentId: string) => void;
  onResumeAgent: (agentId: string) => void;
  onRestartAgent: (agentId: string) => void;
  selectedAgent: Agent | null;
  agents: Agent[];
  messageType: AgentMessage['type'];
  messageInput: string;
  onMessageTypeChange: (value: AgentMessage['type']) => void;
  onMessageInputChange: (value: string) => void;
  onSendMessage: () => void;
  isConnected: boolean;
  isConfigPanelOpen: boolean;
  showAdvancedControls: boolean;
  onUpdateParameters: (agentId: string, parameters: Partial<AgentParameters>) => void;
}> = ({
  sortedAgents,
  selectedAgentId,
  allowDirectControl,
  onSelectAgent,
  onPauseAgent,
  onResumeAgent,
  onRestartAgent,
  selectedAgent,
  agents,
  messageType,
  messageInput,
  onMessageTypeChange,
  onMessageInputChange,
  onSendMessage,
  isConnected,
  isConfigPanelOpen,
  showAdvancedControls,
  onUpdateParameters,
}) => (
  <div className="agent-interface__content">
    <AgentList
      agents={sortedAgents}
      selectedAgentId={selectedAgentId}
      allowDirectControl={allowDirectControl}
      onSelect={onSelectAgent}
      onPause={onPauseAgent}
      onResume={onResumeAgent}
      onRestart={onRestartAgent}
    />

    {selectedAgent && (
      <div className="agent-details">
        <div className="agent-details__header">
          <h4>{selectedAgent.name}</h4>
          <AgentStatusIndicator status={selectedAgent.status} />
        </div>

        <div className="agent-capabilities">
          <h5>Capabilities</h5>
          <div className="capability-tags">
            {selectedAgent.capabilities.map((capability) => (
              <span key={capability} className="capability-tag">
                {capability}
              </span>
            ))}
          </div>
        </div>

        <AgentRelationships selectedAgent={selectedAgent} agents={agents} />

        {allowDirectControl && (
          <AgentMessageComposer
            selectedAgent={selectedAgent}
            messageType={messageType}
            messageInput={messageInput}
            onMessageTypeChange={onMessageTypeChange}
            onMessageInputChange={onMessageInputChange}
            onSend={onSendMessage}
            isConnected={isConnected}
          />
        )}

        {isConfigPanelOpen && showAdvancedControls && (
          <AgentParametersPanel selectedAgent={selectedAgent} onUpdateParameters={onUpdateParameters} />
        )}
      </div>
    )}
  </div>
);

const AgentInterfaceFooter: React.FC<{
  isConnected: boolean;
  coordinationMode: 'autonomous' | 'guided' | 'manual';
}> = ({ isConnected, coordinationMode }) => (
  <div className="agent-interface__footer">
    <div className="connection-status">{isConnected ? '🟢 Connected' : '🔴 Disconnected'}</div>
    <div className="coordination-status">Mode: {coordinationMode}</div>
  </div>
);

const useAgentInterfaceState = (params: {
  sessionId: string;
  maxAgents: number;
}) => {
  const { state: wsState, sendMessage } = useWebSocketContext();
  const { deferUpdate, measureInteractionDelay } = usePerformanceOptimizer();

  const state = useAgentInterfaceStateValues();
  const derived = useAgentInterfaceDerived(state.agents, state.selectedAgentId);
  const actions = useAgentInterfaceActions({
    sessionId: params.sessionId,
    wsState,
    sendMessage,
    measureInteractionDelay,
    messageInput: state.messageInput,
    setMessageInput: state.setMessageInput,
    messageType: state.messageType,
    selectedAgentId: state.selectedAgentId,
  });

  useAgentWebSocket({
    deferUpdate,
    maxAgents: params.maxAgents,
    sessionId: params.sessionId,
    wsState,
    sendMessage,
    setAgents: state.setAgents,
    setMessages: state.setMessages,
    selectedAgentId: state.selectedAgentId,
    setSelectedAgentId: state.setSelectedAgentId,
  });

  useAutoSelectAgent(state.selectedAgentId, derived.sortedAgents, state.setSelectedAgentId);

  return {
    wsState,
    agents: state.agents,
    sortedAgents: derived.sortedAgents,
    selectedAgent: derived.selectedAgent,
    selectedAgentId: state.selectedAgentId,
    setSelectedAgentId: state.setSelectedAgentId,
    messageInput: state.messageInput,
    setMessageInput: state.setMessageInput,
    messageType: state.messageType,
    setMessageType: state.setMessageType,
    isConfigPanelOpen: state.isConfigPanelOpen,
    setIsConfigPanelOpen: state.setIsConfigPanelOpen,
    coordinationMode: state.coordinationMode,
    setCoordinationMode: state.setCoordinationMode,
    sendAgentMessage: actions.sendAgentMessage,
    updateAgentParameters: actions.updateAgentParameters,
    pauseAgent: actions.pauseAgent,
    resumeAgent: actions.resumeAgent,
    restartAgent: actions.restartAgent,
  };
};

const useAgentInterfaceStateValues = () => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [, setMessages] = useState<AgentMessage[]>([]);
  const [messageInput, setMessageInput] = useState('');
  const [messageType, setMessageType] = useState<AgentMessage['type']>('instruction');
  const [isConfigPanelOpen, setIsConfigPanelOpen] = useState(false);
  const [coordinationMode, setCoordinationMode] = useState<'autonomous' | 'guided' | 'manual'>('autonomous');

  return {
    agents,
    setAgents,
    selectedAgentId,
    setSelectedAgentId,
    setMessages,
    messageInput,
    setMessageInput,
    messageType,
    setMessageType,
    isConfigPanelOpen,
    setIsConfigPanelOpen,
    coordinationMode,
    setCoordinationMode,
  };
};

const useAgentInterfaceDerived = (agents: Agent[], selectedAgentId: string | null) => ({
  selectedAgent: useSelectedAgent(agents, selectedAgentId),
  sortedAgents: useSortedAgents(agents),
});

const useAgentMessageActions = (params: {
  sessionId: string;
  wsState: { isConnected: boolean };
  sendMessage: (payload: { type: string; data: Record<string, unknown>; priority: 'normal' }) => void;
  measureInteractionDelay: (callback: () => void) => void;
  messageInput: string;
  setMessageInput: React.Dispatch<React.SetStateAction<string>>;
  messageType: AgentMessage['type'];
  selectedAgentId: string | null;
}) => {
  const {
    sessionId,
    wsState,
    sendMessage,
    measureInteractionDelay,
    messageInput,
    setMessageInput,
    messageType,
    selectedAgentId,
  } = params;

  const sendAgentMessage = useCallback(() => {
    if (!messageInput.trim() || !wsState.isConnected) return;

    measureInteractionDelay(() => {
      const message: Omit<AgentMessage, 'id' | 'timestamp'> = {
        fromAgentId: 'user',
        toAgentId: selectedAgentId ?? undefined,
        content: messageInput.trim(),
        type: messageType,
        priority: 'normal',
        requiresResponse: messageType === 'question',
      };

      sendMessage({
        type: 'agent_message',
        data: {
          sessionId,
          ...message,
        },
        priority: 'normal',
      });
      setMessageInput('');
    });
  }, [
    messageInput,
    messageType,
    selectedAgentId,
    wsState.isConnected,
    measureInteractionDelay,
    sendMessage,
    sessionId,
    setMessageInput,
  ]);

  const updateAgentParameters = useCallback(
    (agentId: string, parameters: Partial<AgentParameters>) => {
      if (!wsState.isConnected) return;

      sendMessage({
        type: 'update_agent_parameters',
        data: {
          sessionId,
          agentId,
          parameters,
        },
        priority: 'normal',
      });
    },
    [wsState.isConnected, sendMessage, sessionId]
  );

  return { sendAgentMessage, updateAgentParameters };
};

const useAgentControlActions = (params: {
  sessionId: string;
  sendMessage: (payload: { type: string; data: Record<string, unknown>; priority: 'high' }) => void;
}) => {
  const { sessionId, sendMessage } = params;

  const pauseAgent = useCallback(
    (agentId: string) => {
      sendMessage({
        type: 'pause_agent',
        data: { sessionId, agentId },
        priority: 'high',
      });
    },
    [sendMessage, sessionId]
  );

  const resumeAgent = useCallback(
    (agentId: string) => {
      sendMessage({
        type: 'resume_agent',
        data: { sessionId, agentId },
        priority: 'high',
      });
    },
    [sendMessage, sessionId]
  );

  const restartAgent = useCallback(
    (agentId: string) => {
      sendMessage({
        type: 'restart_agent',
        data: { sessionId, agentId },
        priority: 'high',
      });
    },
    [sendMessage, sessionId]
  );

  return { pauseAgent, resumeAgent, restartAgent };
};

const useAgentInterfaceActions = (params: {
  sessionId: string;
  wsState: { isConnected: boolean };
  sendMessage: (payload: { type: string; data: Record<string, unknown>; priority: 'normal' | 'high' }) => void;
  measureInteractionDelay: (callback: () => void) => void;
  messageInput: string;
  setMessageInput: React.Dispatch<React.SetStateAction<string>>;
  messageType: AgentMessage['type'];
  selectedAgentId: string | null;
}) => {
  const messageActions = useAgentMessageActions({
    sessionId: params.sessionId,
    wsState: params.wsState,
    sendMessage: params.sendMessage,
    measureInteractionDelay: params.measureInteractionDelay,
    messageInput: params.messageInput,
    setMessageInput: params.setMessageInput,
    messageType: params.messageType,
    selectedAgentId: params.selectedAgentId,
  });

  const controlActions = useAgentControlActions({
    sessionId: params.sessionId,
    sendMessage: params.sendMessage,
  });

  return {
    ...messageActions,
    ...controlActions,
  };
};
const AgentInterface: React.FC<AgentInterfaceProps> = ({
  sessionId,
  allowDirectControl = true,
  showAdvancedControls = false,
  maxAgents = 10,
  className = ''
}) => {
  const {
    wsState,
    agents,
    sortedAgents,
    selectedAgent,
    selectedAgentId,
    setSelectedAgentId,
    messageInput,
    setMessageInput,
    messageType,
    setMessageType,
    isConfigPanelOpen,
    setIsConfigPanelOpen,
    coordinationMode,
    setCoordinationMode,
    sendAgentMessage,
    updateAgentParameters,
    pauseAgent,
    resumeAgent,
    restartAgent,
  } = useAgentInterfaceState({ sessionId, maxAgents });

  return (
    <AgentInterfaceBody
      className={className}
      coordinationMode={coordinationMode}
      showAdvancedControls={showAdvancedControls}
      isConfigPanelOpen={isConfigPanelOpen}
      setCoordinationMode={setCoordinationMode}
      setIsConfigPanelOpen={setIsConfigPanelOpen}
      sortedAgents={sortedAgents}
      selectedAgentId={selectedAgentId}
      allowDirectControl={allowDirectControl}
      onSelectAgent={setSelectedAgentId}
      onPauseAgent={pauseAgent}
      onResumeAgent={resumeAgent}
      onRestartAgent={restartAgent}
      selectedAgent={selectedAgent}
      agents={agents}
      messageType={messageType}
      messageInput={messageInput}
      onMessageTypeChange={setMessageType}
      onMessageInputChange={setMessageInput}
      onSendMessage={sendAgentMessage}
      isConnected={wsState.isConnected}
      onUpdateParameters={updateAgentParameters}
    />
  );
};

export default React.memo(AgentInterface);
