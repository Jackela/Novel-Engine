import React, { useState } from 'react';
import { Space, Badge, Progress, Tag, Typography, Statistic } from 'antd';
import {
  ActivityOutlined,
  TeamOutlined,
  EnvironmentOutlined,
  ClockCircleOutlined,
  RiseOutlined,
  RightCircleOutlined,
  AlertOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import AntBentoGrid, { createTile, TileConfig } from './AntBentoGrid';
import '../styles/design-system.css';
import './EmergentDashboard.css';

const { Text, Title } = Typography;

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

// World State Map Component
const WorldStateMap: React.FC<{ 
  selectedEntity: string | null; 
  onEntitySelect: (id: string) => void 
}> = ({ selectedEntity, onEntitySelect }) => {
  return (
    <div className="world-map" style={{ height: '100%', position: 'relative', minHeight: 400 }}>
      <div className="map-container" style={{ 
        position: 'relative', 
        height: 'calc(100% - 40px)', 
        background: 'linear-gradient(180deg, #1a1a1d 0%, #111113 100%)',
        borderRadius: 8,
        overflow: 'hidden'
      }}>
        {worldEntities.map((entity) => (
          <div
            key={entity.id}
            className={`map-entity entity-${entity.type} ${selectedEntity === entity.id ? 'selected' : ''}`}
            style={{ 
              position: 'absolute',
              left: `${entity.x}%`, 
              top: `${entity.y}%`,
              cursor: 'pointer',
              transform: 'translate(-50%, -50%)',
              transition: 'all 0.3s ease'
            }}
            onClick={() => onEntitySelect(entity.id)}
            title={entity.name}
          >
            <div className="entity-marker" style={{
              width: 12,
              height: 12,
              borderRadius: '50%',
              background: entity.type === 'protagonist' ? '#6366f1' :
                        entity.type === 'antagonist' ? '#ef4444' :
                        entity.type === 'supporting' ? '#10b981' : '#808088',
              boxShadow: '0 0 10px rgba(99, 102, 241, 0.5)'
            }}></div>
            <span className="entity-label" style={{
              position: 'absolute',
              top: '100%',
              left: '50%',
              transform: 'translateX(-50%)',
              fontSize: 10,
              color: '#b0b0b8',
              whiteSpace: 'nowrap',
              marginTop: 4
            }}>{entity.name}</span>
          </div>
        ))}
        <div className="map-grid" style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: 'linear-gradient(#2a2a30 1px, transparent 1px), linear-gradient(90deg, #2a2a30 1px, transparent 1px)',
          backgroundSize: '40px 40px',
          opacity: 0.1
        }}></div>
      </div>
      <Space style={{ marginTop: 12 }} wrap>
        <Badge color="#6366f1" text="Protagonist" />
        <Badge color="#10b981" text="Supporting" />
        <Badge color="#ef4444" text="Antagonist" />
        <Badge color="#808088" text="NPC" />
      </Space>
    </div>
  );
};

// Character Networks Component
const CharacterNetworks: React.FC = () => {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Space size="large">
        <Statistic title="Active Characters" value={12} valueStyle={{ color: '#6366f1' }} />
        <Statistic title="Relationships" value={34} valueStyle={{ color: '#10b981' }} />
      </Space>
      <div style={{ flex: 1, minHeight: 150 }}>
        <svg className="network-graph" viewBox="0 0 300 200" style={{ width: '100%', height: '100%' }}>
          {/* Character relationship lines */}
          <line x1="50" y1="50" x2="150" y2="100" stroke="#6366f1" strokeWidth="2" opacity="0.5" />
          <line x1="150" y1="100" x2="250" y2="50" stroke="#8b5cf6" strokeWidth="2" opacity="0.5" />
          <line x1="150" y1="100" x2="200" y2="150" stroke="#10b981" strokeWidth="2" opacity="0.5" />
          
          {/* Character nodes */}
          <circle cx="50" cy="50" r="8" fill="#6366f1" />
          <circle cx="150" cy="100" r="10" fill="#6366f1" />
          <circle cx="250" cy="50" r="8" fill="#10b981" />
          <circle cx="200" cy="150" r="6" fill="#808088" />
        </svg>
      </div>
    </div>
  );
};

// Narrative Timeline Component
const NarrativeTimeline: React.FC = () => {
  const typeColors = {
    main: '#6366f1',
    character: '#10b981',
    mystery: '#f59e0b'
  };

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      {narrativeArcs.map((arc) => (
        <div key={arc.id}>
          <Space style={{ marginBottom: 8, width: '100%', justifyContent: 'space-between' }}>
            <Space>
              <Tag color={typeColors[arc.type as keyof typeof typeColors]}>{arc.type}</Tag>
              <Text strong>{arc.name}</Text>
            </Space>
            <Text type="secondary">{arc.progress}%</Text>
          </Space>
          <Progress 
            percent={arc.progress} 
            strokeColor={typeColors[arc.type as keyof typeof typeColors]}
            showInfo={false}
            strokeWidth={8}
          />
        </div>
      ))}
    </Space>
  );
};

