import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Stack, 
  Chip, 
  LinearProgress, 
  Grid, 
  CircularProgress,
  useTheme,
  useMediaQuery 
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  Speed as PerformanceIcon,
  Memory as MemoryIcon,
  Storage as StorageIcon,
  NetworkCheck as NetworkIcon,
  Circle as StatusIcon,
} from '@mui/icons-material';
import GridTile from '../layout/GridTile';

const MetricCard = styled(Box)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  borderRadius: theme.spacing(1),
  backgroundColor: theme.palette.action.hover,
  
  // Mobile: more compact layout
  [theme.breakpoints.down('md')]: {
    padding: theme.spacing(0.75),
    minHeight: '50px',
  },
  
  // Desktop: standard layout
  [theme.breakpoints.up('md')]: {
    padding: theme.spacing(1),
    minHeight: '60px',
  },
}));

const StatusIndicator = styled(Box)<{ status: 'healthy' | 'warning' | 'error' }>(
  ({ theme, status }) => ({
    display: 'flex',
    alignItems: 'center',
    gap: theme.spacing(0.5),
    '& .MuiSvgIcon-root': {
      fontSize: '12px',
      color: status === 'healthy' 
        ? theme.palette.success.main 
        : status === 'warning' 
        ? theme.palette.warning.main 
        : theme.palette.error.main,
    },
  })
);

interface PerformanceData {
  responseTime: number;
  errorRate: number;
  requestsPerSecond: number;
  activeUsers: number;
  systemLoad: number;
  memoryUsage: number;
  storageUsage: number;
  networkLatency: number;
}

interface SystemStatus {
  overall: 'healthy' | 'warning' | 'error';
  database: 'healthy' | 'warning' | 'error';
  aiService: 'healthy' | 'warning' | 'error';
  memoryService: 'healthy' | 'warning' | 'error';
}

interface PerformanceMetricsProps {
  loading?: boolean;
  error?: boolean;
}

