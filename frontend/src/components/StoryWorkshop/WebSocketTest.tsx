import React, { useState } from 'react';
import {
  Box,
  Button,
  Typography,
  Card,
  CardContent,
  Alert,
  Chip,
  TextField,
} from '@mui/material';
import { useWebSocketProgress } from '../../hooks/useWebSocketProgress';

/**
 * Test component for WebSocket real-time progress functionality
 * This component is for development/testing purposes only
 */
export default function WebSocketTest() {
  const [testGenerationId, setTestGenerationId] = useState('story_test123');
  const [isTestActive, setIsTestActive] = useState(false);

  const {
    isConnected,
    lastUpdate,
    error,
    connectionAttempts,
    connect: _connect,
    disconnect: _disconnect,
    sendMessage,
  } = useWebSocketProgress({
    generationId: isTestActive ? testGenerationId : null,
    enabled: isTestActive,
    onUpdate: (update) => {
      console.log('WebSocket Update Received:', update);
    },
    onError: (error) => {
      console.error('WebSocket Error:', error);
    },
    onConnect: () => {
      console.log('WebSocket Connected');
    },
    onDisconnect: () => {
      console.log('WebSocket Disconnected');
    },
  });

  const handleStartTest = () => {
    setIsTestActive(true);
  };

  const handleStopTest = () => {
    setIsTestActive(false);
  };

  const handleSendTestMessage = () => {
    sendMessage('test message from client');
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" sx={{ mb: 3, fontWeight: 600 }}>
        WebSocket Real-Time Progress Test
      </Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Connection Controls
          </Typography>

          <Box sx={{ display: 'flex', gap: 2, mb: 2, alignItems: 'center' }}>
            <TextField
              label="Generation ID"
              value={testGenerationId}
              onChange={(e) => setTestGenerationId(e.target.value)}
              size="small"
              disabled={isTestActive}
            />
            
            <Button
              variant="contained"
              onClick={handleStartTest}
              disabled={isTestActive}
              color="primary"
            >
              Start Connection
            </Button>
            
            <Button
              variant="outlined"
              onClick={handleStopTest}
              disabled={!isTestActive}
              color="secondary"
            >
              Stop Connection
            </Button>
            
            <Button
              variant="text"
              onClick={handleSendTestMessage}
              disabled={!isConnected}
            >
              Send Test Message
            </Button>
          </Box>

          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              Status:
            </Typography>
            <Chip
              label={
                isConnected
                  ? 'Connected'
                  : isTestActive
                  ? connectionAttempts > 0
                    ? `Reconnecting (${connectionAttempts})`
                    : 'Connecting...'
                  : 'Disconnected'
              }
              color={
                isConnected
                  ? 'success'
                  : isTestActive
                  ? 'warning'
                  : 'default'
              }
              size="small"
            />
          </Box>
        </CardContent>
      </Card>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          <Typography variant="subtitle2">WebSocket Error</Typography>
          <Typography variant="body2">{error}</Typography>
        </Alert>
      )}

      {lastUpdate && (
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Latest Update Received
            </Typography>

            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 2 }}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Progress
                </Typography>
                <Typography variant="h4" color="primary.main">
                  {Math.round(lastUpdate.progress)}%
                </Typography>
              </Box>

              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Stage
                </Typography>
                <Typography variant="body1" sx={{ fontWeight: 600 }}>
                  {lastUpdate.stage}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {lastUpdate.stage_detail}
                </Typography>
              </Box>

              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Time Remaining
                </Typography>
                <Typography variant="body1">
                  {Math.floor(lastUpdate.estimated_time_remaining / 60)}m {lastUpdate.estimated_time_remaining % 60}s
                </Typography>
              </Box>

              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Active Agents
                </Typography>
                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                  {lastUpdate.active_agents.map((agent) => (
                    <Chip
                      key={agent}
                      label={agent.replace('Agent', '')}
                      size="small"
                      variant="outlined"
                    />
                  ))}
                </Box>
              </Box>
            </Box>

            <Box sx={{ mt: 2, p: 2, bgcolor: 'action.hover', borderRadius: 1 }}>
              <Typography variant="caption" color="text.secondary">
                Raw Update Data:
              </Typography>
              <Typography
                variant="body2"
                component="pre"
                sx={{ fontFamily: 'monospace', fontSize: '0.75rem', whiteSpace: 'pre-wrap' }}
              >
                {JSON.stringify(lastUpdate, null, 2)}
              </Typography>
            </Box>
          </CardContent>
        </Card>
      )}

      <Box sx={{ mt: 3, p: 2, bgcolor: 'info.light', borderRadius: 1, color: 'info.contrastText' }}>
        <Typography variant="body2">
          <strong>Testing Instructions:</strong>
        </Typography>
        <Typography variant="body2" sx={{ mt: 1 }}>
          1. Ensure the backend server is running with the new WebSocket endpoints<br/>
          2. Enter a generation ID (use "story_test123" for mock data)<br/>
          3. Click "Start Connection" to establish WebSocket connection<br/>
          4. Start a story generation to see real-time progress updates<br/>
          5. Monitor the browser console for detailed logs
        </Typography>
      </Box>
    </Box>
  );
}
