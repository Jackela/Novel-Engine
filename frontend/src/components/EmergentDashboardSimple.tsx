import React, { useState } from 'react';
import '../styles/design-system.css';
import './EmergentDashboard.css';

// Icons - simple SVG icons
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

const EmergentDashboardSimple: React.FC = () => {
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);

  return (
    <div className="emergent-dashboard">
      {/* Dashboard Header */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1 className="dashboard-title">Emergent Narrative Dashboard</h1>
          <div className="header-actions">
            <button className="btn-primary">New Campaign</button>
            <button className="btn-secondary">
              <Icons.Settings />
            </button>
          </div>
        </div>
      </header>

      {/* Bento Grid Layout */}
      <div className="bento-grid">
        {/* World State Map - Large tile */}
        <div className="bento-tile tile-large">
          <div className="tile-header">
            <h2 className="tile-title">
              <Icons.Map />
              World State Map
            </h2>
            <span className="badge badge-success">Live</span>
          </div>
          <div className="world-map">
            <div className="map-container">
              {worldEntities.map((entity) => (
                <div
                  key={entity.id}
                  className={`map-entity entity-${entity.type} ${selectedEntity === entity.id ? 'selected' : ''}`}
                  style={{ left: `${entity.x}%`, top: `${entity.y}%` }}
                  onClick={() => setSelectedEntity(entity.id)}
                  title={entity.name}
                >
                  <div className="entity-marker"></div>
                  <span className="entity-label">{entity.name}</span>
                </div>
              ))}
              <div className="map-grid"></div>
            </div>
            <div className="map-legend">
              <div className="legend-item">
                <span className="legend-dot protagonist"></span>
                Protagonist
              </div>
              <div className="legend-item">
                <span className="legend-dot supporting"></span>
                Supporting
              </div>
              <div className="legend-item">
                <span className="legend-dot antagonist"></span>
                Antagonist
              </div>
              <div className="legend-item">
                <span className="legend-dot npc"></span>
                NPC
              </div>
            </div>
          </div>
        </div>

        {/* Character Networks - Medium tile */}
        <div className="bento-tile tile-medium">
          <div className="tile-header">
            <h2 className="tile-title">
              <Icons.Users />
              Character Networks
            </h2>
          </div>
          <div className="character-network">
            <div className="network-stats">
              <div className="stat">
                <span className="stat-value">12</span>
                <span className="stat-label">Active Characters</span>
              </div>
              <div className="stat">
                <span className="stat-value">34</span>
                <span className="stat-label">Relationships</span>
              </div>
            </div>
            <div className="network-visual">
              <svg className="network-graph" viewBox="0 0 300 200">
                {/* Character relationship lines */}
                <line x1="50" y1="50" x2="150" y2="100" stroke="var(--color-primary)" strokeWidth="2" opacity="0.5" />
                <line x1="150" y1="100" x2="250" y2="50" stroke="var(--color-secondary)" strokeWidth="2" opacity="0.5" />
                <line x1="150" y1="100" x2="200" y2="150" stroke="var(--color-success)" strokeWidth="2" opacity="0.5" />
                
                {/* Character nodes */}
                <circle cx="50" cy="50" r="8" fill="var(--color-character-protagonist)" />
                <circle cx="150" cy="100" r="10" fill="var(--color-character-protagonist)" />
                <circle cx="250" cy="50" r="8" fill="var(--color-character-supporting)" />
                <circle cx="200" cy="150" r="6" fill="var(--color-character-npc)" />
              </svg>
            </div>
          </div>
        </div>

        {/* Narrative Timeline - Medium tile */}
        <div className="bento-tile tile-medium">
          <div className="tile-header">
            <h2 className="tile-title">
              <Icons.Clock />
              Narrative Timeline
            </h2>
          </div>
          <div className="narrative-timeline">
            {narrativeArcs.map((arc) => (
              <div key={arc.id} className="timeline-arc">
                <div className="arc-header">
                  <span className={`arc-type arc-${arc.type}`}>{arc.type}</span>
                  <span className="arc-name">{arc.name}</span>
                </div>
                <div className="arc-progress">
                  <div className="progress-bar">
                    <div 
                      className="progress-fill"
                      style={{ width: `${arc.progress}%` }}
                    ></div>
                  </div>
                  <span className="progress-text">{arc.progress}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Real-time Activity Stream - Small tile */}
        <div className="bento-tile tile-small">
          <div className="tile-header">
            <h2 className="tile-title">
              <Icons.Activity />
              Activity Stream
            </h2>
          </div>
          <div className="activity-stream">
            <div className="activity-item">
              <span className="activity-time">2m ago</span>
              <span className="activity-text">Aria discovered ancient tome</span>
            </div>
            <div className="activity-item">
              <span className="activity-time">5m ago</span>
              <span className="activity-text">Kael engaged in combat</span>
            </div>
            <div className="activity-item">
              <span className="activity-time">12m ago</span>
              <span className="activity-text">New quest unlocked</span>
            </div>
          </div>
        </div>

        {/* Performance Metrics - Small tile */}
        <div className="bento-tile tile-small">
          <div className="tile-header">
            <h2 className="tile-title">
              <Icons.TrendingUp />
              Performance
            </h2>
          </div>
          <div className="performance-metrics">
            <div className="metric">
              <span className="metric-label">Response Time</span>
              <span className="metric-value">32ms</span>
            </div>
            <div className="metric">
              <span className="metric-label">Token Usage</span>
              <span className="metric-value">2.4K/10K</span>
            </div>
            <div className="metric">
              <span className="metric-label">Cache Hit Rate</span>
              <span className="metric-value">94%</span>
            </div>
          </div>
        </div>

        {/* Event Cascade Flow - Small tile */}
        <div className="bento-tile tile-small">
          <div className="tile-header">
            <h2 className="tile-title">
              <Icons.AlertCircle />
              Event Cascade
            </h2>
          </div>
          <div className="event-cascade">
            {eventCascade.map((event) => (
              <div key={event.id} className={`event-item impact-${event.impact}`}>
                <span className={`event-type type-${event.type}`}>{event.type}</span>
                <span className="event-desc">{event.description}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Turn Pipeline Status - Small tile */}
        <div className="bento-tile tile-small">
          <div className="tile-header">
            <h2 className="tile-title">
              <Icons.ChevronRight />
              Pipeline Status
            </h2>
          </div>
          <div className="pipeline-status">
            <div className="pipeline-stage complete">
              <span className="stage-name">Input</span>
              <span className="stage-status">✓</span>
            </div>
            <div className="pipeline-stage complete">
              <span className="stage-name">Process</span>
              <span className="stage-status">✓</span>
            </div>
            <div className="pipeline-stage active">
              <span className="stage-name">Generate</span>
              <span className="stage-status">...</span>
            </div>
            <div className="pipeline-stage pending">
              <span className="stage-name">Output</span>
              <span className="stage-status">-</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EmergentDashboardSimple;