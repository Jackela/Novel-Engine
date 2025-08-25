/**
 * Main Novel Engine Application Component
 * ======================================
 * 
 * Primary React application component integrating all features:
 * - Real-time narrative display
 * - Agent management interface
 * - WebSocket communication
 * - Performance optimization
 */

import React, { useState, useEffect, useCallback } from 'react';
import { WebSocketProvider } from './hooks/useWebSocket';
import { PerformanceProvider } from './hooks/usePerformanceOptimizer';
import EnhancedNarrativeDisplay from './components/enhanced/EnhancedNarrativeDisplay';
import EnhancedAgentInterface from './components/enhanced/EnhancedAgentInterface';
import { Button } from './components/ui/Button';
import { Badge, StatusBadge } from './components/ui/Badge';
import { cn } from './lib/utils';
import './App.css';

interface AppState {
  sessionId: string;
  isConnected: boolean;
  currentView: 'narrative' | 'agents' | 'split';
  darkMode: boolean;
  performanceMode: boolean;
}

const App: React.FC = () => {
  const [appState, setAppState] = useState<AppState>({
    sessionId: `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    isConnected: false,
    currentView: 'split',
    darkMode: false,
    performanceMode: true
  });

  // WebSocket configuration
  const webSocketOptions = {
    url: process.env.REACT_APP_WS_URL || 'ws://localhost:8001/ws',
    protocols: ['novel-engine-v1'],
    maxReconnectAttempts: 10,
    reconnectInterval: 1000,
    maxReconnectInterval: 30000,
    heartbeatInterval: 30000,
    messageQueueSize: 1000,
    enableCompression: true,
    enableMessageDeduplication: true
  };

  // Theme management
  useEffect(() => {
    const savedTheme = localStorage.getItem('novel-engine-theme');
    const systemDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    const shouldUseDarkMode = savedTheme ? savedTheme === 'dark' : systemDarkMode;
    
    setAppState(prev => ({ ...prev, darkMode: shouldUseDarkMode }));
    document.documentElement.setAttribute('data-theme', shouldUseDarkMode ? 'dark' : 'light');
  }, []);

  // Session management
  useEffect(() => {
    const savedSessionId = sessionStorage.getItem('novel-engine-session-id');
    if (savedSessionId) {
      setAppState(prev => ({ ...prev, sessionId: savedSessionId }));
    } else {
      sessionStorage.setItem('novel-engine-session-id', appState.sessionId);
    }
  }, [appState.sessionId]);

  // View management
  const handleViewChange = useCallback((view: AppState['currentView']) => {
    setAppState(prev => ({ ...prev, currentView: view }));
    localStorage.setItem('novel-engine-view', view);
  }, []);

  // Theme toggle
  const toggleTheme = useCallback(() => {
    setAppState(prev => {
      const newDarkMode = !prev.darkMode;
      localStorage.setItem('novel-engine-theme', newDarkMode ? 'dark' : 'light');
      document.documentElement.setAttribute('data-theme', newDarkMode ? 'dark' : 'light');
      return { ...prev, darkMode: newDarkMode };
    });
  }, []);

  // Performance mode toggle
  const togglePerformanceMode = useCallback(() => {
    setAppState(prev => ({ ...prev, performanceMode: !prev.performanceMode }));
  }, []);

  // New session handler
  const startNewSession = useCallback(() => {
    const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    setAppState(prev => ({ ...prev, sessionId: newSessionId }));
    sessionStorage.setItem('novel-engine-session-id', newSessionId);
  }, []);

  // Connection status handler
  const handleConnectionChange = useCallback((isConnected: boolean) => {
    setAppState(prev => ({ ...prev, isConnected }));
  }, []);

  // Connection status listener
  useEffect(() => {
    const handleWebSocketMessage = (event: CustomEvent) => {
      const message = event.detail;
      if (message.type === 'connection_status') {
        handleConnectionChange(message.data.isConnected);
      }
    };

    window.addEventListener('websocket-message', handleWebSocketMessage);
    return () => window.removeEventListener('websocket-message', handleWebSocketMessage);
  }, [handleConnectionChange]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyboard = (event: KeyboardEvent) => {
      if (event.ctrlKey || event.metaKey) {
        switch (event.key) {
          case '1':
            event.preventDefault();
            handleViewChange('narrative');
            break;
          case '2':
            event.preventDefault();
            handleViewChange('agents');
            break;
          case '3':
            event.preventDefault();
            handleViewChange('split');
            break;
          case 'd':
            event.preventDefault();
            toggleTheme();
            break;
          case 'n':
            event.preventDefault();
            startNewSession();
            break;
        }
      }
    };

    window.addEventListener('keydown', handleKeyboard);
    return () => window.removeEventListener('keydown', handleKeyboard);
  }, [handleViewChange, toggleTheme, startNewSession]);

  // Render main content based on current view
  const renderContent = () => {
    switch (appState.currentView) {
      case 'narrative':
        return (
          <div className="single-panel">
            <EnhancedNarrativeDisplay
              sessionId={appState.sessionId}
              maxEvents={1000}
              enableVirtualization={appState.performanceMode}
              showAgentThoughts={true}
              enableInteractivity={true}
              className="full-height"
            />
          </div>
        );
        
      case 'agents':
        return (
          <div className="single-panel">
            <EnhancedAgentInterface
              sessionId={appState.sessionId}
              allowDirectControl={true}
              showAdvancedControls={true}
              maxAgents={10}
              className="full-height"
            />
          </div>
        );
        
      case 'split':
      default:
        return (
          <div className="split-panel">
            <div className="split-panel__left">
              <EnhancedNarrativeDisplay
                sessionId={appState.sessionId}
                maxEvents={500}
                enableVirtualization={appState.performanceMode}
                showAgentThoughts={false}
                enableInteractivity={true}
              />
            </div>
            <div className="split-panel__right">
              <EnhancedAgentInterface
                sessionId={appState.sessionId}
                allowDirectControl={true}
                showAdvancedControls={false}
                maxAgents={8}
              />
            </div>
          </div>
        );
    }
  };

  return (
    <PerformanceProvider enableAutoOptimization={appState.performanceMode}>
      <WebSocketProvider options={webSocketOptions}>
        <div className={`app ${appState.darkMode ? 'app--dark' : 'app--light'}`}>
          <header className="app-header">
            <div className="app-header__left">
              <h1 className="app-title">Novel Engine</h1>
              <Badge variant="outline" size="sm" className="mt-1">
                Session: {appState.sessionId.split('_')[1]}
              </Badge>
            </div>
            
            <div className="app-header__center">
              <div className="view-selector flex items-center gap-2">
                <Button
                  variant={appState.currentView === 'narrative' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => handleViewChange('narrative')}
                  title="Narrative View (Ctrl/Cmd+1)"
                >
                  📖 Story
                </Button>
                <Button
                  variant={appState.currentView === 'agents' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => handleViewChange('agents')}
                  title="Agents View (Ctrl/Cmd+2)"
                >
                  🤖 Agents
                </Button>
                <Button
                  variant={appState.currentView === 'split' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => handleViewChange('split')}
                  title="Split View (Ctrl/Cmd+3)"
                >
                  📱 Split
                </Button>
              </div>
            </div>
            
            <div className="app-header__right">
              <div className="app-controls flex items-center gap-2">
                <Button
                  variant={appState.performanceMode ? 'default' : 'outline'}
                  size="sm"
                  onClick={togglePerformanceMode}
                  title="Toggle Performance Mode"
                >
                  ⚡
                </Button>
                
                <Button
                  variant="outline"
                  size="sm"
                  onClick={toggleTheme}
                  title="Toggle Theme (Ctrl/Cmd+D)"
                >
                  {appState.darkMode ? '☀️' : '🌙'}
                </Button>
                
                <Button
                  variant="outline"
                  size="sm"
                  onClick={startNewSession}
                  title="New Session (Ctrl/Cmd+N)"
                >
                  🔄
                </Button>
              </div>
              
              <div className="connection-indicator flex items-center gap-2">
                <StatusBadge 
                  status={appState.isConnected ? 'online' : 'offline'} 
                  showLabel={false}
                />
                <span className="text-sm">
                  {appState.isConnected ? 'Connected' : 'Connecting...'}
                </span>
              </div>
            </div>
          </header>
          
          <main className="app-content">
            {renderContent()}
          </main>
          
          <footer className="app-footer">
            <div className="app-footer__left">
              <Badge variant="ghost" size="sm">
                Novel Engine v2.0 - Advanced AI Narrative Generation
              </Badge>
            </div>
            
            <div className="app-footer__center">
              <Badge variant="ghost" size="sm" className="text-xs">
                Keyboard: Ctrl/Cmd+1-3 (Views), Ctrl/Cmd+D (Theme), Ctrl/Cmd+N (New)
              </Badge>
            </div>
            
            <div className="app-footer__right">
              <Badge variant="secondary" size="sm">
                Session: {appState.sessionId.substring(0, 12)}...
              </Badge>
            </div>
          </footer>
          
          {/* Performance Metrics Overlay (Development) */}
          {process.env.NODE_ENV === 'development' && (
            <div className="dev-metrics fixed bottom-4 left-4 p-4 bg-card border rounded-lg shadow-lg space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span>Session:</span>
                <Badge variant="outline" size="sm" className="ml-2 font-mono text-xs">
                  {appState.sessionId.substring(0, 16)}...
                </Badge>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span>View:</span>
                <Badge variant="secondary" size="sm" className="ml-2">
                  {appState.currentView}
                </Badge>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span>Performance:</span>
                <Badge 
                  variant={appState.performanceMode ? 'success' : 'secondary'} 
                  size="sm" 
                  className="ml-2"
                >
                  {appState.performanceMode ? 'ON' : 'OFF'}
                </Badge>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span>Theme:</span>
                <Badge variant="info" size="sm" className="ml-2">
                  {appState.darkMode ? 'Dark' : 'Light'}
                </Badge>
              </div>
            </div>
          )}
        </div>
      </WebSocketProvider>
    </PerformanceProvider>
  );
};

export default App;