// Activity Stream Component
const ActivityStream: React.FC = () => {
  return (
    <Space direction="vertical" size="small" style={{ width: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>2m ago</Text>
        <Text>Aria discovered ancient tome</Text>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>5m ago</Text>
        <Text>Kael engaged in combat</Text>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>12m ago</Text>
        <Text>New quest unlocked</Text>
      </div>
    </Space>
  );
};

// Performance Metrics Component
const PerformanceMetrics: React.FC = () => {
  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text type="secondary">Response Time</Text>
        <Text strong style={{ color: '#10b981' }}>32ms</Text>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text type="secondary">Token Usage</Text>
        <Text strong style={{ color: '#6366f1' }}>2.4K/10K</Text>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text type="secondary">Cache Hit Rate</Text>
        <Text strong style={{ color: '#10b981' }}>94%</Text>
      </div>
    </Space>
  );
};

// Event Cascade Component
const EventCascadeFlow: React.FC = () => {
  const impactColors = {
    high: '#ef4444',
    medium: '#f59e0b',
    low: '#10b981'
  };

  const typeIcons = {
    discovery: '🔍',
    conflict: '⚔️',
    dialogue: '💬'
  };

  return (
    <Space direction="vertical" size="small" style={{ width: '100%' }}>
      {eventCascade.map((event) => (
        <div key={event.id} style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: 8,
          padding: '4px 8px',
          background: '#1a1a1d',
          borderRadius: 6,
          borderLeft: `3px solid ${impactColors[event.impact as keyof typeof impactColors]}`
        }}>
          <span>{typeIcons[event.type as keyof typeof typeIcons]}</span>
          <Text>{event.description}</Text>
        </div>
      ))}
    </Space>
  );
};

// Pipeline Status Component
const PipelineStatus: React.FC = () => {
  const stages = [
    { name: 'Input', status: 'complete' },
    { name: 'Process', status: 'complete' },
    { name: 'Generate', status: 'active' },
    { name: 'Output', status: 'pending' }
  ];

  const statusSymbols = {
    complete: '✓',
    active: '...',
    pending: '-'
  };

  const statusColors = {
    complete: '#10b981',
    active: '#6366f1',
    pending: '#606068'
  };

  return (
    <Space direction="vertical" size="small" style={{ width: '100%' }}>
      {stages.map((stage, index) => (
        <div key={index} style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '6px 12px',
          background: stage.status === 'active' ? '#1a1a1d' : 'transparent',
          borderRadius: 6,
          transition: 'all 0.3s ease'
        }}>
          <Text style={{ color: statusColors[stage.status as keyof typeof statusColors] }}>
            {stage.name}
          </Text>
          <Text strong style={{ color: statusColors[stage.status as keyof typeof statusColors] }}>
            {statusSymbols[stage.status as keyof typeof statusSymbols]}
          </Text>
        </div>
      ))}
    </Space>
  );
};

const EmergentDashboardSimple: React.FC = () => {
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);

  // Create tile configurations with proper Ant Design components
  const tiles: TileConfig[] = [
    // Large tile - World State Map
    createTile(
      'world-map',
      'large',
      'World State Map',
      <WorldStateMap selectedEntity={selectedEntity} onEntitySelect={setSelectedEntity} />,
      {
        extra: <Badge status="success" text="Live" />,
        style: { minHeight: 450 }
      }
    ),

    // Medium tiles
    createTile(
      'character-networks',
      'medium',
      'Character Networks',
      <CharacterNetworks />,
      {
        style: { minHeight: 300 }
      }
    ),
    
    createTile(
      'narrative-timeline',
      'medium',
      'Narrative Timeline',
      <NarrativeTimeline />,
      {
        style: { minHeight: 300 }
      }
    ),

    // Small tiles
    createTile(
      'activity-stream',
      'small',
      'Activity Stream',
      <ActivityStream />,
      {
        style: { minHeight: 200 }
      }
    ),
    
    createTile(
      'performance',
      'small',
      'Performance',
      <PerformanceMetrics />,
      {
        style: { minHeight: 200 }
      }
    ),
    
    createTile(
      'event-cascade',
      'small',
      'Event Cascade',
      <EventCascadeFlow />,
      {
        style: { minHeight: 200 }
      }
    ),
    
    createTile(
      'pipeline-status',
      'small',
      'Pipeline Status',
      <PipelineStatus />,
      {
        style: { minHeight: 200 }
      }
    ),
  ];

  return (
    <div className="emergent-dashboard" style={{ 
      width: '100%',
      maxWidth: '1600px',
      margin: '0 auto'
    }}>
      <AntBentoGrid 
        tiles={tiles}
        gutter={[16, 16]}
      />
    </div>
  );
};

export default EmergentDashboardSimple;