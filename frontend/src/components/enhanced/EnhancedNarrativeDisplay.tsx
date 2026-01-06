/**
 * Enhanced Narrative Display with Magic UI
 * =======================================
 * 
 * Advanced narrative display component using Magic UI components:
 * - Modern card-based event layout
 * - Interactive story elements
 * - Performance optimized rendering
 * - Advanced filtering and search
 * - Real-time animations
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { FixedSizeList as List } from 'react-window';
import { useWebSocketContext } from '../../hooks/useWebSocket';
import { usePerformanceOptimizer } from '../../hooks/usePerformanceOptimizer';
import { Button } from '../ui/Button';
import { Card, CardHeader, CardContent, StatCard } from '../ui/Card';
import { Badge, StatusBadge } from '../ui/Badge';
import { cn, formatRelativeTime, generateId, PerformanceMonitor } from '../../lib/utils';
import './EnhancedNarrativeDisplay.css';

// Enhanced narrative event interface
interface EnhancedNarrativeEvent {
  id: string;
  type: 'action' | 'dialogue' | 'description' | 'system' | 'agent_thought' | 'user_input' | 'world_event';
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
  
  // Enhanced properties
  priority: 'low' | 'normal' | 'high' | 'critical';
  emotion?: 'neutral' | 'happy' | 'sad' | 'angry' | 'surprised' | 'fearful';
  tags: string[];
  reactions: { [userId: string]: 'like' | 'dislike' | 'love' | 'laugh' | 'wow' };
  reactionCount: number;
  editHistory?: { timestamp: number; content: string; editor: string }[];
  attachments?: { type: string; url: string; name: string }[];
  characters: string[];
  location?: string;
  timeOfDay?: string;
  sentiment: number; // -1 to 1
}

interface EnhancedNarrativeDisplayProps {
  sessionId: string;
  maxEvents?: number;
  enableVirtualization?: boolean;
  showAgentThoughts?: boolean;
  enableInteractivity?: boolean;
  className?: string;
  compact?: boolean;
}

const EVENT_TYPE_ICONS: Record<EnhancedNarrativeEvent['type'], string> = {
  action: '⚡',
  dialogue: '💬',
  description: '📝',
  system: '⚙️',
  agent_thought: '💭',
  user_input: '👤',
  world_event: '🌍',
};

const EMOTION_COLORS: Record<NonNullable<EnhancedNarrativeEvent['emotion']>, string> = {
  happy: 'text-green-600',
  sad: 'text-blue-600',
  angry: 'text-red-600',
  surprised: 'text-yellow-600',
  fearful: 'text-purple-600',
  neutral: 'text-gray-600',
};

const PRIORITY_ORDER: Record<EnhancedNarrativeEvent['priority'], number> = {
  critical: 0,
  high: 1,
  normal: 2,
  low: 3,
};

const REACTION_EMOJIS = ['👍', '❤️', '😂', '😮', '😢'] as const;

const getEventTypeIcon = (type: EnhancedNarrativeEvent['type']) => EVENT_TYPE_ICONS[type] ?? '📄';

const getEmotionColor = (emotion?: EnhancedNarrativeEvent['emotion']) =>
  EMOTION_COLORS[emotion || 'neutral'] ?? 'text-gray-600';

const normalizeNarrativeEvent = (
  data: Partial<EnhancedNarrativeEvent> & { content?: string }
): EnhancedNarrativeEvent => ({
  id: data.id || generateId('event'),
  type: data.type || 'description',
  content: data.content || '',
  timestamp: data.timestamp || Date.now(),
  agentId: data.agentId,
  agentName: data.agentName,
  metadata: data.metadata,
  isStreaming: data.isStreaming,
  confidence: data.confidence,
  causality: data.causality,
  priority: data.priority || 'normal',
  emotion: data.emotion,
  tags: data.tags || [],
  reactions: data.reactions || {},
  reactionCount: Object.keys(data.reactions || {}).length,
  editHistory: data.editHistory,
  attachments: data.attachments,
  characters: data.characters || [],
  location: data.location,
  timeOfDay: data.timeOfDay,
  sentiment: data.sentiment || 0,
});

const updateNarrativeEvents = (
  prevEvents: EnhancedNarrativeEvent[],
  message: { data: Partial<EnhancedNarrativeEvent> & { id?: string; isStreaming?: boolean } },
  maxEvents: number
) => {
  const newEvents = [...prevEvents];

  if (message.data.isStreaming && message.data.id) {
    const eventIndex = newEvents.findIndex((event) => event.id === message.data.id);
    if (eventIndex >= 0) {
      newEvents[eventIndex] = normalizeNarrativeEvent({
        ...newEvents[eventIndex],
        ...message.data,
      });
    }
    return newEvents;
  }

  newEvents.unshift(normalizeNarrativeEvent(message.data));
  if (newEvents.length > maxEvents) {
    newEvents.splice(maxEvents);
  }
  return newEvents;
};

const filterNarrativeEvents = (
  events: EnhancedNarrativeEvent[],
  params: {
    searchQuery: string;
    filterType: string;
    filterEmotion: string;
    showAgentThoughts: boolean;
    sortBy: 'timestamp' | 'priority' | 'reactions';
  }
) => {
  let filtered = events;
  const { searchQuery, filterType, filterEmotion, showAgentThoughts, sortBy } = params;

  if (searchQuery) {
    const query = searchQuery.toLowerCase();
    filtered = filtered.filter(
      (event) =>
        event.content.toLowerCase().includes(query) ||
        event.agentName?.toLowerCase().includes(query) ||
        event.tags.some((tag) => tag.toLowerCase().includes(query)) ||
        event.characters.some((char) => char.toLowerCase().includes(query))
    );
  }

  if (filterType !== 'all') {
    filtered = filtered.filter((event) => event.type === filterType);
  }

  if (filterEmotion !== 'all') {
    filtered = filtered.filter((event) => event.emotion === filterEmotion);
  }

  if (!showAgentThoughts) {
    filtered = filtered.filter((event) => event.type !== 'agent_thought');
  }

  const sorted = [...filtered];
  sorted.sort((a, b) => {
    switch (sortBy) {
      case 'priority':
        return PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority];
      case 'reactions':
        return b.reactionCount - a.reactionCount;
      case 'timestamp':
      default:
        return b.timestamp - a.timestamp;
    }
  });

  return sorted;
};

const NarrativeHeader: React.FC<{
  metrics: { totalEvents: number; streamingEvents: number; avgConfidence: number; recentActivity: number };
  isConnected: boolean;
}> = ({ metrics, isConnected }) => (
  <div className="mb-4 space-y-4">
    <div className="flex items-center justify-between">
      <h2 className="text-xl font-bold">Narrative Feed</h2>
      <StatusBadge status={isConnected ? 'online' : 'offline'} />
    </div>

    <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
      <StatCard title="Total Events" value={metrics.totalEvents} color="info" icon={<span className="text-lg">📝</span>} />
      <StatCard title="Streaming" value={metrics.streamingEvents} color="success" icon={<span className="text-lg">⚡</span>} />
      <StatCard
        title="Avg Confidence"
        value={`${Math.round(metrics.avgConfidence * 100)}%`}
        color="warning"
        icon={<span className="text-lg">🎯</span>}
      />
      <StatCard title="Recent Activity" value={metrics.recentActivity} color="default" icon={<span className="text-lg">📊</span>} />
    </div>
  </div>
);

const NarrativeControls: React.FC<{
  searchQuery: string;
  filterType: string;
  sortBy: 'timestamp' | 'priority' | 'reactions';
  autoScroll: boolean;
  showAgentThoughts: boolean;
  onSearchChange: (value: string) => void;
  onFilterTypeChange: (value: string) => void;
  onSortChange: (value: 'timestamp' | 'priority' | 'reactions') => void;
  onAutoScrollToggle: () => void;
  onAgentThoughtsToggle: () => void;
}> = ({
  searchQuery,
  filterType,
  sortBy,
  autoScroll,
  showAgentThoughts,
  onSearchChange,
  onFilterTypeChange,
  onSortChange,
  onAutoScrollToggle,
  onAgentThoughtsToggle,
}) => (
  <div className="flex flex-wrap items-center gap-3">
    <input
      type="text"
      placeholder="Search events..."
      value={searchQuery}
      onChange={(event) => onSearchChange(event.target.value)}
      className="px-3 py-2 bg-background border border-border rounded-md text-sm min-w-[200px]"
    />

    <select
      value={filterType}
      onChange={(event) => onFilterTypeChange(event.target.value)}
      className="px-3 py-2 bg-background border border-border rounded-md text-sm"
    >
      <option value="all">All Types</option>
      <option value="action">Actions</option>
      <option value="dialogue">Dialogue</option>
      <option value="description">Descriptions</option>
      <option value="system">System</option>
      <option value="user_input">User Input</option>
      <option value="world_event">World Events</option>
    </select>

    <select
      value={sortBy}
      onChange={(event) => onSortChange(event.target.value as 'timestamp' | 'priority' | 'reactions')}
      className="px-3 py-2 bg-background border border-border rounded-md text-sm"
    >
      <option value="timestamp">Latest</option>
      <option value="priority">Priority</option>
      <option value="reactions">Most Reactions</option>
    </select>

    <Button variant={autoScroll ? 'default' : 'outline'} size="sm" onClick={onAutoScrollToggle}>
      Auto Scroll
    </Button>

    <Button variant={showAgentThoughts ? 'default' : 'outline'} size="sm" onClick={onAgentThoughtsToggle}>
      Show Thoughts
    </Button>
  </div>
);

const NarrativeEmptyState: React.FC<{ hasFilters: boolean }> = ({ hasFilters }) => (
  <Card className="p-8 text-center">
    <div className="text-muted-foreground">
      <span className="text-4xl block mb-4">📝</span>
      <p>No narrative events found.</p>
      <p className="text-sm mt-2">
        {hasFilters ? 'Try adjusting your search or filters.' : 'Start a narrative session to see events here.'}
      </p>
    </div>
  </Card>
);

const NarrativeEventHeader: React.FC<{
  event: EnhancedNarrativeEvent;
}> = ({ event }) => (
  <CardHeader className="pb-2">
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className="text-lg">{getEventTypeIcon(event.type)}</span>
        <div className="flex items-center gap-2">
          {event.agentName && (
            <Badge variant="outline" size="sm">
              {event.agentName}
            </Badge>
          )}
          <Badge variant="ghost" size="sm" className={cn('capitalize', getEmotionColor(event.emotion))}>
            {event.emotion || 'neutral'}
          </Badge>
          <Badge variant="secondary" size="sm">
            {event.type}
          </Badge>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {event.confidence && (
          <Badge
            variant="ghost"
            size="sm"
            className={
              event.confidence > 0.8 ? 'text-green-600' : event.confidence > 0.5 ? 'text-yellow-600' : 'text-red-600'
            }
          >
            {Math.round(event.confidence * 100)}%
          </Badge>
        )}
        <span className="text-xs text-muted-foreground">{formatRelativeTime(event.timestamp)}</span>
      </div>
    </div>
  </CardHeader>
);

const NarrativeEventMeta: React.FC<{ event: EnhancedNarrativeEvent; isStreaming: boolean }> = ({ event, isStreaming }) => (
  <div className="prose prose-sm max-w-none">
    <p className={cn('text-sm leading-relaxed', isStreaming && 'typing-effect')}>
      {event.content}
      {isStreaming && <span className="animate-pulse">|</span>}
    </p>
  </div>
);

const NarrativeEventLocation: React.FC<{ event: EnhancedNarrativeEvent }> = ({ event }) => {
  if (!event.location) return null;
  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      <span>📍</span>
      <span>{event.location}</span>
      {event.timeOfDay && (
        <>
          <span>•</span>
          <span>{event.timeOfDay}</span>
        </>
      )}
    </div>
  );
};

const NarrativeEventCharacters: React.FC<{ characters: string[] }> = ({ characters }) => {
  if (characters.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1">
      {characters.map((character) => (
        <Badge key={character} variant="secondary" size="sm">
          👤 {character}
        </Badge>
      ))}
    </div>
  );
};

const NarrativeEventTags: React.FC<{ tags: string[] }> = ({ tags }) => {
  if (tags.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1">
      {tags.map((tag) => (
        <Badge key={tag} variant="outline" size="sm">
          #{tag}
        </Badge>
      ))}
    </div>
  );
};

const NarrativeEventReactions: React.FC<{
  event: EnhancedNarrativeEvent;
  onReaction: (eventId: string, reaction: string) => void;
  onEventAction: (eventId: string, action: string) => void;
}> = ({ event, onReaction, onEventAction }) => (
  <div className="flex items-center justify-between pt-2">
    <div className="flex items-center gap-1">
      {REACTION_EMOJIS.map((emoji) => (
        <Button
          key={emoji}
          variant="ghost"
          size="sm"
          className="h-6 w-6 p-0 hover:scale-110"
          onClick={(eventClick) => {
            eventClick.stopPropagation();
            onReaction(event.id, emoji);
          }}
        >
          {emoji}
        </Button>
      ))}
      {event.reactionCount > 0 && (
        <span className="text-xs text-muted-foreground ml-2">{event.reactionCount}</span>
      )}
    </div>

    <div className="flex items-center gap-1">
      <Button
        variant="ghost"
        size="sm"
        onClick={(eventClick) => {
          eventClick.stopPropagation();
          onEventAction(event.id, 'expand');
        }}
      >
        🔍
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={(eventClick) => {
          eventClick.stopPropagation();
          onEventAction(event.id, 'branch');
        }}
      >
        🌿
      </Button>
    </div>
  </div>
);

const NarrativeEventCausality: React.FC<{ causality: NonNullable<EnhancedNarrativeEvent['causality']> }> = ({
  causality,
}) => (
  <Card variant="ghost" className="mt-3 p-3">
    <div className="space-y-2">
      {causality.causes.length > 0 && (
        <div>
          <h5 className="text-xs font-semibold text-muted-foreground">Causes:</h5>
          <ul className="text-xs space-y-1 mt-1">
            {causality.causes.map((cause, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-muted-foreground">←</span>
                <span>{cause}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {causality.effects.length > 0 && (
        <div>
          <h5 className="text-xs font-semibold text-muted-foreground">Effects:</h5>
          <ul className="text-xs space-y-1 mt-1">
            {causality.effects.map((effect, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-muted-foreground">→</span>
                <span>{effect}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  </Card>
);

const NarrativeEventCard: React.FC<{
  event: EnhancedNarrativeEvent;
  isSelected: boolean;
  enableInteractivity: boolean;
  onEventClick: (eventId: string) => void;
  onReaction: (eventId: string, reaction: string) => void;
  onEventAction: (eventId: string, action: string) => void;
}> = ({ event, isSelected, enableInteractivity, onEventClick, onReaction, onEventAction }) => (
  <Card
    variant={isSelected ? 'interactive' : 'elevated'}
    className={cn(
      'cursor-pointer transition-all duration-200 narrative-event-card',
      isSelected && 'ring-2 ring-primary',
      event.isStreaming && 'animate-pulse',
      event.priority === 'critical' && 'ring-1 ring-red-500',
      event.priority === 'high' && 'border-yellow-500'
    )}
    onClick={() => onEventClick(event.id)}
    glow={event.priority === 'critical'}
  >
    <NarrativeEventHeader event={event} />
    <CardContent>
      <div className="space-y-3">
        <NarrativeEventMeta event={event} isStreaming={!!event.isStreaming} />
        <NarrativeEventLocation event={event} />
        <NarrativeEventCharacters characters={event.characters} />
        <NarrativeEventTags tags={event.tags} />
        {enableInteractivity && (
          <NarrativeEventReactions event={event} onReaction={onReaction} onEventAction={onEventAction} />
        )}
        {isSelected && event.causality && <NarrativeEventCausality causality={event.causality} />}
      </div>
    </CardContent>
  </Card>
);

const NarrativeEventRow: React.FC<{
  event: EnhancedNarrativeEvent;
  style: React.CSSProperties;
  isSelected: boolean;
  enableInteractivity: boolean;
  onEventClick: (eventId: string) => void;
  onReaction: (eventId: string, reaction: string) => void;
  onEventAction: (eventId: string, action: string) => void;
}> = ({ event, style, isSelected, enableInteractivity, onEventClick, onReaction, onEventAction }) => (
  <div style={style} className="px-2 py-1">
    <NarrativeEventCard
      event={event}
      isSelected={isSelected}
      enableInteractivity={enableInteractivity}
      onEventClick={onEventClick}
      onReaction={onReaction}
      onEventAction={onEventAction}
    />
  </div>
);

const useFilteredEvents = (
  events: EnhancedNarrativeEvent[],
  searchQuery: string,
  filterType: string,
  filterEmotion: string,
  showAgentThoughts: boolean,
  sortBy: 'timestamp' | 'priority' | 'reactions'
) =>
  useMemo(() => {
    PerformanceMonitor.start('event-filtering');
    const filtered = filterNarrativeEvents(events, {
      searchQuery,
      filterType,
      filterEmotion,
      showAgentThoughts,
      sortBy,
    });
    PerformanceMonitor.end('event-filtering');
    return filtered;
  }, [events, searchQuery, filterType, filterEmotion, showAgentThoughts, sortBy]);

const useNarrativeWebSocket = (params: {
  sessionId: string;
  wsState: { isConnected: boolean };
  sendMessage: (payload: { type: string; data: Record<string, unknown>; priority: 'normal' }) => void;
  deferUpdate: (callback: () => void) => void;
  maxEvents: number;
  setEvents: React.Dispatch<React.SetStateAction<EnhancedNarrativeEvent[]>>;
  setMetrics: React.Dispatch<
    React.SetStateAction<{ totalEvents: number; streamingEvents: number; avgConfidence: number; recentActivity: number }>
  >;
}) => {
  const { sessionId, wsState, sendMessage, deferUpdate, maxEvents, setEvents, setMetrics } = params;

  const handleWebSocketMessage = useCallback(
    (event: CustomEvent) => {
      const message = event.detail;

      switch (message.type) {
        case 'narrative_event':
          deferUpdate(() => {
            setEvents((prev) => updateNarrativeEvents(prev, message, maxEvents));
          });
          break;

        case 'narrative_metrics':
          setMetrics({
            totalEvents: message.data.totalEvents || 0,
            streamingEvents: message.data.streamingEvents || 0,
            avgConfidence: message.data.avgConfidence || 0,
            recentActivity: message.data.recentActivity || 0,
          });
          break;
      }
    },
    [deferUpdate, maxEvents, setEvents, setMetrics]
  );

  useEffect(() => {
    window.addEventListener('websocket-message', handleWebSocketMessage as EventListener);

    if (wsState.isConnected) {
      sendMessage({
        type: 'get_narrative_state',
        data: { sessionId },
        priority: 'normal',
      });
    }

    return () => {
      window.removeEventListener('websocket-message', handleWebSocketMessage as EventListener);
    };
  }, [handleWebSocketMessage, sendMessage, sessionId, wsState.isConnected]);
};

const useNarrativeEventHandlers = (params: {
  enableInteractivity: boolean;
  measureInteractionDelay: (callback: () => void) => void;
  wsState: { isConnected: boolean };
  sendMessage: (payload: { type: string; data: Record<string, unknown>; priority: 'normal' }) => void;
  sessionId: string;
  setSelectedEventId: React.Dispatch<React.SetStateAction<string | null>>;
}) => {
  const { enableInteractivity, measureInteractionDelay, wsState, sendMessage, sessionId, setSelectedEventId } = params;

  const handleEventClick = useCallback(
    (eventId: string) => {
      if (!enableInteractivity) return;
      measureInteractionDelay(() => {
        setSelectedEventId((prev) => (prev === eventId ? null : eventId));
      });
    },
    [enableInteractivity, measureInteractionDelay, setSelectedEventId]
  );

  const handleReaction = useCallback(
    (eventId: string, reaction: string) => {
      if (!wsState.isConnected) return;

      sendMessage({
        type: 'narrative_reaction',
        data: {
          sessionId,
          eventId,
          reaction,
          userId: 'current_user',
        },
        priority: 'normal',
      });
    },
    [sendMessage, sessionId, wsState.isConnected]
  );

  const handleEventAction = useCallback(
    (eventId: string, action: string) => {
      if (!wsState.isConnected) return;

      sendMessage({
        type: 'narrative_action',
        data: {
          sessionId,
          eventId,
          action,
        },
        priority: 'normal',
      });
    },
    [sendMessage, sessionId, wsState.isConnected]
  );

  return { handleEventClick, handleReaction, handleEventAction };
};

const NarrativeEventList: React.FC<{
  filteredEvents: EnhancedNarrativeEvent[];
  enableVirtualization: boolean;
  compact: boolean;
  listRef: React.RefObject<List>;
  virtualConfig: { overscan: number };
  renderEvent: (props: { index: number; style: React.CSSProperties }) => React.ReactNode;
  scrollContainerRef: React.RefObject<HTMLDivElement>;
  hasFilters: boolean;
}> = ({
  filteredEvents,
  enableVirtualization,
  compact,
  listRef,
  virtualConfig,
  renderEvent,
  scrollContainerRef,
  hasFilters,
}) => (
  <div className="flex-1 overflow-hidden" ref={scrollContainerRef}>
    {enableVirtualization && filteredEvents.length > 20 ? (
      <List
        ref={listRef}
        height={600}
        itemCount={filteredEvents.length}
        itemSize={compact ? 80 : 160}
        width="100%"
        overscanCount={virtualConfig.overscan}
      >
        {renderEvent}
      </List>
    ) : (
      <div className="space-y-2 max-h-[600px] overflow-y-auto">
        {filteredEvents.map((event, index) => (
          <div key={event.id}>{renderEvent({ index, style: {} })}</div>
        ))}
      </div>
    )}

    {filteredEvents.length === 0 && <NarrativeEmptyState hasFilters={hasFilters} />}
  </div>
);

const NarrativeDisplayBody: React.FC<{
  metrics: { totalEvents: number; streamingEvents: number; avgConfidence: number; recentActivity: number };
  isConnected: boolean;
  searchQuery: string;
  filterType: string;
  sortBy: 'timestamp' | 'priority' | 'reactions';
  autoScroll: boolean;
  showThoughts: boolean;
  onSearchChange: (value: string) => void;
  onFilterTypeChange: (value: string) => void;
  onSortChange: (value: 'timestamp' | 'priority' | 'reactions') => void;
  onAutoScrollToggle: () => void;
  onAgentThoughtsToggle: () => void;
  filteredEvents: EnhancedNarrativeEvent[];
  enableVirtualization: boolean;
  compact: boolean;
  listRef: React.RefObject<List>;
  virtualConfig: { overscan: number };
  renderEvent: (props: { index: number; style: React.CSSProperties }) => React.ReactNode;
  scrollContainerRef: React.RefObject<HTMLDivElement>;
  hasFilters: boolean;
}> = ({
  metrics,
  isConnected,
  searchQuery,
  filterType,
  sortBy,
  autoScroll,
  showThoughts,
  onSearchChange,
  onFilterTypeChange,
  onSortChange,
  onAutoScrollToggle,
  onAgentThoughtsToggle,
  filteredEvents,
  enableVirtualization,
  compact,
  listRef,
  virtualConfig,
  renderEvent,
  scrollContainerRef,
  hasFilters,
}) => (
  <>
    <NarrativeHeader metrics={metrics} isConnected={isConnected} />
    <NarrativeControls
      searchQuery={searchQuery}
      filterType={filterType}
      sortBy={sortBy}
      autoScroll={autoScroll}
      showAgentThoughts={showThoughts}
      onSearchChange={onSearchChange}
      onFilterTypeChange={onFilterTypeChange}
      onSortChange={onSortChange}
      onAutoScrollToggle={onAutoScrollToggle}
      onAgentThoughtsToggle={onAgentThoughtsToggle}
    />
    <NarrativeEventList
      filteredEvents={filteredEvents}
      enableVirtualization={enableVirtualization}
      compact={compact}
      listRef={listRef}
      virtualConfig={virtualConfig}
      renderEvent={renderEvent}
      scrollContainerRef={scrollContainerRef}
      hasFilters={hasFilters}
    />
  </>
);

const useNarrativeStateValues = (showAgentThoughts: boolean) => {
  const listRef = useRef<List>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [events, setEvents] = useState<EnhancedNarrativeEvent[]>([]);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [filterEmotion, _setFilterEmotion] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'timestamp' | 'priority' | 'reactions'>('timestamp');
  const [autoScroll, setAutoScroll] = useState(true);
  const [showThoughts, setShowThoughts] = useState(showAgentThoughts);
  const [_viewMode, _setViewMode] = useState<'feed' | 'timeline' | 'compact'>('feed');
  const [metrics, setMetrics] = useState({
    totalEvents: 0,
    streamingEvents: 0,
    avgConfidence: 0,
    recentActivity: 0,
  });

  return {
    listRef,
    scrollContainerRef,
    events,
    setEvents,
    selectedEventId,
    setSelectedEventId,
    searchQuery,
    setSearchQuery,
    filterType,
    setFilterType,
    filterEmotion,
    sortBy,
    setSortBy,
    autoScroll,
    setAutoScroll,
    showThoughts,
    setShowThoughts,
    metrics,
    setMetrics,
  };
};

const useNarrativeDerivedState = (params: {
  events: EnhancedNarrativeEvent[];
  searchQuery: string;
  filterType: string;
  filterEmotion: string;
  showThoughts: boolean;
  sortBy: 'timestamp' | 'priority' | 'reactions';
  compact: boolean;
  createVirtualScrollConfig: (itemCount: number, itemHeight: number, containerHeight: number) => {
    overscan: number;
  };
  scrollContainerRef: React.RefObject<HTMLDivElement>;
}) => {
  const { events, searchQuery, filterType, filterEmotion, showThoughts, sortBy, compact, createVirtualScrollConfig, scrollContainerRef } =
    params;

  const virtualConfig = useMemo(() => {
    const containerHeight = scrollContainerRef.current?.clientHeight || 600;
    return createVirtualScrollConfig(events.length, compact ? 60 : 120, containerHeight);
  }, [events.length, createVirtualScrollConfig, compact, scrollContainerRef]);

  const filteredEvents = useFilteredEvents(events, searchQuery, filterType, filterEmotion, showThoughts, sortBy);

  return { filteredEvents, virtualConfig };
};

const useNarrativeRuntime = (params: {
  sessionId: string;
  maxEvents: number;
  wsState: { isConnected: boolean };
  sendMessage: (payload: { type: string; data: Record<string, unknown>; priority: 'normal' }) => void;
  deferUpdate: (callback: () => void) => void;
  setEvents: React.Dispatch<React.SetStateAction<EnhancedNarrativeEvent[]>>;
  setMetrics: React.Dispatch<
    React.SetStateAction<{ totalEvents: number; streamingEvents: number; avgConfidence: number; recentActivity: number }>
  >;
  optimizeForRealTime: () => void;
  autoScroll: boolean;
  filteredEvents: EnhancedNarrativeEvent[];
  listRef: React.RefObject<List>;
}) => {
  const {
    sessionId,
    maxEvents,
    wsState,
    sendMessage,
    deferUpdate,
    setEvents,
    setMetrics,
    optimizeForRealTime,
    autoScroll,
    filteredEvents,
    listRef,
  } = params;

  useNarrativeWebSocket({
    sessionId,
    wsState,
    sendMessage,
    deferUpdate,
    maxEvents,
    setEvents,
    setMetrics,
  });

  useEffect(() => {
    if (autoScroll && listRef.current && filteredEvents.length > 0) {
      listRef.current.scrollToItem(0, 'start');
    }
  }, [filteredEvents, autoScroll, listRef]);

  useEffect(() => {
    optimizeForRealTime();
  }, [optimizeForRealTime]);
};

const useNarrativeEventRenderer = (params: {
  filteredEvents: EnhancedNarrativeEvent[];
  selectedEventId: string | null;
  enableInteractivity: boolean;
  handleEventClick: (eventId: string) => void;
  handleReaction: (eventId: string, reaction: string) => void;
  handleEventAction: (eventId: string, action: string) => void;
}) =>
  useCallback(
    ({ index, style }: { index: number; style: React.CSSProperties }) => {
      const event = params.filteredEvents[index];
      if (!event) return null;
      return (
        <NarrativeEventRow
          event={event}
          style={style}
          isSelected={params.selectedEventId === event.id}
          enableInteractivity={params.enableInteractivity}
          onEventClick={params.handleEventClick}
          onReaction={params.handleReaction}
          onEventAction={params.handleEventAction}
        />
      );
    },
    [
      params.filteredEvents,
      params.selectedEventId,
      params.enableInteractivity,
      params.handleEventClick,
      params.handleReaction,
      params.handleEventAction,
    ]
  );

const useNarrativeDisplayState = (params: {
  sessionId: string;
  maxEvents: number;
  enableInteractivity: boolean;
  showAgentThoughts: boolean;
  compact: boolean;
}) => {
  const { state: wsState, sendMessage } = useWebSocketContext();
  const { optimizeForRealTime, createVirtualScrollConfig, deferUpdate, measureInteractionDelay } =
    usePerformanceOptimizer();

  const state = useNarrativeStateValues(params.showAgentThoughts);
  const { filteredEvents, virtualConfig } = useNarrativeDerivedState({
    events: state.events,
    searchQuery: state.searchQuery,
    filterType: state.filterType,
    filterEmotion: state.filterEmotion,
    showThoughts: state.showThoughts,
    sortBy: state.sortBy,
    compact: params.compact,
    createVirtualScrollConfig,
    scrollContainerRef: state.scrollContainerRef,
  });

  const { handleEventClick, handleReaction, handleEventAction } = useNarrativeEventHandlers({
    enableInteractivity: params.enableInteractivity,
    measureInteractionDelay,
    wsState,
    sendMessage,
    sessionId: params.sessionId,
    setSelectedEventId: state.setSelectedEventId,
  });

  useNarrativeRuntime({
    sessionId: params.sessionId,
    maxEvents: params.maxEvents,
    wsState,
    sendMessage,
    deferUpdate,
    setEvents: state.setEvents,
    setMetrics: state.setMetrics,
    optimizeForRealTime,
    autoScroll: state.autoScroll,
    filteredEvents,
    listRef: state.listRef,
  });

  const renderEvent = useNarrativeEventRenderer({
    filteredEvents,
    selectedEventId: state.selectedEventId,
    enableInteractivity: params.enableInteractivity,
    handleEventClick,
    handleReaction,
    handleEventAction,
  });

  return {
    wsState,
    listRef: state.listRef,
    scrollContainerRef: state.scrollContainerRef,
    searchQuery: state.searchQuery,
    setSearchQuery: state.setSearchQuery,
    filterType: state.filterType,
    setFilterType: state.setFilterType,
    sortBy: state.sortBy,
    setSortBy: state.setSortBy,
    autoScroll: state.autoScroll,
    setAutoScroll: state.setAutoScroll,
    showThoughts: state.showThoughts,
    setShowThoughts: state.setShowThoughts,
    metrics: state.metrics,
    virtualConfig,
    filteredEvents,
    renderEvent,
    hasFilters: Boolean(state.searchQuery || state.filterType !== 'all'),
  };
};

const EnhancedNarrativeDisplay: React.FC<EnhancedNarrativeDisplayProps> = ({
  sessionId,
  maxEvents = 1000,
  enableVirtualization = true,
  showAgentThoughts = false,
  enableInteractivity = true,
  className = '',
  compact = false
}) => {
  const {
    wsState,
    listRef,
    scrollContainerRef,
    searchQuery,
    setSearchQuery,
    filterType,
    setFilterType,
    sortBy,
    setSortBy,
    autoScroll,
    setAutoScroll,
    showThoughts,
    setShowThoughts,
    metrics,
    virtualConfig,
    filteredEvents,
    renderEvent,
    hasFilters,
  } = useNarrativeDisplayState({
    sessionId,
    maxEvents,
    enableInteractivity,
    showAgentThoughts,
    compact,
  });

  return (
    <div className={cn("enhanced-narrative-display", className, compact && "compact")}>
      <NarrativeDisplayBody
        metrics={metrics}
        isConnected={wsState.isConnected}
        searchQuery={searchQuery}
        filterType={filterType}
        sortBy={sortBy}
        autoScroll={autoScroll}
        showThoughts={showThoughts}
        onSearchChange={setSearchQuery}
        onFilterTypeChange={setFilterType}
        onSortChange={setSortBy}
        onAutoScrollToggle={() => setAutoScroll((prev) => !prev)}
        onAgentThoughtsToggle={() => setShowThoughts((prev) => !prev)}
        filteredEvents={filteredEvents}
        enableVirtualization={enableVirtualization}
        compact={compact}
        listRef={listRef}
        virtualConfig={virtualConfig}
        renderEvent={renderEvent}
        scrollContainerRef={scrollContainerRef}
        hasFilters={hasFilters}
      />
    </div>
  );
};

export default React.memo(EnhancedNarrativeDisplay);
