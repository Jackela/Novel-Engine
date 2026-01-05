import React, { useState } from 'react';
import {
  Box,
  Typography,
  Stack,
  Grid,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { motion } from 'framer-motion';
// Removed unused imports: PerformanceIcon, MemoryIcon, StorageIcon, NetworkIcon, StatusIcon
import { usePerformance, type PerformanceMetric } from '@/hooks/usePerformance';

// Try importing useAuth - may not be available yet
let useAuth: (() => { user: { roles: string[] } | null }) | undefined;
try {
  const authModule = require('@/hooks/useAuth');
  useAuth = authModule.useAuth;
} catch {
  // useAuth not available, will fall back to env var
}

const MetricCard = styled(motion.div)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  borderRadius: theme.shape.borderRadius,
  backgroundColor: theme.palette.background.paper,
  border: `1px solid ${theme.palette.divider}`,
  transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
  '&:hover': {
    borderColor: theme.palette.primary.main,
    backgroundColor: 'var(--color-bg-tertiary)',
    transform: 'translateY(-2px)',
    boxShadow: '0 4px 8px rgba(99, 102, 241, 0.2)',
  },

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

// Removed unused styled components: StatusIndicator, AnimatedProgress

interface WebVitalsState {
  lcp?: number;
  fid?: number;
  cls?: number;
  fcp?: number;
  ttfb?: number;
}

interface PerformanceMetricsProps {
  loading?: boolean;
  error?: boolean;
  sourceLabel?: string;
}

const PerformanceMetrics: React.FC<PerformanceMetricsProps> = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  // Track Web Vitals - hooks must be called unconditionally before any returns
  const [webVitals, setWebVitals] = useState<WebVitalsState>({});

  usePerformance({
    onMetric: (metric: PerformanceMetric) => {
      // Update Web Vitals state when metrics are reported
      setWebVitals((prev) => ({
        ...prev,
        [metric.name.toLowerCase()]: metric.value,
      }));
    },
  });

  // RBAC: Check if user has developer or admin role
  const authResult = useAuth?.();
  const hasDevAccess = authResult?.user?.roles?.includes('developer') ||
    authResult?.user?.roles?.includes('admin');

  // Prefer real RBAC if available, otherwise allow opt-in via env flag or test override
  const canViewMetrics = hasDevAccess || (import.meta.env.VITE_SHOW_PERFORMANCE_METRICS === 'true') || (window as any).__FORCE_SHOW_METRICS__;

  // Hide widget if user doesn't have access
  if (!canViewMetrics) {
    return null;
  }

  const formatNumber = (num: number | undefined, decimals = 1) => {
    if (num === undefined) return '-';
    return num.toFixed(decimals);
  };

  const getRating = (metricName: string, value: number | undefined): 'good' | 'needs-improvement' | 'poor' => {
    if (value === undefined) return 'needs-improvement';

    switch (metricName) {
      case 'LCP':
        return value <= 2500 ? 'good' : value <= 4000 ? 'needs-improvement' : 'poor';
      case 'FID':
        return value <= 100 ? 'good' : value <= 300 ? 'needs-improvement' : 'poor';
      case 'CLS':
        return value <= 0.1 ? 'good' : value <= 0.25 ? 'needs-improvement' : 'poor';
      case 'FCP':
        return value <= 1800 ? 'good' : value <= 3000 ? 'needs-improvement' : 'poor';
      case 'TTFB':
        return value <= 600 ? 'good' : value <= 1500 ? 'needs-improvement' : 'poor';
      default:
        return 'needs-improvement';
    }
  };

  const getRatingColor = (rating: 'good' | 'needs-improvement' | 'poor') => {
    switch (rating) {
      case 'good':
        return theme.palette.success.main;
      case 'poor':
        return theme.palette.error.main;
      default:
        return theme.palette.warning.main;
    }
  };

  return (

    <Box sx={{ height: '100%', overflow: 'hidden' }} className="h-full" data-testid="performance-metrics">
      {isMobile ? (
        // Mobile: Web Vitals display
        <Box sx={{ height: '100%' }}>
          <Stack spacing={1}>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5 }}>
              Core Web Vitals
            </Typography>

            {/* Web Vitals Grid */}
            <Grid container spacing={1}>
              <Grid item xs={6}>
                <MetricCard>
                  <Typography variant="caption" color="text.secondary">
                    LCP
                  </Typography>
                  <Typography
                    variant="body1"
                    fontWeight={600}
                    data-testid="performance-metric-value"
                    sx={{ color: getRatingColor(getRating('LCP', webVitals.lcp)) }}
                  >
                    {formatNumber(webVitals.lcp, 0)}ms
                  </Typography>
                </MetricCard>
              </Grid>
              <Grid item xs={6}>
                <MetricCard>
                  <Typography variant="caption" color="text.secondary">
                    FID
                  </Typography>
                  <Typography
                    variant="body1"
                    fontWeight={600}
                    data-testid="performance-metric-value"
                    sx={{ color: getRatingColor(getRating('FID', webVitals.fid)) }}
                  >
                    {formatNumber(webVitals.fid, 0)}ms
                  </Typography>
                </MetricCard>
              </Grid>
              <Grid item xs={4}>
                <MetricCard>
                  <Typography variant="caption" color="text.secondary">
                    CLS
                  </Typography>
                  <Typography
                    variant="body1"
                    fontWeight={600}
                    data-testid="performance-metric-value"
                    sx={{ color: getRatingColor(getRating('CLS', webVitals.cls)) }}
                  >
                    {formatNumber(webVitals.cls, 3)}
                  </Typography>
                </MetricCard>
              </Grid>
              <Grid item xs={4}>
                <MetricCard>
                  <Typography variant="caption" color="text.secondary">
                    FCP
                  </Typography>
                  <Typography
                    variant="body1"
                    fontWeight={600}
                    data-testid="performance-metric-value"
                    sx={{ color: getRatingColor(getRating('FCP', webVitals.fcp)) }}
                  >
                    {formatNumber(webVitals.fcp, 0)}ms
                  </Typography>
                </MetricCard>
              </Grid>
              <Grid item xs={4}>
                <MetricCard>
                  <Typography variant="caption" color="text.secondary">
                    TTFB
                  </Typography>
                  <Typography
                    variant="body1"
                    fontWeight={600}
                    data-testid="performance-metric-value"
                    sx={{ color: getRatingColor(getRating('TTFB', webVitals.ttfb)) }}
                  >
                    {formatNumber(webVitals.ttfb, 0)}ms
                  </Typography>
                </MetricCard>
              </Grid>
            </Grid>
          </Stack>
        </Box>
      ) : (
        // Desktop: Web Vitals display
        <Box sx={{ height: '100%' }}>
          <Stack spacing={1.5}>
            <Typography variant="caption" color="text.secondary">
              Core Web Vitals
            </Typography>

            {/* Web Vitals Grid */}
            <Grid container spacing={1}>
              <Grid item xs={6}>
                <MetricCard>
                  <Typography variant="caption" color="text.secondary">
                    LCP (Largest Contentful Paint)
                  </Typography>
                  <Typography
                    variant="h6"
                    fontWeight={600}
                    data-testid="performance-metric-value"
                    sx={{ color: getRatingColor(getRating('LCP', webVitals.lcp)) }}
                  >
                    {formatNumber(webVitals.lcp, 0)}ms
                  </Typography>
                </MetricCard>
              </Grid>

              <Grid item xs={6}>
                <MetricCard>
                  <Typography variant="caption" color="text.secondary">
                    FID (First Input Delay)
                  </Typography>
                  <Typography
                    variant="h6"
                    fontWeight={600}
                    data-testid="performance-metric-value"
                    sx={{ color: getRatingColor(getRating('FID', webVitals.fid)) }}
                  >
                    {formatNumber(webVitals.fid, 0)}ms
                  </Typography>
                </MetricCard>
              </Grid>

              <Grid item xs={4}>
                <MetricCard>
                  <Typography variant="caption" color="text.secondary">
                    CLS
                  </Typography>
                  <Typography
                    variant="h6"
                    fontWeight={600}
                    data-testid="performance-metric-value"
                    sx={{ color: getRatingColor(getRating('CLS', webVitals.cls)) }}
                  >
                    {formatNumber(webVitals.cls, 3)}
                  </Typography>
                </MetricCard>
              </Grid>

              <Grid item xs={4}>
                <MetricCard>
                  <Typography variant="caption" color="text.secondary">
                    FCP
                  </Typography>
                  <Typography
                    variant="h6"
                    fontWeight={600}
                    data-testid="performance-metric-value"
                    sx={{ color: getRatingColor(getRating('FCP', webVitals.fcp)) }}
                  >
                    {formatNumber(webVitals.fcp, 0)}ms
                  </Typography>
                </MetricCard>
              </Grid>

              <Grid item xs={4}>
                <MetricCard>
                  <Typography variant="caption" color="text.secondary">
                    TTFB
                  </Typography>
                  <Typography
                    variant="h6"
                    fontWeight={600}
                    data-testid="performance-metric-value"
                    sx={{ color: getRatingColor(getRating('TTFB', webVitals.ttfb)) }}
                  >
                    {formatNumber(webVitals.ttfb, 0)}ms
                  </Typography>
                </MetricCard>
              </Grid>
            </Grid>
          </Stack>
        </Box>
      )}
    </Box>
  );
};

export default PerformanceMetrics;
