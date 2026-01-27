import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { FixedSizeList as List } from 'react-window';
import { useWebSocketContext } from '@/hooks/useWebSocket';
import { usePerformanceOptimizer } from '@/hooks/usePerformanceOptimizer';
import './NarrativeDisplay.css';

interface NarrativeEvent {
  id: string;
  type: 'action' | 'dialogue' | 'description' | 'system' | 'agent_thought';
  content: string;
  timestamp: number;
  agentId?: string;
  agentName?: string;
  metadata?: Record<string, unknown>;
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
  streamingEventId: string | undefined;
}

interface NarrativeDisplayProps {
  sessionId: string;
  maxEvents?: number;
  enableVirtualization?: boolean;
  showAgentThoughts?: boolean;
  enableInteractivity?: boolean;
  className?: string;
}

const DEFAULT_STATE: NarrativeState = {
  events: [],
  activeAgents: [],
  currentTurn: 0,
  isGenerating: false,
  streamingEventId: undefined,
};

type NarrativeFilterType = 'all' | NarrativeEvent['type'];

const shouldIncludeEvent = (
  event: NarrativeEvent,
  filterType: NarrativeFilterType,
  showThoughts: boolean
) => {
  if (filterType !== 'all' && event.type !== filterType) return false;
  if (!showThoughts && event.type === 'agent_thought') return false;
  return true;
};

const updateEventsForMessage = (
  prevState: NarrativeState,
  payload: NarrativeEvent,
  maxEvents: number
) => {
  const newEvents = [...prevState.events];

  if (payload.isStreaming && payload.id === prevState.streamingEventId) {
    const eventIndex = newEvents.findIndex((event) => event.id === payload.id);
    if (eventIndex >= 0) {
      newEvents[eventIndex] = { ...newEvents[eventIndex], ...payload };
    }
  } else {
    newEvents.push(payload);
    if (newEvents.length > maxEvents) {
      newEvents.shift();
    }
  }

  return {
    ...prevState,
    events: newEvents,
    streamingEventId: payload.isStreaming ? payload.id : undefined,
  };
};

const updateAgentActions = (prev: AgentAction[], payload: AgentAction) => {
  const newActions = [...prev];
  const existingIndex = newActions.findIndex(
    (action) => action.agentId === payload.agentId
  );

  if (existingIndex >= 0) {
    newActions[existingIndex] = payload;
  } else {
    newActions.push(payload);
    if (newActions.length > 20) {
      newActions.shift();
    }
  }

  return newActions;
};

const useNarrativeDisplayState = (initialShowThoughts: boolean) => {
  const [narrativeState, setNarrativeState] = useState<NarrativeState>(DEFAULT_STATE);
  const [agentActions, setAgentActions] = useState<AgentAction[]>([]);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<NarrativeFilterType>('all');
  const [autoScroll, setAutoScroll] = useState(true);
  const [showThoughts, setShowThoughts] = useState(initialShowThoughts);

  return {
    narrativeState,
    setNarrativeState,
    agentActions,
    setAgentActions,
    selectedEventId,
    setSelectedEventId,
    filterType,
    setFilterType,
    autoScroll,
    setAutoScroll,
    showThoughts,
    setShowThoughts,
  };
};

const NarrativeControls: React.FC<{
  filterType: NarrativeFilterType;
  onFilterChange: (value: NarrativeFilterType) => void;
  autoScroll: boolean;
  onToggleScroll: () => void;
  showThoughts: boolean;
  onToggleThoughts: () => void;
}> = ({
  filterType,
  onFilterChange,
  autoScroll,
  onToggleScroll,
  showThoughts,
  onToggleThoughts,
}) => (
  <div className="narrative-controls">
    <select
      value={filterType}
      onChange={(event) => onFilterChange(event.target.value as NarrativeFilterType)}
      className="narrative-filter"
    >
      <option value="all">All Events</option>
      <option value="action">Actions</option>
      <option value="dialogue">Dialogue</option>
      <option value="description">Descriptions</option>
      <option value="system">System</option>
      {showThoughts && <option value="agent_thought">Agent Thoughts</option>}
    </select>

    <button
      onClick={onToggleScroll}
      className={`control-btn ${autoScroll ? 'active' : ''}`}
    >
      Auto Scroll
    </button>

    <button
      onClick={onToggleThoughts}
      className={`control-btn ${showThoughts ? 'active' : ''}`}
    >
      Show Thoughts
    </button>
  </div>
);

