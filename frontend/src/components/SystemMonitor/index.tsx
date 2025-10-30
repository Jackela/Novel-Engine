import React, { useState } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Paper,
  Chip,
  LinearProgress,
  Alert,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
  Button,
  Switch,
  FormControlLabel,
  Tabs,
  Tab,
} from '@mui/material';
import {
  Monitor as MonitoringIcon,
  Speed as SpeedIcon,
  Memory as MemoryIcon,
  Storage as StorageIcon,
  Api as ApiIcon,
  TrendingUp as TrendingUpIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  Download as DownloadIcon,
  Settings as SettingsIcon,
  Timeline as TimelineIcon,
  Analytics as AnalyticsIcon,
  Psychology as PsychologyIcon,
  Group as GroupIcon,
  AutoStories as StoryIcon,
} from '@mui/icons-material';
import { useQuery } from 'react-query';
import api from '../../services/api';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel({ children, value, index, ...other }: TabPanelProps) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`monitor-tabpanel-${index}`}
      aria-labelledby={`monitor-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

// Mock system metrics - in real app, these would come from API
const MOCK_METRICS = {
  api: {
    responseTime: 145,
    requestsPerSecond: 12.3,
    errorRate: 0.2,
    uptime: 99.7,
  },
  system: {
    cpuUsage: 34.5,
    memoryUsage: 67.8,
    diskUsage: 23.1,
    networkIn: 2.4,
    networkOut: 1.8,
  },
  aiServices: {
    tokenUsage: 15420,
    tokenLimit: 50000,
    cacheHitRate: 89.2,
    averageGenerationTime: 42.3,
  },
  application: {
    activeUsers: 3,
    totalCharacters: 12,
    totalStories: 8,
    storiesGenerated24h: 3,
  },
};

const MOCK_LOGS = [
  {
    id: '1',
    timestamp: new Date(Date.now() - 5 * 60 * 1000),
    level: 'INFO',
    message: 'Story generation completed successfully',
    details: 'Generated story "The Last Stand" with 2 characters',
  },
  {
    id: '2',
    timestamp: new Date(Date.now() - 15 * 60 * 1000),
    level: 'INFO',
    message: 'Character "krieg_guardsman" created',
    details: 'New character added to the system',
  },
  {
    id: '3',
    timestamp: new Date(Date.now() - 30 * 60 * 1000),
    level: 'WARNING',
    message: 'High token usage detected',
    details: 'Token usage at 85% of daily limit',
  },
  {
    id: '4',
    timestamp: new Date(Date.now() - 45 * 60 * 1000),
    level: 'ERROR',
    message: 'API rate limit reached',
    details: 'OpenAI API rate limit exceeded, retry in 60 seconds',
  },
  {
    id: '5',
    timestamp: new Date(Date.now() - 60 * 60 * 1000),
    level: 'INFO',
    message: 'System startup completed',
    details: 'Novel Engine backend started successfully',
  },
];

export default function SystemMonitor() {
  const [activeTab, setActiveTab] = useState(0);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Fetch system status
  const { data: systemStatus, isLoading: statusLoading, refetch: refetchStatus } = useQuery(
    'system-status-monitor',
    api.getSystemStatus,
    {
      refetchInterval: autoRefresh ? 10000 : false, // Refresh every 10 seconds if auto-refresh is on
      retry: 1,
    }
  );

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleRefresh = () => {
    refetchStatus();
  };

  const getHealthColor = (value: number, thresholds: { good: number; warning: number }) => {
    if (value >= thresholds.good) return 'success';
    if (value >= thresholds.warning) return 'warning';
    return 'error';
  };

  const getLogLevelColor = (level: string) => {
    switch (level) {
      case 'ERROR':
        return 'error';
      case 'WARNING':
        return 'warning';
      case 'INFO':
        return 'info';
      default:
        return 'default';
    }
  };

  const formatTimestamp = (timestamp: Date) => {
    return timestamp.toLocaleTimeString();
  };

  // Removed unused formatBytes helper to satisfy linting; add back when needed.

  return (
    <Box sx={{ maxWidth: 1400, mx: 'auto' }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Box>
            <Typography variant="h3" component="h1" sx={{ mb: 1, fontWeight: 700 }}>
              System Monitor
            </Typography>
            <Typography variant="h6" color="text.secondary">
              Real-time system performance and health monitoring
            </Typography>
          </Box>

          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <FormControlLabel
              control={
                <Switch
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                />
              }
              label="Auto-refresh"
            />
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={handleRefresh}
              disabled={statusLoading}
            >
              Refresh
            </Button>
          </Box>
        </Box>

        {/* System Status Banner */}
        <Alert
          severity={systemStatus?.api === 'healthy' ? 'success' : 'warning'}
          sx={{ mb: 3 }}
          action={
            <Chip
              label={systemStatus?.api || 'Unknown'}
              color={systemStatus?.api === 'healthy' ? 'success' : 'warning'}
              size="small"
            />
          }
        >
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            System Status: {systemStatus?.api === 'healthy' ? 'All systems operational' : 'Some issues detected'}
          </Typography>
          <Typography variant="body2">
            Last updated: {new Date().toLocaleTimeString()}
            {systemStatus?.version && ` • Version: ${systemStatus.version}`}
          </Typography>
        </Alert>
      </Box>

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={handleTabChange} aria-label="monitor tabs">
          <Tab label="Overview" />
          <Tab label="Performance" />
          <Tab label="AI Services" />
          <Tab label="System Logs" />
        </Tabs>
      </Box>

      {/* Overview Tab */}
      <TabPanel value={activeTab} index={0}>
        <Grid container spacing={3}>
          {/* Key Metrics Cards */}
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent sx={{ textAlign: 'center' }}>
                <ApiIcon sx={{ fontSize: 40, color: 'primary.main', mb: 1 }} />
                <Typography variant="h4" sx={{ fontWeight: 700, mb: 0.5 }}>
                  {MOCK_METRICS.api.responseTime}ms
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Avg Response Time
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={Math.min((200 - MOCK_METRICS.api.responseTime) / 2, 100)}
                  color="success"
                  sx={{ mt: 1, height: 4, borderRadius: 1 }}
                />
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent sx={{ textAlign: 'center' }}>
                <TrendingUpIcon sx={{ fontSize: 40, color: 'info.main', mb: 1 }} />
                <Typography variant="h4" sx={{ fontWeight: 700, mb: 0.5 }}>
                  {MOCK_METRICS.api.uptime}%
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  System Uptime
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={MOCK_METRICS.api.uptime}
                  color="success"
                  sx={{ mt: 1, height: 4, borderRadius: 1 }}
                />
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent sx={{ textAlign: 'center' }}>
                <PsychologyIcon sx={{ fontSize: 40, color: 'secondary.main', mb: 1 }} />
                <Typography variant="h4" sx={{ fontWeight: 700, mb: 0.5 }}>
                  {MOCK_METRICS.aiServices.cacheHitRate}%
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Cache Hit Rate
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={MOCK_METRICS.aiServices.cacheHitRate}
                  color="info"
                  sx={{ mt: 1, height: 4, borderRadius: 1 }}
                />
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent sx={{ textAlign: 'center' }}>
                <StoryIcon sx={{ fontSize: 40, color: 'success.main', mb: 1 }} />
                <Typography variant="h4" sx={{ fontWeight: 700, mb: 0.5 }}>
                  {MOCK_METRICS.application.storiesGenerated24h}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Stories Today
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={(MOCK_METRICS.application.storiesGenerated24h / 10) * 100}
                  color="success"
                  sx={{ mt: 1, height: 4, borderRadius: 1 }}
                />
              </CardContent>
            </Card>
          </Grid>

          {/* Application Statistics */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                  Application Statistics
                </Typography>
                
                <List dense>
                  <ListItem>
                    <ListItemIcon>
                      <GroupIcon color="primary" />
                    </ListItemIcon>
                    <ListItemText
                      primary="Total Characters"
                      secondary={`${MOCK_METRICS.application.totalCharacters} characters created`}
                    />
                    <Typography variant="h6" color="primary">
                      {MOCK_METRICS.application.totalCharacters}
                    </Typography>
                  </ListItem>
                  
                  <ListItem>
                    <ListItemIcon>
                      <StoryIcon color="secondary" />
                    </ListItemIcon>
                    <ListItemText
                      primary="Total Stories"
                      secondary={`${MOCK_METRICS.application.totalStories} stories generated`}
                    />
                    <Typography variant="h6" color="secondary">
                      {MOCK_METRICS.application.totalStories}
                    </Typography>
                  </ListItem>
                  
                  <ListItem>
                    <ListItemIcon>
                      <MonitoringIcon color="info" />
                    </ListItemIcon>
                    <ListItemText
                      primary="Active Users"
                      secondary="Currently online users"
                    />
                    <Typography variant="h6" color="info">
                      {MOCK_METRICS.application.activeUsers}
                    </Typography>
                  </ListItem>
                </List>
              </CardContent>
            </Card>
          </Grid>

          {/* Recent Activity */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                  Recent Activity
                </Typography>
                
                <List dense>
                  {MOCK_LOGS.slice(0, 5).map((log, index) => (
                    <React.Fragment key={log.id}>
                      <ListItem>
                        <ListItemIcon>
                          {log.level === 'ERROR' ? (
                            <ErrorIcon color="error" />
                          ) : log.level === 'WARNING' ? (
                            <WarningIcon color="warning" />
                          ) : (
                            <CheckCircleIcon color="success" />
                          )}
                        </ListItemIcon>
                        <ListItemText
                          primary={log.message}
                          secondary={`${formatTimestamp(log.timestamp)} • ${log.details}`}
                        />
                      </ListItem>
                      {index < 4 && <Divider />}
                    </React.Fragment>
                  ))}
                </List>

                <Button
                  fullWidth
                  variant="outlined"
                  sx={{ mt: 2 }}
                  onClick={() => setActiveTab(3)}
                >
                  View All Logs
                </Button>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      {/* Performance Tab */}
      <TabPanel value={activeTab} index={1}>
        <Grid container spacing={3}>
          {/* API Performance */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
                  API Performance
                </Typography>

                <Box sx={{ mb: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2">Response Time</Typography>
                    <Typography variant="body2" color="primary" sx={{ fontWeight: 600 }}>
                      {MOCK_METRICS.api.responseTime}ms
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={Math.min((500 - MOCK_METRICS.api.responseTime) / 5, 100)}
                    color={getHealthColor(500 - MOCK_METRICS.api.responseTime, { good: 350, warning: 200 })}
                    sx={{ height: 8, borderRadius: 1 }}
                  />
                </Box>

                <Box sx={{ mb: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2">Requests/Second</Typography>
                    <Typography variant="body2" color="info.main" sx={{ fontWeight: 600 }}>
                      {MOCK_METRICS.api.requestsPerSecond}
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={(MOCK_METRICS.api.requestsPerSecond / 50) * 100}
                    color="info"
                    sx={{ height: 8, borderRadius: 1 }}
                  />
                </Box>

                <Box sx={{ mb: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2">Error Rate</Typography>
                    <Typography variant="body2" color="error.main" sx={{ fontWeight: 600 }}>
                      {MOCK_METRICS.api.errorRate}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={MOCK_METRICS.api.errorRate * 10}
                    color="error"
                    sx={{ height: 8, borderRadius: 1 }}
                  />
                </Box>

                <Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2">Uptime</Typography>
                    <Typography variant="body2" color="success.main" sx={{ fontWeight: 600 }}>
                      {MOCK_METRICS.api.uptime}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={MOCK_METRICS.api.uptime}
                    color="success"
                    sx={{ height: 8, borderRadius: 1 }}
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* System Resources */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
                  System Resources
                </Typography>

                <Box sx={{ mb: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <SpeedIcon sx={{ fontSize: 16 }} />
                      CPU Usage
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {MOCK_METRICS.system.cpuUsage}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={MOCK_METRICS.system.cpuUsage}
                    color={getHealthColor(100 - MOCK_METRICS.system.cpuUsage, { good: 50, warning: 20 })}
                    sx={{ height: 8, borderRadius: 1 }}
                  />
                </Box>

                <Box sx={{ mb: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <MemoryIcon sx={{ fontSize: 16 }} />
                      Memory Usage
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {MOCK_METRICS.system.memoryUsage}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={MOCK_METRICS.system.memoryUsage}
                    color={getHealthColor(100 - MOCK_METRICS.system.memoryUsage, { good: 40, warning: 20 })}
                    sx={{ height: 8, borderRadius: 1 }}
                  />
                </Box>

                <Box sx={{ mb: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <StorageIcon sx={{ fontSize: 16 }} />
                      Disk Usage
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {MOCK_METRICS.system.diskUsage}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={MOCK_METRICS.system.diskUsage}
                    color={getHealthColor(100 - MOCK_METRICS.system.diskUsage, { good: 70, warning: 10 })}
                    sx={{ height: 8, borderRadius: 1 }}
                  />
                </Box>

                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'action.hover' }}>
                      <Typography variant="body2" color="text.secondary">
                        Network In
                      </Typography>
                      <Typography variant="h6" sx={{ fontWeight: 600 }}>
                        {MOCK_METRICS.system.networkIn} MB/s
                      </Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={6}>
                    <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'action.hover' }}>
                      <Typography variant="body2" color="text.secondary">
                        Network Out
                      </Typography>
                      <Typography variant="h6" sx={{ fontWeight: 600 }}>
                        {MOCK_METRICS.system.networkOut} MB/s
                      </Typography>
                    </Paper>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      {/* AI Services Tab */}
      <TabPanel value={activeTab} index={2}>
        <Grid container spacing={3}>
          {/* Token Usage */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
                  Token Usage
                </Typography>

                <Box sx={{ mb: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2">Daily Token Usage</Typography>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {MOCK_METRICS.aiServices.tokenUsage.toLocaleString()} / {MOCK_METRICS.aiServices.tokenLimit.toLocaleString()}
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={(MOCK_METRICS.aiServices.tokenUsage / MOCK_METRICS.aiServices.tokenLimit) * 100}
                    color={getHealthColor(
                      100 - (MOCK_METRICS.aiServices.tokenUsage / MOCK_METRICS.aiServices.tokenLimit) * 100,
                      { good: 50, warning: 20 }
                    )}
                    sx={{ height: 8, borderRadius: 1 }}
                  />
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                    {((MOCK_METRICS.aiServices.tokenUsage / MOCK_METRICS.aiServices.tokenLimit) * 100).toFixed(1)}% of daily limit used
                  </Typography>
                </Box>

                <Box sx={{ mb: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2">Cache Hit Rate</Typography>
                    <Typography variant="body2" color="success.main" sx={{ fontWeight: 600 }}>
                      {MOCK_METRICS.aiServices.cacheHitRate}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={MOCK_METRICS.aiServices.cacheHitRate}
                    color="success"
                    sx={{ height: 8, borderRadius: 1 }}
                  />
                </Box>

                <Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    Average Generation Time
                  </Typography>
                  <Typography variant="h4" sx={{ fontWeight: 700, color: 'primary.main' }}>
                    {MOCK_METRICS.aiServices.averageGenerationTime}s
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* AI Service Health */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
                  AI Service Health
                </Typography>

                <List dense>
                  <ListItem>
                    <ListItemIcon>
                      <CheckCircleIcon color="success" />
                    </ListItemIcon>
                    <ListItemText
                      primary="OpenAI API"
                      secondary="Connected and operational"
                    />
                    <Chip label="Healthy" color="success" size="small" />
                  </ListItem>

                  <ListItem>
                    <ListItemIcon>
                      <CheckCircleIcon color="success" />
                    </ListItemIcon>
                    <ListItemText
                      primary="Character Agents"
                      secondary="All agents responsive"
                    />
                    <Chip label="Active" color="success" size="small" />
                  </ListItem>

                  <ListItem>
                    <ListItemIcon>
                      <CheckCircleIcon color="success" />
                    </ListItemIcon>
                    <ListItemText
                      primary="Story Generation"
                      secondary="Generation pipeline operational"
                    />
                    <Chip label="Ready" color="success" size="small" />
                  </ListItem>

                  <ListItem>
                    <ListItemIcon>
                      <WarningIcon color="warning" />
                    </ListItemIcon>
                    <ListItemText
                      primary="Rate Limiting"
                      secondary="Approaching daily limits"
                    />
                    <Chip label="Warning" color="warning" size="small" />
                  </ListItem>
                </List>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      {/* System Logs Tab */}
      <TabPanel value={activeTab} index={3}>
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                System Logs
              </Typography>
              <Button
                variant="outlined"
                startIcon={<DownloadIcon />}
                size="small"
              >
                Export Logs
              </Button>
            </Box>

            <TableContainer component={Paper} variant="outlined">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Timestamp</TableCell>
                    <TableCell>Level</TableCell>
                    <TableCell>Message</TableCell>
                    <TableCell>Details</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {MOCK_LOGS.map((log) => (
                    <TableRow key={log.id} hover>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                          {log.timestamp.toLocaleString()}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={log.level}
                          size="small"
                          color={getLogLevelColor(log.level)}
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {log.message}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {log.details}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      </TabPanel>
    </Box>
  );
}
