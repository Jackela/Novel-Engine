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
import { Card, CardHeader, CardTitle, CardContent, StatCard } from '../ui/Card';
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

const EnhancedNarrativeDisplay: React.FC<EnhancedNarrativeDisplayProps> = ({
  sessionId: _sessionId,
  maxEvents = 1000,
  enableVirtualization = true,
  showAgentThoughts = false,
  enableInteractivity = true,
  className = '',
  compact = false
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
  const [events, setEvents] = useState<EnhancedNarrativeEvent[]>([]);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [filterEmotion, _setFilterEmotion] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'timestamp' | 'priority' | 'reactions'>('timestamp');
  const [autoScroll, setAutoScroll] = useState(true);
  const [_viewMode, _setViewMode] = useState<'feed' | 'timeline' | 'compact'>('feed');

  // Performance metrics
  const [metrics, setMetrics] = useState({
    totalEvents: 0,
    streamingEvents: 0,
    avgConfidence: 0,
    recentActivity: 0
  });

  // Virtual scrolling configuration
  const virtualConfig = useMemo(() => {
    const containerHeight = scrollContainerRef.current?.clientHeight || 600;
    return createVirtualScrollConfig(events.length, compact ? 60 : 120, containerHeight);
  }, [events.length, createVirtualScrollConfig, compact]);

  // Filtered and sorted events
  const filteredEvents = useMemo(() => {
    PerformanceMonitor.start('event-filtering');
    
    let filtered = events;
    
    // Text search
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(event => 
        event.content.toLowerCase().includes(query) ||
        event.agentName?.toLowerCase().includes(query) ||
        event.tags.some(tag => tag.toLowerCase().includes(query)) ||
        event.characters.some(char => char.toLowerCase().includes(query))
      );
    }
    
    // Type filter
    if (filterType !== 'all') {
      filtered = filtered.filter(event => event.type === filterType);
    }
    
    // Emotion filter
    if (filterEmotion !== 'all') {
      filtered = filtered.filter(event => event.emotion === filterEmotion);
    }
    
    // Hide agent thoughts if disabled
    if (!showAgentThoughts) {
      filtered = filtered.filter(event => event.type !== 'agent_thought');
    }
    
    // Sort events
    const sorted = filtered.sort((a, b) => {
      switch (sortBy) {
        case 'priority':
          const priorityOrder = { critical: 0, high: 1, normal: 2, low: 3 };
          return priorityOrder[a.priority] - priorityOrder[b.priority];
        case 'reactions':
          return b.reactionCount - a.reactionCount;
        case 'timestamp':
        default:
          return b.timestamp - a.timestamp;
      }
    });
    
    PerformanceMonitor.end('event-filtering');
    return sorted;
  }, [events, searchQuery, filterType, filterEmotion, showAgentThoughts, sortBy]);

  // WebSocket event handlers
  const handleWebSocketMessage = useCallback((event: CustomEvent) => {
    const message = event.detail;
    
    switch (message.type) {
      case 'narrative_event':
        deferUpdate(() => {
          setEvents(prev => {
            const newEvents = [...prev];
            
            if (message.data.isStreaming && message.data.id) {
              // Update existing streaming event
              const eventIndex = newEvents.findIndex(e => e.id === message.data.id);
              if (eventIndex >= 0) {
                newEvents[eventIndex] = { 
                  ...newEvents[eventIndex], 
                  ...message.data,
                  tags: message.data.tags || [],
                  reactions: message.data.reactions || {},
                  reactionCount: Object.keys(message.data.reactions || {}).length,
                  characters: message.data.characters || [],
                  priority: message.data.priority || 'normal',
                  sentiment: message.data.sentiment || 0
                };
              }
            } else {
              // Add new event
              const enhancedEvent: EnhancedNarrativeEvent = {
                ...message.data,
                id: message.data.id || generateId('event'),
                tags: message.data.tags || [],
                reactions: message.data.reactions || {},
                reactionCount: Object.keys(message.data.reactions || {}).length,
                characters: message.data.characters || [],
                priority: message.data.priority || 'normal',
                sentiment: message.data.sentiment || 0
              };
              
              newEvents.unshift(enhancedEvent);
              
              if (newEvents.length > maxEvents) {
                newEvents.splice(maxEvents);
              }
            }
            
            return newEvents;
          });
        });
        break;
        
      case 'narrative_metrics':
        setMetrics({
          totalEvents: message.data.totalEvents || 0,
          streamingEvents: message.data.streamingEvents || 0,
          avgConfidence: message.data.avgConfidence || 0,
          recentActivity: message.data.recentActivity || 0
        });
        break;
    }
  }, [deferUpdate, maxEvents]);

  // Event interaction handlers
  const handleEventClick = useCallback((eventId: string) => {
    if (!enableInteractivity) return;
    
    measureInteractionDelay(() => {
      setSelectedEventId(prev => prev === eventId ? null : eventId);
    });
  }, [enableInteractivity, measureInteractionDelay]);

  const handleReaction = useCallback((eventId: string, reaction: string) => {
    if (!wsState.isConnected) return;
    
    sendMessage({
      type: 'narrative_reaction',
      data: {
        sessionId,
        eventId,
        reaction,
        userId: 'current_user'
      },
      priority: 'normal'
    });
  }, [wsState.isConnected, sendMessage, sessionId]);

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

  // Auto-scroll management
  useEffect(() => {
    if (autoScroll && listRef.current && filteredEvents.length > 0) {
      listRef.current.scrollToItem(0, 'start');
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

  // Get event type icon
  const getEventTypeIcon = (type: string) => {
    const icons = {
      action: '⚡',
      dialogue: '💬',
      description: '📝',
      system: '⚙️',
      agent_thought: '💭',
      user_input: '👤',
      world_event: '🌍'
    };
    return icons[type] || '📄';
  };

  // Get emotion color
  const getEmotionColor = (emotion?: string) => {
    const colors = {
      happy: 'text-green-600',
      sad: 'text-blue-600',
      angry: 'text-red-600',
      surprised: 'text-yellow-600',
      fearful: 'text-purple-600',
      neutral: 'text-gray-600'
    };
    return colors[emotion || 'neutral'] || 'text-gray-600';
  };

  // Render individual narrative event
  const renderEvent = useCallback(({ index, style }: { index: number; style: React.CSSProperties }) => {
    const event = filteredEvents[index];
    if (!event) return null;
    
    const isSelected = selectedEventId === event.id;
    const isStreaming = event.isStreaming;
    
    return (
      <div style={style} className="px-2 py-1">
        <Card
          variant={isSelected ? "interactive" : "elevated"}
          className={cn(
            "cursor-pointer transition-all duration-200 narrative-event-card",
            isSelected && "ring-2 ring-primary",
            isStreaming && "animate-pulse",
            event.priority === 'critical' && "ring-1 ring-red-500",
            event.priority === 'high' && "border-yellow-500"
          )}
          onClick={() => handleEventClick(event.id)}
          glow={event.priority === 'critical'}
        >
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
                  <Badge 
                    variant="ghost" 
                    size="sm"
                    className={cn("capitalize", getEmotionColor(event.emotion))}
                  >
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
                    className={event.confidence > 0.8 ? "text-green-600" : event.confidence > 0.5 ? "text-yellow-600" : "text-red-600"}
                  >
                    {Math.round(event.confidence * 100)}%
                  </Badge>
                )}
                <span className="text-xs text-muted-foreground">
                  {formatRelativeTime(event.timestamp)}
                </span>
              </div>
            </div>
          </CardHeader>

          <CardContent>
            <div className="space-y-3">
              <div className="prose prose-sm max-w-none">
                <p className={cn(
                  "text-sm leading-relaxed",
                  isStreaming && "typing-effect"
                )}>
                  {event.content}
                  {isStreaming && <span className="animate-pulse">|</span>}
                </p>
              </div>

              {event.location && (
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
              )}

              {event.characters.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {event.characters.map(character => (
                    <Badge key={character} variant="secondary" size="sm">
                      👤 {character}
                    </Badge>
                  ))}
                </div>
              )}

              {event.tags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {event.tags.map(tag => (
                    <Badge key={tag} variant="outline" size="sm">
                      #{tag}
                    </Badge>
                  ))}
                </div>
              )}

              {/* Reactions */}
              {enableInteractivity && (
                <div className="flex items-center justify-between pt-2">
                  <div className="flex items-center gap-1">
                    {['👍', '❤️', '😂', '😮', '😢'].map(emoji => (
                      <Button
                        key={emoji}
                        variant="ghost"
                        size="sm"
                        className="h-6 w-6 p-0 hover:scale-110"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleReaction(event.id, emoji);
                        }}
                      >
                        {emoji}
                      </Button>
                    ))}
                    {event.reactionCount > 0 && (
                      <span className="text-xs text-muted-foreground ml-2">
                        {event.reactionCount}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleEventAction(event.id, 'expand');
                      }}
                    >
                      🔍
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleEventAction(event.id, 'branch');
                      }}
                    >
                      🌿
                    </Button>
                  </div>
                </div>
              )}

              {/* Expanded details */}
              {isSelected && event.causality && (
                <Card variant="ghost" className="mt-3 p-3">
                  <div className="space-y-2">
                    {event.causality.causes.length > 0 && (
                      <div>
                        <h5 className="text-xs font-semibold text-muted-foreground">Causes:</h5>
                        <ul className="text-xs space-y-1 mt-1">
                          {event.causality.causes.map((cause, idx) => (
                            <li key={idx} className="flex items-start gap-2">
                              <span className="text-muted-foreground">←</span>
                              <span>{cause}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {event.causality.effects.length > 0 && (
                      <div>
                        <h5 className="text-xs font-semibold text-muted-foreground">Effects:</h5>
                        <ul className="text-xs space-y-1 mt-1">
                          {event.causality.effects.map((effect, idx) => (
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
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }, [filteredEvents, selectedEventId, enableInteractivity, handleEventClick, handleReaction, handleEventAction]);

  return (
    <div className={cn("enhanced-narrative-display", className, compact && "compact")}>
      {/* Header with metrics and controls */}
      <div className="mb-4 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold">Narrative Feed</h2>
          <StatusBadge status={wsState.isConnected ? 'online' : 'offline'} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <StatCard
            title="Total Events"
            value={metrics.totalEvents}
            color="info"
            icon={<span className="text-lg">📝</span>}
          />
          <StatCard
            title="Streaming"
            value={metrics.streamingEvents}
            color="success"
            icon={<span className="text-lg">⚡</span>}
          />
          <StatCard
            title="Avg Confidence"
            value={`${Math.round(metrics.avgConfidence * 100)}%`}
            color="warning"
            icon={<span className="text-lg">🎯</span>}
          />
          <StatCard
            title="Recent Activity"
            value={metrics.recentActivity}
            color="default"
            icon={<span className="text-lg">📊</span>}
          />
        </div>

        {/* Controls */}
        <div className="flex flex-wrap items-center gap-3">
          <input
            type="text"
            placeholder="Search events..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="px-3 py-2 bg-background border border-border rounded-md text-sm min-w-[200px]"
          />

          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
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
            onChange={(e) => setSortBy(e.target.value as 'timestamp' | 'priority' | 'reactions')}
            className="px-3 py-2 bg-background border border-border rounded-md text-sm"
          >
            <option value="timestamp">Latest</option>
            <option value="priority">Priority</option>
            <option value="reactions">Most Reactions</option>
          </select>

          <Button
            variant={autoScroll ? 'default' : 'outline'}
            size="sm"
            onClick={() => setAutoScroll(!autoScroll)}
          >
            Auto Scroll
          </Button>

          <Button
            variant={showAgentThoughts ? 'default' : 'outline'}
            size="sm"
            onClick={() => setShowAgentThoughts(!showAgentThoughts)}
          >
            Show Thoughts
          </Button>
        </div>
      </div>

      {/* Events Feed */}
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
              <div key={event.id}>
                {renderEvent({ index, style: {} })}
              </div>
            ))}
          </div>
        )}

        {filteredEvents.length === 0 && (
          <Card className="p-8 text-center">
            <div className="text-muted-foreground">
              <span className="text-4xl block mb-4">📝</span>
              <p>No narrative events found.</p>
              <p className="text-sm mt-2">
                {searchQuery || filterType !== 'all' 
                  ? 'Try adjusting your search or filters.'
                  : 'Start a narrative session to see events here.'
                }
              </p>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
};

export default React.memo(EnhancedNarrativeDisplay);