const NarrativeStatus: React.FC<{
  currentTurn: number;
  activeAgentCount: number;
  isGenerating: boolean;
  isConnected: boolean;
}> = ({ currentTurn, activeAgentCount, isGenerating, isConnected }) => (
  <div className="narrative-status">
    <span className="turn-counter">Turn {currentTurn}</span>
    <span className="active-agents">Active: {activeAgentCount}</span>
    {isGenerating && <span className="generating-indicator">Generating...</span>}
    <span className="connection-status">
      {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
    </span>
  </div>
);

const NarrativeHeader: React.FC<{
  filterType: NarrativeFilterType;
  onFilterChange: (value: NarrativeFilterType) => void;
  autoScroll: boolean;
  onToggleScroll: () => void;
  showThoughts: boolean;
  onToggleThoughts: () => void;
  currentTurn: number;
  activeAgentCount: number;
  isGenerating: boolean;
  isConnected: boolean;
}> = ({
  filterType,
  onFilterChange,
  autoScroll,
  onToggleScroll,
  showThoughts,
  onToggleThoughts,
  currentTurn,
  activeAgentCount,
  isGenerating,
  isConnected,
}) => (
  <div className="narrative-display__header">
    <NarrativeControls
      filterType={filterType}
      onFilterChange={onFilterChange}
      autoScroll={autoScroll}
      onToggleScroll={onToggleScroll}
      showThoughts={showThoughts}
      onToggleThoughts={onToggleThoughts}
    />
    <NarrativeStatus
      currentTurn={currentTurn}
      activeAgentCount={activeAgentCount}
      isGenerating={isGenerating}
      isConnected={isConnected}
    />
  </div>
);

const NarrativeEventHeader: React.FC<{ event: NarrativeEvent }> = ({ event }) => (
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
);

const NarrativeEventCausality: React.FC<{ event: NarrativeEvent }> = ({ event }) => (
  <div className="narrative-event__causality">
    {event.causality?.causes?.length ? (
      <div className="causality__section">
        <strong>Causes:</strong>
        <ul>
          {event.causality.causes.map((cause, idx) => (
            <li key={idx}>{cause}</li>
          ))}
        </ul>
      </div>
    ) : null}
    {event.causality?.effects?.length ? (
      <div className="causality__section">
        <strong>Effects:</strong>
        <ul>
          {event.causality.effects.map((effect, idx) => (
            <li key={idx}>{effect}</li>
          ))}
        </ul>
      </div>
    ) : null}
  </div>
);

const NarrativeEventActions: React.FC<{
  eventId: string;
  onAction: (action: string) => void;
}> = ({ eventId, onAction }) => (
  <div className="narrative-event__actions">
    <button
      onClick={(event) => {
        event.stopPropagation();
        onAction('expand');
      }}
      className="event-action-btn"
    >
      Expand
    </button>
    <button
      onClick={(event) => {
        event.stopPropagation();
        onAction('branch');
      }}
      className="event-action-btn"
    >
      Branch Story
    </button>
  </div>
);

const NarrativeEventCard: React.FC<{
  event: NarrativeEvent;
  style?: React.CSSProperties;
  isSelected: boolean;
  enableInteractivity: boolean;
  onClick: () => void;
  onKeyDown: (event: React.KeyboardEvent<HTMLDivElement>) => void;
  onAction: (action: string) => void;
}> = ({
  event,
  style,
  isSelected,
  enableInteractivity,
  onClick,
  onKeyDown,
  onAction,
}) => (
  <div
    style={style}
    className={`narrative-event narrative-event--${event.type.replace(/_/g, '-')} ${
      isSelected ? 'narrative-event--selected' : ''
    } ${event.isStreaming ? 'narrative-event--streaming' : ''}`}
    onClick={onClick}
    onKeyDown={onKeyDown}
    data-event-id={event.id}
    role="button"
    tabIndex={enableInteractivity ? 0 : -1}
  >
    <NarrativeEventHeader event={event} />

    <div className="narrative-event__content">
      {event.content}
      {event.isStreaming && <span className="narrative-event__cursor">|</span>}
    </div>

    {isSelected && event.causality && <NarrativeEventCausality event={event} />}

    {isSelected && enableInteractivity && (
      <NarrativeEventActions eventId={event.id} onAction={onAction} />
    )}
  </div>
);

const NarrativeEventsList: React.FC<{
  events: NarrativeEvent[];
  enableVirtualization: boolean;
  virtualConfig: { overscan: number };
  listRef: React.RefObject<List>;
  enableInteractivity: boolean;
  selectedEventId: string | null;
  onEventClick: (eventId: string) => void;
  onEventKeyDown: (eventId: string, event: React.KeyboardEvent<HTMLDivElement>) => void;
  onEventAction: (eventId: string, action: string) => void;
}> = ({
  events,
  enableVirtualization,
  virtualConfig,
  listRef,
  enableInteractivity,
  selectedEventId,
  onEventClick,
  onEventKeyDown,
  onEventAction,
}) => {
  const renderVirtualRow = useCallback(
    ({ index, style }: { index: number; style: React.CSSProperties }) => {
      const event = events[index];
      if (!event) return null;

      return (
        <NarrativeEventCard
          event={event}
          style={style}
          isSelected={selectedEventId === event.id}
          enableInteractivity={enableInteractivity}
          onClick={() => onEventClick(event.id)}
          onKeyDown={(keyboardEvent) => onEventKeyDown(event.id, keyboardEvent)}
          onAction={(action) => onEventAction(event.id, action)}
        />
      );
    },
    [
      events,
      selectedEventId,
      enableInteractivity,
      onEventClick,
      onEventKeyDown,
      onEventAction,
    ]
  );

  if (enableVirtualization && events.length > 50) {
    return (
      <List
        ref={listRef}
        height={600}
        itemCount={events.length}
        itemSize={80}
        width="100%"
        overscanCount={virtualConfig.overscan}
      >
        {renderVirtualRow}
      </List>
    );
  }

  return (
    <div className="narrative-events-list">
      {events.map((event, index) => (
        <div key={event.id}>{renderVirtualRow({ index, style: {} })}</div>
      ))}
    </div>
  );
};

const AgentActionsPanel: React.FC<{ actions: AgentAction[] }> = ({ actions }) => (
  <div className="agent-actions">
    <h3>Active Agents</h3>
    {actions.map((action) => (
      <div
        key={action.agentId}
        className={`agent-action agent-action--${action.status}`}
      >
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

const useNarrativeAutoScroll = (
  listRef: React.RefObject<List>,
  filteredEvents: NarrativeEvent[],
  autoScroll: boolean,
  lastEventRef: React.MutableRefObject<string>
) => {
  useEffect(() => {
    if (autoScroll && listRef.current && filteredEvents.length > 0) {
      const lastEvent = filteredEvents.at(-1);
      if (!lastEvent) return;
      if (lastEvent.id !== lastEventRef.current) {
        listRef.current.scrollToItem(filteredEvents.length - 1, 'end');
        lastEventRef.current = lastEvent.id;
      }
    }
  }, [filteredEvents, autoScroll, listRef, lastEventRef]);
};

const useNarrativeWebSocket = (params: {
  sessionId: string;
  wsState: ReturnType<typeof useWebSocketContext>['state'];
  sendMessage: ReturnType<typeof useWebSocketContext>['sendMessage'];
  handleWebSocketMessage: (event: Event) => void;
}) => {
  const { sessionId, wsState, sendMessage, handleWebSocketMessage } = params;

  useEffect(() => {
    window.addEventListener(
      'websocket-message',
      handleWebSocketMessage as EventListener
    );

    if (wsState.isConnected) {
      sendMessage({
        type: 'get_narrative_state',
        data: { sessionId },
        priority: 'normal',
      });
    }

    return () => {
      window.removeEventListener(
        'websocket-message',
        handleWebSocketMessage as EventListener
      );
    };
  }, [handleWebSocketMessage, wsState.isConnected, sendMessage, sessionId]);
};

const createNarrativeEventHandlers = (params: {
  enableInteractivity: boolean;
  measureInteractionDelay: ReturnType<
    typeof usePerformanceOptimizer
  >['measureInteractionDelay'];
  setSelectedEventId: React.Dispatch<React.SetStateAction<string | null>>;
  wsState: ReturnType<typeof useWebSocketContext>['state'];
  sendMessage: ReturnType<typeof useWebSocketContext>['sendMessage'];
  sessionId: string;
}) => {
  const handleEventClick = (eventId: string) => {
    if (!params.enableInteractivity) return;

    params.measureInteractionDelay(() => {
      params.setSelectedEventId((prev) => (prev === eventId ? null : eventId));
    });
  };

  const handleEventAction = (eventId: string, action: string) => {
    if (!params.wsState.isConnected) return;

    params.sendMessage({
      type: 'narrative_action',
      data: {
        sessionId: params.sessionId,
        eventId,
        action,
      },
      priority: 'normal',
    });
  };

  const handleEventKeyDown = (
    eventId: string,
    keyboardEvent: React.KeyboardEvent<HTMLDivElement>
  ) => {
    if (!params.enableInteractivity) return;
    if (keyboardEvent.key === 'Enter' || keyboardEvent.key === ' ') {
      keyboardEvent.preventDefault();
      handleEventClick(eventId);
    }
  };

  return { handleEventClick, handleEventAction, handleEventKeyDown };
};

const useNarrativeVirtualConfig = (
  scrollContainerRef: React.RefObject<HTMLDivElement>,
  eventsCount: number,
  createVirtualScrollConfig: ReturnType<
    typeof usePerformanceOptimizer
  >['createVirtualScrollConfig']
) => {
  return useMemo(() => {
    const containerHeight = scrollContainerRef.current?.clientHeight || 600;
    return createVirtualScrollConfig(eventsCount, 80, containerHeight);
  }, [eventsCount, createVirtualScrollConfig, scrollContainerRef]);
};

const useNarrativeFilteredEvents = (
  events: NarrativeEvent[],
  filterType: NarrativeFilterType,
  showThoughts: boolean
) => {
  return useMemo(
    () => events.filter((event) => shouldIncludeEvent(event, filterType, showThoughts)),
    [events, filterType, showThoughts]
  );
};

const useNarrativeRealtimeSync = (params: {
  sessionId: string;
  wsState: ReturnType<typeof useWebSocketContext>['state'];
  sendMessage: ReturnType<typeof useWebSocketContext>['sendMessage'];
  deferUpdate: ReturnType<typeof usePerformanceOptimizer>['deferUpdate'];
  setNarrativeState: React.Dispatch<React.SetStateAction<NarrativeState>>;
  setAgentActions: React.Dispatch<React.SetStateAction<AgentAction[]>>;
  maxEvents: number;
  listRef: React.RefObject<List>;
  filteredEvents: NarrativeEvent[];
  autoScroll: boolean;
  lastEventRef: React.MutableRefObject<string>;
  optimizeForRealTime: ReturnType<
    typeof usePerformanceOptimizer
  >['optimizeForRealTime'];
}) => {
  const {
    sessionId,
    wsState,
    sendMessage,
    deferUpdate,
    setNarrativeState,
    setAgentActions,
    maxEvents,
    listRef,
    filteredEvents,
    autoScroll,
    lastEventRef,
    optimizeForRealTime,
  } = params;

  const handleWebSocketMessage = useCallback(
    (event: Event) => {
      const message = (event as CustomEvent).detail;

      switch (message.type) {
        case 'narrative_event':
          deferUpdate(() => {
            setNarrativeState((prev) =>
              updateEventsForMessage(prev, message.data, maxEvents)
            );
          });
          break;
        case 'agent_action':
          setAgentActions((prev) => updateAgentActions(prev, message.data));
          break;
        case 'narrative_state':
          setNarrativeState((prev) => ({
            ...prev,
            activeAgents: message.data.activeAgents || [],
            currentTurn: message.data.currentTurn || prev.currentTurn,
            isGenerating: message.data.isGenerating || false,
          }));
          break;
        default:
          break;
      }
    },
    [deferUpdate, maxEvents, setNarrativeState, setAgentActions]
  );

  useNarrativeAutoScroll(listRef, filteredEvents, autoScroll, lastEventRef);
  useNarrativeWebSocket({ sessionId, wsState, sendMessage, handleWebSocketMessage });

  useEffect(() => {
    optimizeForRealTime();
  }, [optimizeForRealTime]);
};

const useNarrativeDisplayController = (params: {
  sessionId: string;
  maxEvents: number;
  showAgentThoughts: boolean;
  enableInteractivity: boolean;
}) => {
  const { sessionId, maxEvents, showAgentThoughts, enableInteractivity } = params;
  const { state: wsState, sendMessage } = useWebSocketContext();
  const {
    optimizeForRealTime,
    createVirtualScrollConfig,
    deferUpdate,
    measureInteractionDelay,
  } = usePerformanceOptimizer();

  const { listRef, scrollContainerRef, lastEventRef } = useNarrativeRefs();

  const {
    narrativeState,
    setNarrativeState,
    agentActions,
    setAgentActions,
    selectedEventId,
    setSelectedEventId,
    filterType,
    setFilterType,
    autoScroll,
    setAutoScroll,
    showThoughts,
    setShowThoughts,
  } = useNarrativeDisplayState(showAgentThoughts);

  const { virtualConfig, filteredEvents } = useNarrativeDerivedState({
    scrollContainerRef,
    createVirtualScrollConfig,
    events: narrativeState.events,
    filterType,
    showThoughts,
  });

  useNarrativeRealtimeSync({
    sessionId,
    wsState,
    sendMessage,
    deferUpdate,
    setNarrativeState,
    setAgentActions,
    maxEvents,
    listRef,
    filteredEvents,
    autoScroll,
    lastEventRef,
    optimizeForRealTime,
  });

  const { handleEventClick, handleEventAction, handleEventKeyDown } =
    createNarrativeEventHandlers({
      enableInteractivity,
      measureInteractionDelay,
      setSelectedEventId,
      wsState,
      sendMessage,
      sessionId,
    });

  return {
    wsState,
    listRef,
    scrollContainerRef,
    narrativeState,
    agentActions,
    filterType,
    setFilterType,
    autoScroll,
    setAutoScroll,
    showThoughts,
    setShowThoughts,
    filteredEvents,
    virtualConfig,
    selectedEventId,
    handleEventClick,
    handleEventAction,
    handleEventKeyDown,
  };
};

const useNarrativeRefs = () => {
  const listRef = useRef<List>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const lastEventRef = useRef<string>('');
  return { listRef, scrollContainerRef, lastEventRef };
};

const useNarrativeDerivedState = (params: {
  scrollContainerRef: React.RefObject<HTMLDivElement>;
  createVirtualScrollConfig: ReturnType<
    typeof usePerformanceOptimizer
  >['createVirtualScrollConfig'];
  events: NarrativeEvent[];
  filterType: NarrativeFilterType;
  showThoughts: boolean;
}) => {
  const {
    scrollContainerRef,
    createVirtualScrollConfig,
    events,
    filterType,
    showThoughts,
  } = params;
  const virtualConfig = useNarrativeVirtualConfig(
    scrollContainerRef,
    events.length,
    createVirtualScrollConfig
  );
  const filteredEvents = useNarrativeFilteredEvents(events, filterType, showThoughts);
  return { virtualConfig, filteredEvents };
};

const NarrativeDisplay: React.FC<NarrativeDisplayProps> = ({
  sessionId,
  maxEvents = 1000,
  enableVirtualization = true,
  showAgentThoughts = false,
  enableInteractivity = true,
  className = '',
}) => {
  const {
    wsState,
    listRef,
    scrollContainerRef,
    narrativeState,
    agentActions,
    filterType,
    setFilterType,
    autoScroll,
    setAutoScroll,
    showThoughts,
    setShowThoughts,
    filteredEvents,
    virtualConfig,
    selectedEventId,
    handleEventClick,
    handleEventAction,
    handleEventKeyDown,
  } = useNarrativeDisplayController({
    sessionId,
    maxEvents,
    showAgentThoughts,
    enableInteractivity,
  });

  return (
    <div className={`narrative-display ${className}`}>
      <NarrativeHeader
        filterType={filterType}
        onFilterChange={setFilterType}
        autoScroll={autoScroll}
        onToggleScroll={() => setAutoScroll((prev) => !prev)}
        showThoughts={showThoughts}
        onToggleThoughts={() => setShowThoughts((prev) => !prev)}
        currentTurn={narrativeState.currentTurn}
        activeAgentCount={narrativeState.activeAgents.length}
        isGenerating={narrativeState.isGenerating}
        isConnected={wsState.isConnected}
      />

      <div className="narrative-display__content">
        <div className="narrative-events" ref={scrollContainerRef}>
          <NarrativeEventsList
            events={filteredEvents}
            enableVirtualization={enableVirtualization}
            virtualConfig={virtualConfig}
            listRef={listRef}
            enableInteractivity={enableInteractivity}
            selectedEventId={selectedEventId}
            onEventClick={handleEventClick}
            onEventKeyDown={handleEventKeyDown}
            onEventAction={handleEventAction}
          />

          {filteredEvents.length === 0 && (
            <div className="empty-narrative">
              <p>No narrative events yet. Start a new story to see content here.</p>
            </div>
          )}
        </div>

        {agentActions.length > 0 && <AgentActionsPanel actions={agentActions} />}
      </div>
    </div>
  );
};

export default React.memo(NarrativeDisplay);
