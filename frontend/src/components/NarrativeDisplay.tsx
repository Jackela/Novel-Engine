/**
 * Real-time Narrative Display Component
 * ====================================
 * 
 * Advanced React component for displaying dynamic narratives with:
 * - Real-time narrative streaming
 * - Performance-optimized rendering
 * - Virtual scrolling for large narratives
 * - Interactive story elements
 * - Agent action visualization
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { FixedSizeList as List } from 'react-window';
import { useWebSocketContext } from '../hooks/useWebSocket';
import { usePerformanceOptimizer } from '../hooks/usePerformanceOptimizer';
import './NarrativeDisplay.css';

// Types for narrative data
interface NarrativeEvent {
  id: string;
  type: 'action' | 'dialogue' | 'description' | 'system' | 'agent_thought';
  content: string;
  timestamp: number;
  agentId?: string;
  agentName?: string;
  metadata?: Record<string, any>;
  isStreaming?: boolean;
  confidence?: number;
  causality?: {
    causes: string[];
    effects: string[];
  };
}

interface AgentAction {
  agentId: string;
  agentName: string;
  action: string;
  target?: string;
  reasoning: string;
  timestamp: number;
  status: 'pending' | 'executing' | 'completed' | 'failed';
}

interface NarrativeState {
  events: NarrativeEvent[];
  activeAgents: string[];
  currentTurn: number;
  isGenerating: boolean;
  streamingEventId?: string;
}

interface NarrativeDisplayProps {
  sessionId: string;
  maxEvents?: number;
  enableVirtualization?: boolean;
  showAgentThoughts?: boolean;
  enableInteractivity?: boolean;
  className?: string;
}

const NarrativeDisplay: React.FC<NarrativeDisplayProps> = ({
  sessionId,
  maxEvents = 1000,
  enableVirtualization = true,
  showAgentThoughts = false,
  enableInteractivity = true,
  className = ''
}) => {
  const { state: wsState, sendMessage } = useWebSocketContext();
  const { 
    optimizeForRealTime, 
    createVirtualScrollConfig, 
    deferUpdate,
    measureInteractionDelay 
  } = usePerformanceOptimizer();

  const listRef = useRef<List>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const lastEventRef = useRef<string>('');

  const [narrativeState, setNarrativeState] = useState<NarrativeState>({
    events: [],
    activeAgents: [],
    currentTurn: 0,
    isGenerating: false
  });

  const [agentActions, setAgentActions] = useState<AgentAction[]>([]);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>('all');
  const [autoScroll, setAutoScroll] = useState(true);

  // Virtual scrolling configuration
  const virtualConfig = useMemo(() => {
    const containerHeight = scrollContainerRef.current?.clientHeight || 600;
    return createVirtualScrollConfig(narrativeState.events.length, 80, containerHeight);
  }, [narrativeState.events.length, createVirtualScrollConfig]);

  // Filtered events based on type and visibility settings
  const filteredEvents = useMemo(() => {
    return narrativeState.events.filter(event => {
      if (filterType !== 'all' && event.type !== filterType) return false;
      if (!showAgentThoughts && event.type === 'agent_thought') return false;
      return true;
    });
  }, [narrativeState.events, filterType, showAgentThoughts]);

  // WebSocket event handlers
  const handleWebSocketMessage = useCallback((event: CustomEvent) => {
    const message = event.detail;
    
    switch (message.type) {
      case 'narrative_event':
        deferUpdate(() => {
          setNarrativeState(prev => {
            const newEvents = [...prev.events];
            
            if (message.data.isStreaming && message.data.id === prev.streamingEventId) {
              // Update existing streaming event
              const eventIndex = newEvents.findIndex(e => e.id === message.data.id);
              if (eventIndex >= 0) {
                newEvents[eventIndex] = { ...newEvents[eventIndex], ...message.data };
              }
            } else {
              // Add new event
              newEvents.push(message.data);
              if (newEvents.length > maxEvents) {
                newEvents.shift(); // Remove oldest event
              }
            }
            
            return {
              ...prev,
              events: newEvents,
              streamingEventId: message.data.isStreaming ? message.data.id : undefined
            };
          });
        });
        break;
        
      case 'agent_action':
        setAgentActions(prev => {
          const newActions = [...prev];
          const existingIndex = newActions.findIndex(a => a.agentId === message.data.agentId);
          
          if (existingIndex >= 0) {
            newActions[existingIndex] = message.data;
          } else {
            newActions.push(message.data);
            if (newActions.length > 20) {
              newActions.shift();
            }
          }
          
          return newActions;
        });
        break;
        
      case 'narrative_state':
        setNarrativeState(prev => ({
          ...prev,
          activeAgents: message.data.activeAgents || [],
          currentTurn: message.data.currentTurn || prev.currentTurn,
          isGenerating: message.data.isGenerating || false
        }));
        break;
    }
  }, [deferUpdate, maxEvents]);

  // Auto-scroll to latest event
  useEffect(() => {
    if (autoScroll && listRef.current && filteredEvents.length > 0) {
      const lastEvent = filteredEvents[filteredEvents.length - 1];
      if (lastEvent.id !== lastEventRef.current) {
        listRef.current.scrollToItem(filteredEvents.length - 1, 'end');
        lastEventRef.current = lastEvent.id;
      }
    }
  }, [filteredEvents, autoScroll]);

  // WebSocket message listener
  useEffect(() => {
    window.addEventListener('websocket-message', handleWebSocketMessage);
    
    // Request initial narrative state
    if (wsState.isConnected) {
      sendMessage({
        type: 'get_narrative_state',
        data: { sessionId },
        priority: 'normal'
      });
    }
    
    return () => {
      window.removeEventListener('websocket-message', handleWebSocketMessage);
    };
  }, [handleWebSocketMessage, wsState.isConnected, sendMessage, sessionId]);

  // Performance optimization
  useEffect(() => {
    optimizeForRealTime();
  }, [optimizeForRealTime]);

  // Event interaction handlers
  const handleEventClick = useCallback((eventId: string) => {
    if (!enableInteractivity) return;
    
    measureInteractionDelay(() => {
      setSelectedEventId(prev => prev === eventId ? null : eventId);
    });
  }, [enableInteractivity, measureInteractionDelay]);

  const handleEventAction = useCallback((eventId: string, action: string) => {
    if (!wsState.isConnected) return;
    
    sendMessage({
      type: 'narrative_action',
      data: {
        sessionId,
        eventId,
        action
      },
      priority: 'normal'
    });
  }, [wsState.isConnected, sendMessage, sessionId]);

  // Render individual narrative event
  const renderEvent = useCallback(({ index, style }: { index: number; style: React.CSSProperties }) => {
    const event = filteredEvents[index];
    if (!event) return null;
    
    const isSelected = selectedEventId === event.id;
    const isStreaming = event.isStreaming;
    
    return (
      <div
        style={style}
        className={`narrative-event narrative-event--${event.type} ${isSelected ? 'narrative-event--selected' : ''} ${isStreaming ? 'narrative-event--streaming' : ''}`}
        onClick={() => handleEventClick(event.id)}
        data-event-id={event.id}
      >
        <div className="narrative-event__header">
          {event.agentName && (
            <span className="narrative-event__agent">{event.agentName}</span>
          )}
          <span className="narrative-event__type">{event.type}</span>
          <span className="narrative-event__timestamp">
            {new Date(event.timestamp).toLocaleTimeString()}
          </span>
          {event.confidence && (
            <span className="narrative-event__confidence">
              {Math.round(event.confidence * 100)}%
            </span>
          )}
        </div>
        
        <div className="narrative-event__content">
          {event.content}
          {isStreaming && <span className="narrative-event__cursor">|</span>}
        </div>
        
        {isSelected && event.causality && (
          <div className="narrative-event__causality">
            {event.causality.causes.length > 0 && (
              <div className="causality__section">
                <strong>Causes:</strong>
                <ul>
                  {event.causality.causes.map((cause, idx) => (
                    <li key={idx}>{cause}</li>
                  ))}
                </ul>
              </div>
            )}
            {event.causality.effects.length > 0 && (
              <div className="causality__section">
                <strong>Effects:</strong>
                <ul>
                  {event.causality.effects.map((effect, idx) => (
                    <li key={idx}>{effect}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
        
        {isSelected && enableInteractivity && (
          <div className="narrative-event__actions">
            <button 
              onClick={(e) => {
                e.stopPropagation();
                handleEventAction(event.id, 'expand');
              }}
              className="event-action-btn"
            >
              Expand
            </button>
            <button 
              onClick={(e) => {
                e.stopPropagation();
                handleEventAction(event.id, 'branch');
              }}
              className="event-action-btn"
            >
              Branch Story
            </button>
          </div>
        )}
      </div>
    );
  }, [filteredEvents, selectedEventId, handleEventClick, handleEventAction, enableInteractivity]);

  // Agent actions sidebar
  const renderAgentActions = () => (
    <div className="agent-actions">
      <h3>Active Agents</h3>
      {agentActions.map(action => (
        <div key={action.agentId} className={`agent-action agent-action--${action.status}`}>
          <div className="agent-action__header">
            <strong>{action.agentName}</strong>
            <span className="agent-action__status">{action.status}</span>
          </div>
          <div className="agent-action__details">
            <div className="action-text">{action.action}</div>
            {action.target && <div className="action-target">→ {action.target}</div>}
            <div className="action-reasoning">{action.reasoning}</div>
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <div className={`narrative-display ${className}`}>
      <div className="narrative-display__header">
        <div className="narrative-controls">
          <select 
            value={filterType} 
            onChange={(e) => setFilterType(e.target.value)}
            className="narrative-filter"
          >
            <option value="all">All Events</option>
            <option value="action">Actions</option>
            <option value="dialogue">Dialogue</option>
            <option value="description">Descriptions</option>
            <option value="system">System</option>
            {showAgentThoughts && <option value="agent_thought">Agent Thoughts</option>}
          </select>
          
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`control-btn ${autoScroll ? 'active' : ''}`}
          >
            Auto Scroll
          </button>
          
          <button
            onClick={() => setShowAgentThoughts(!showAgentThoughts)}
            className={`control-btn ${showAgentThoughts ? 'active' : ''}`}
          >
            Show Thoughts
          </button>
        </div>
        
        <div className="narrative-status">
          <span className="turn-counter">Turn {narrativeState.currentTurn}</span>
          <span className="active-agents">
            Active: {narrativeState.activeAgents.length}
          </span>
          {narrativeState.isGenerating && (
            <span className="generating-indicator">Generating...</span>
          )}
          <span className="connection-status">
            {wsState.isConnected ? '🟢 Connected' : '🔴 Disconnected'}
          </span>
        </div>
      </div>
      
      <div className="narrative-display__content">
        <div className="narrative-events" ref={scrollContainerRef}>
          {enableVirtualization && filteredEvents.length > 50 ? (
            <List
              ref={listRef}
              height={600}
              itemCount={filteredEvents.length}
              itemSize={80}
              width="100%"
              overscanCount={virtualConfig.overscan}
            >
              {renderEvent}
            </List>
          ) : (
            <div className="narrative-events-list">
              {filteredEvents.map((event, index) => (
                <div key={event.id}>
                  {renderEvent({ index, style: {} })}
                </div>
              ))}
            </div>
          )}
          
          {filteredEvents.length === 0 && (
            <div className="empty-narrative">
              <p>No narrative events yet. Start a new story to see content here.</p>
            </div>
          )}
        </div>
        
        {agentActions.length > 0 && renderAgentActions()}
      </div>
    </div>
  );
};

export default React.memo(NarrativeDisplay);