import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from 'react-query';
import api from '../services/api';
import '../styles/design-system.css';
import './EmergentDashboard.css';

// Icons - we'll use simple SVG icons
const Icons = {
  Activity: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
    </svg>
  ),
  Users: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
      <circle cx="9" cy="7" r="4"></circle>
      <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
      <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
    </svg>
  ),
  Map: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"></polygon>
      <line x1="8" y1="2" x2="8" y2="18"></line>
      <line x1="16" y1="6" x2="16" y2="22"></line>
    </svg>
  ),
  Clock: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10"></circle>
      <polyline points="12 6 12 12 16 14"></polyline>
    </svg>
  ),
  TrendingUp: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline>
      <polyline points="17 6 23 6 23 12"></polyline>
    </svg>
  ),
  ChevronRight: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="9 18 15 12 9 6"></polyline>
    </svg>
  ),
  AlertCircle: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10"></circle>
      <line x1="12" y1="8" x2="12" y2="12"></line>
      <line x1="12" y1="16" x2="12.01" y2="16"></line>
    </svg>
  ),
  Settings: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="3"></circle>
      <path d="M12 1v6m0 6v6m4.22-13.22l4.24 4.24M1.54 1.54l4.24 4.24M20.46 20.46l-4.24-4.24M1.54 20.46l4.24-4.24"></path>
    </svg>
  ),
};

// Mock data for entities on the world map
const worldEntities = [
  { id: '1', name: 'Aria', type: 'protagonist', x: 30, y: 40, status: 'active' },
  { id: '2', name: 'Kael', type: 'supporting', x: 60, y: 25, status: 'active' },
  { id: '3', name: 'Shadowbane', type: 'antagonist', x: 75, y: 60, status: 'conflict' },
  { id: '4', name: 'Merchant', type: 'npc', x: 45, y: 70, status: 'neutral' },
];

// Mock data for narrative arcs
const narrativeArcs = [
  { id: '1', name: 'The Prophecy Unfolds', type: 'main', progress: 75, status: 'active' },
  { id: '2', name: 'Bonds of Brotherhood', type: 'character', progress: 60, status: 'active' },
  { id: '3', name: 'The Lost Artifact', type: 'mystery', progress: 30, status: 'pending' },
];

// Mock event cascade data
const eventCascade = [
  { id: '1', type: 'discovery', impact: 'high', character: 'Aria', description: 'Found ancient tome' },
  { id: '2', type: 'conflict', impact: 'medium', character: 'Kael', description: 'Confronted guards' },
  { id: '3', type: 'dialogue', impact: 'low', character: 'Merchant', description: 'Shared rumors' },
];

const EmergentDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);
  const [activityStream, setActivityStream] = useState<any[]>([]);

  // Fetch data
  const { data: systemStatus, isLoading: statusLoading } = useQuery(
    'system-status',
    api.getHealth,
    {
      refetchInterval: 10000,
    }
  );

  const { data: characters } = useQuery('characters', api.getCharacters);
  const { data: campaigns } = useQuery('campaigns', api.getCampaigns);

  // Simulate real-time activity
  useEffect(() => {
    const activities = [
      { timestamp: '12:34', character: 'Aria', content: 'discovered hidden passage in the ancient library' },
      { timestamp: '12:33', character: 'Kael', content: 'engaged in combat with shadow creatures' },
      { timestamp: '12:31', character: 'Shadowbane', content: 'cast dark spell affecting northern region' },
      { timestamp: '12:29', character: 'System', content: 'new narrative branch activated: The Prophecy' },
      { timestamp: '12:27', character: 'Merchant', content: 'revealed crucial information about artifact' },
    ];
    
    setActivityStream(activities);
  }, []);

  // Performance metrics
  const metrics = {
    turnTime: 2.3,
    cacheHit: 89,
    apiLatency: 45,
    activeThreads: 12,
  };

  return (
    <div className="emergent-dashboard">
      {/* Dashboard Header */}
      <header className="dashboard-header">
        <div className="dashboard-header__content">
          <h1 className="dashboard-title">
            Emergent Narrative Dashboard
          </h1>
          <p className="dashboard-subtitle">
            Real-time monitoring of emergent storytelling systems
          </p>
        </div>
        <div className="dashboard-header__actions">
          <button className="action-button action-button--primary">
            New Campaign
          </button>
          <button className="action-button action-button--secondary">
            <Icons.Settings />
          </button>
        </div>
      </header>

      {/* Bento Grid Layout */}
      <div className="bento-grid">
        {/* World State Map - Large Tile (spans 6 columns) */}
        <div className="bento-tile world-state-map" style={{ gridColumn: 'span 6' }}>
          <div className="bento-tile-header">
            <h2 className="bento-tile-title">
              <Icons.Map />
              World State Map
            </h2>
            <span className="status-indicator status-indicator--success">
              Live
            </span>
          </div>
          <div className="bento-tile-content">
            <div className="world-map-canvas">
              {worldEntities.map((entity) => (
                <div
                  key={entity.id}
                  className={`entity-marker entity-marker--${entity.type} ${
                    selectedEntity === entity.id ? 'entity-marker--selected' : ''
                  }`}
                  style={{ left: `${entity.x}%`, top: `${entity.y}%` }}
                  onClick={() => setSelectedEntity(entity.id)}
                  title={entity.name}
                >
                  <span className="entity-label">{entity.name[0]}</span>
                </div>
              ))}
            </div>
            <div className="world-map-legend">
              <div className="legend-item">
                <span className="legend-dot legend-dot--protagonist"></span>
                <span className="legend-label">Protagonist</span>
              </div>
              <div className="legend-item">
                <span className="legend-dot legend-dot--supporting"></span>
                <span className="legend-label">Supporting</span>
              </div>
              <div className="legend-item">
                <span className="legend-dot legend-dot--antagonist"></span>
                <span className="legend-label">Antagonist</span>
              </div>
              <div className="legend-item">
                <span className="legend-dot legend-dot--npc"></span>
                <span className="legend-label">NPC</span>
              </div>
            </div>
          </div>
        </div>

        {/* Character Networks - Medium Tile (spans 3 columns) */}
        <div className="bento-tile character-networks" style={{ gridColumn: 'span 3' }}>
          <div className="bento-tile-header">
            <h2 className="bento-tile-title">
              <Icons.Users />
              Character Networks
            </h2>
            <span className="tile-badge">{characters?.length || 0}</span>
          </div>
          <div className="bento-tile-content">
            <div className="character-list">
              {characters?.slice(0, 5).map((character: string) => (
                <div key={character} className="character-item">
                  <div className="character-avatar">
                    {character[0].toUpperCase()}
                  </div>
                  <div className="character-info">
                    <div className="character-name">{character}</div>
                    <div className="character-status">Active • 3 relations</div>
                  </div>
                  <Icons.ChevronRight />
                </div>
              )) || (
                <div className="empty-state">
                  <p>No characters loaded</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Narrative Timeline - Small Tile (spans 3 columns) */}
        <div className="bento-tile narrative-timeline" style={{ gridColumn: 'span 3' }}>
          <div className="bento-tile-header">
            <h2 className="bento-tile-title">
              <Icons.TrendingUp />
              Narrative Arcs
            </h2>
          </div>
          <div className="bento-tile-content">
            {narrativeArcs.map((arc) => (
              <div key={arc.id} className="arc-item">
                <div className="arc-header">
                  <span className={`arc-type arc-type--${arc.type}`}>
                    {arc.type}
                  </span>
                  <span className="arc-progress">{arc.progress}%</span>
                </div>
                <div className="arc-name">{arc.name}</div>
                <div className="arc-progress-bar">
                  <div 
                    className={`arc-progress-fill arc-progress-fill--${arc.type}`}
                    style={{ width: `${arc.progress}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Real-time Activity - Wide Tile (spans 4 columns) */}
        <div className="bento-tile real-time-activity" style={{ gridColumn: 'span 4' }}>
          <div className="bento-tile-header">
            <h2 className="bento-tile-title">
              <Icons.Activity />
              Real-time Activity
            </h2>
            <span className="status-indicator status-indicator--info">
              Live Feed
            </span>
          </div>
          <div className="bento-tile-content">
            <div className="activity-stream">
              {activityStream.map((activity, index) => (
                <div key={index} className="activity-item">
                  <span className="activity-timestamp">
                    {activity.timestamp}
                  </span>
                  <div className="activity-content">
                    <span className="activity-character">
                      {activity.character}
                    </span>
                    {' '}
                    {activity.content}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Event Cascade Flow - Medium Tile (spans 3 columns) */}
        <div className="bento-tile event-cascade" style={{ gridColumn: 'span 3' }}>
          <div className="bento-tile-header">
            <h2 className="bento-tile-title">
              Event Cascade
            </h2>
          </div>
          <div className="bento-tile-content">
            {eventCascade.map((event, index) => (
              <div key={event.id} className="cascade-item">
                <div className={`cascade-indicator cascade-indicator--${event.impact}`} />
                <div className="cascade-content">
                  <div className="cascade-header">
                    <span className={`cascade-type cascade-type--${event.type}`}>
                      {event.type}
                    </span>
                    <span className="cascade-character">{event.character}</span>
                  </div>
                  <div className="cascade-description">{event.description}</div>
                </div>
                {index < eventCascade.length - 1 && (
                  <div className="cascade-connector" />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Turn Pipeline Status - Small Tile (spans 2 columns) */}
        <div className="bento-tile turn-pipeline" style={{ gridColumn: 'span 2' }}>
          <div className="bento-tile-header">
            <h2 className="bento-tile-title">
              Pipeline Status
            </h2>
          </div>
          <div className="bento-tile-content">
            <div className="pipeline-stages">
              <div className="pipeline-stage pipeline-stage--complete">
                <div className="pipeline-dot" />
                <span>Analysis</span>
              </div>
              <div className="pipeline-stage pipeline-stage--active">
                <div className="pipeline-dot" />
                <span>Processing</span>
              </div>
              <div className="pipeline-stage pipeline-stage--pending">
                <div className="pipeline-dot" />
                <span>Integration</span>
              </div>
              <div className="pipeline-stage pipeline-stage--pending">
                <div className="pipeline-dot" />
                <span>Output</span>
              </div>
            </div>
          </div>
        </div>

        {/* Performance Metrics - Small Tile (spans 2 columns) */}
        <div className="bento-tile performance-metrics" style={{ gridColumn: 'span 2' }}>
          <div className="bento-tile-header">
            <h2 className="bento-tile-title">
              Performance
            </h2>
          </div>
          <div className="bento-tile-content">
            <div className="metric-item">
              <span className="metric-label">Turn Time</span>
              <span className="metric-value metric-status--good">
                {metrics.turnTime}s
              </span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Cache Hit</span>
              <span className="metric-value metric-status--good">
                {metrics.cacheHit}%
              </span>
            </div>
            <div className="metric-item">
              <span className="metric-label">API Latency</span>
              <span className="metric-value metric-status--warning">
                {metrics.apiLatency}ms
              </span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Active Threads</span>
              <span className="metric-value">
                {metrics.activeThreads}
              </span>
            </div>
          </div>
        </div>

        {/* System Health - Small Tile (spans 1 column) */}
        <div className="bento-tile system-health" style={{ gridColumn: 'span 1' }}>
          <div className="bento-tile-header">
            <h2 className="bento-tile-title">
              Health
            </h2>
          </div>
          <div className="bento-tile-content">
            <div className="health-status">
              <div className={`health-indicator health-indicator--${
                systemStatus?.api === 'running' ? 'healthy' : 'error'
              }`}>
                <div className="health-dot" />
                <span>API</span>
              </div>
              <div className="health-indicator health-indicator--healthy">
                <div className="health-dot" />
                <span>Cache</span>
              </div>
              <div className="health-indicator health-indicator--healthy">
                <div className="health-dot" />
                <span>Queue</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EmergentDashboard;