const PerformanceMetrics: React.FC<PerformanceMetricsProps> = ({ loading, error }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [metrics, setMetrics] = useState<PerformanceData>({
    responseTime: 145,
    errorRate: 0.2,
    requestsPerSecond: 23.5,
    activeUsers: 127,
    systemLoad: 68,
    memoryUsage: 74,
    storageUsage: 42,
    networkLatency: 12,
  });

  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    overall: 'healthy',
    database: 'healthy',
    aiService: 'warning',
    memoryService: 'healthy',
  });

  // Simulate real-time metric updates
  useEffect(() => {
    const interval = setInterval(() => {
      setMetrics(prev => ({
        responseTime: Math.max(50, prev.responseTime + (Math.random() - 0.5) * 20),
        errorRate: Math.max(0, Math.min(5, prev.errorRate + (Math.random() - 0.5) * 0.2)),
        requestsPerSecond: Math.max(0, prev.requestsPerSecond + (Math.random() - 0.5) * 5),
        activeUsers: Math.max(0, prev.activeUsers + Math.floor((Math.random() - 0.5) * 10)),
        systemLoad: Math.max(0, Math.min(100, prev.systemLoad + (Math.random() - 0.5) * 10)),
        memoryUsage: Math.max(0, Math.min(100, prev.memoryUsage + (Math.random() - 0.5) * 5)),
        storageUsage: Math.max(0, Math.min(100, prev.storageUsage + (Math.random() - 0.5) * 2)),
        networkLatency: Math.max(1, prev.networkLatency + (Math.random() - 0.5) * 5),
      }));

      // Update system status based on metrics
      setSystemStatus(prev => {
        const newStatus = { ...prev };
        
        if (metrics.systemLoad > 90 || metrics.errorRate > 2) {
          newStatus.overall = 'error';
        } else if (metrics.systemLoad > 70 || metrics.errorRate > 1) {
          newStatus.overall = 'warning';
        } else {
          newStatus.overall = 'healthy';
        }

        if (metrics.responseTime > 200) {
          newStatus.aiService = 'warning';
        } else if (metrics.responseTime > 300) {
          newStatus.aiService = 'error';
        } else {
          newStatus.aiService = 'healthy';
        }

        return newStatus;
      });
    }, 3000);

    return () => clearInterval(interval);
  }, [metrics.systemLoad, metrics.errorRate, metrics.responseTime]);

  const getStatusColor = (status: 'healthy' | 'warning' | 'error') => {
    switch (status) {
      case 'healthy':
        return theme.palette.success.main;
      case 'warning':
        return theme.palette.warning.main;
      case 'error':
        return theme.palette.error.main;
    }
  };

  const formatNumber = (num: number, decimals = 1) => {
    return num.toFixed(decimals);
  };

  return (
    <GridTile
      title="Performance"
      data-testid="performance-metrics"
      position={{
        desktop: { column: '12 / 13', height: '160px' },
        tablet: { column: '8 / 9', height: '150px' },
        mobile: { height: '200px' },
      }}
      loading={loading}
      error={error}
    >
      {isMobile ? (
        // Mobile: Condensed critical metrics
        <Box sx={{ height: '100%' }}>
          <Stack spacing={1}>
            {/* Status and Users */}
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <StatusIndicator status={systemStatus.overall}>
                <StatusIcon />
                <Typography variant="caption" fontWeight={500}>
                  System {systemStatus.overall}
                </Typography>
              </StatusIndicator>
              <Chip
                label={`${metrics.activeUsers} users`}
                size="small"
                variant="outlined"
                color="primary"
              />
            </Box>

            {/* Essential Metrics Row */}
            <Grid container spacing={1}>
              <Grid item xs={6}>
                <MetricCard>
                  <Typography variant="caption" color="text.secondary">
                    Response
                  </Typography>
                  <Typography variant="body1" fontWeight={600}>
                    {formatNumber(metrics.responseTime, 0)}ms
                  </Typography>
                </MetricCard>
              </Grid>
              <Grid item xs={6}>
                <MetricCard>
                  <Typography variant="caption" color="text.secondary">
                    Load
                  </Typography>
                  <Box sx={{ width: '100%', mt: 0.25 }}>
                    <LinearProgress
                      variant="determinate"
                      value={metrics.systemLoad}
                      sx={{ height: 4, borderRadius: 2 }}
                      color={metrics.systemLoad > 80 ? 'warning' : 'primary'}
                    />
                    <Typography variant="caption" color="text.secondary">
                      {formatNumber(metrics.systemLoad, 0)}%
                    </Typography>
                  </Box>
                </MetricCard>
              </Grid>
            </Grid>

            {/* Secondary Metrics */}
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Typography variant="caption" color="text.secondary">
                Memory: {formatNumber(metrics.memoryUsage, 0)}% • RPS: {formatNumber(metrics.requestsPerSecond, 1)}
              </Typography>
            </Box>

            {/* Error Rate */}
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Typography variant="caption" color="text.secondary">
                Error Rate
              </Typography>
              <Typography 
                variant="caption" 
                fontWeight={500}
                color={metrics.errorRate > 1 ? 'error.main' : 'success.main'}
              >
                {formatNumber(metrics.errorRate, 2)}%
              </Typography>
            </Box>
          </Stack>
        </Box>
      ) : (
        // Desktop: Full metrics layout
        <Box sx={{ height: '100%' }}>
          <Stack spacing={1.5}>
            {/* Overall Status */}
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <StatusIndicator status={systemStatus.overall}>
                <StatusIcon />
                <Typography variant="caption" fontWeight={500}>
                  System {systemStatus.overall}
                </Typography>
              </StatusIndicator>
              <Chip
                label={`${metrics.activeUsers} users`}
                size="small"
                variant="outlined"
                color="primary"
              />
            </Box>

            {/* Key Metrics Grid */}
            <Grid container spacing={1}>
              <Grid item xs={6}>
                <MetricCard>
                  <Stack direction="row" alignItems="center" spacing={0.5}>
                    <PerformanceIcon fontSize="small" />
                    <Typography variant="caption" color="text.secondary">
                      Response
                    </Typography>
                  </Stack>
                  <Typography variant="h6" fontWeight={600}>
                    {formatNumber(metrics.responseTime, 0)}ms
                  </Typography>
                </MetricCard>
              </Grid>
              
              <Grid item xs={6}>
                <MetricCard>
                  <Stack direction="row" alignItems="center" spacing={0.5}>
                    <NetworkIcon fontSize="small" />
                    <Typography variant="caption" color="text.secondary">
                      RPS
                    </Typography>
                  </Stack>
                  <Typography variant="h6" fontWeight={600}>
                    {formatNumber(metrics.requestsPerSecond)}
                  </Typography>
                </MetricCard>
              </Grid>

              <Grid item xs={6}>
                <MetricCard>
                  <Stack direction="row" alignItems="center" spacing={0.5}>
                    <MemoryIcon fontSize="small" />
                    <Typography variant="caption" color="text.secondary">
                      Memory
                    </Typography>
                  </Stack>
                  <Box sx={{ width: '100%', mt: 0.5 }}>
                    <LinearProgress
                      variant="determinate"
                      value={metrics.memoryUsage}
                      sx={{ height: 4, borderRadius: 2 }}
                      color={metrics.memoryUsage > 80 ? 'error' : 'primary'}
                    />
                    <Typography variant="caption" color="text.secondary">
                      {formatNumber(metrics.memoryUsage, 0)}%
                    </Typography>
                  </Box>
                </MetricCard>
              </Grid>

              <Grid item xs={6}>
                <MetricCard>
                  <Stack direction="row" alignItems="center" spacing={0.5}>
                    <StorageIcon fontSize="small" />
                    <Typography variant="caption" color="text.secondary">
                      Load
                    </Typography>
                  </Stack>
                  <Box sx={{ width: '100%', mt: 0.5 }}>
                    <LinearProgress
                      variant="determinate"
                      value={metrics.systemLoad}
                      sx={{ height: 4, borderRadius: 2 }}
                      color={metrics.systemLoad > 80 ? 'warning' : 'primary'}
                    />
                    <Typography variant="caption" color="text.secondary">
                      {formatNumber(metrics.systemLoad, 0)}%
                    </Typography>
                  </Box>
                </MetricCard>
              </Grid>
            </Grid>

            {/* Error Rate Indicator */}
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Typography variant="caption" color="text.secondary">
                Error Rate
              </Typography>
              <Typography 
                variant="caption" 
                fontWeight={500}
                color={metrics.errorRate > 1 ? 'error.main' : 'success.main'}
              >
                {formatNumber(metrics.errorRate, 2)}%
              </Typography>
            </Box>
          </Stack>
        </Box>
      )}
    </GridTile>
  );
};

export default PerformanceMetrics;