import React, { useState } from 'react';
import {
  Box,
  Typography,
  Stack,
  Grid,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import { styled, alpha } from '@mui/material/styles';
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
    boxShadow: `0 4px 8px ${alpha(theme.palette.primary.main, 0.2)}`,
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

type MetricName = 'LCP' | 'FID' | 'CLS' | 'FCP' | 'TTFB';
type MetricKey = keyof WebVitalsState;
type MetricRating = 'good' | 'needs-improvement' | 'poor';

type MetricsWindow = Window & { __FORCE_SHOW_METRICS__?: boolean };

const METRIC_THRESHOLDS: Record<MetricName, { good: number; ok: number }> = {
  LCP: { good: 2500, ok: 4000 },
  FID: { good: 100, ok: 300 },
  CLS: { good: 0.1, ok: 0.25 },
  FCP: { good: 1800, ok: 3000 },
  TTFB: { good: 600, ok: 1500 },
};

const MOBILE_METRICS: Array<{
  key: MetricKey;
  label: string;
  decimals: number;
  grid: number;
  metricName: MetricName;
}> = [
  { key: 'lcp', label: 'LCP', decimals: 0, grid: 6, metricName: 'LCP' },
  { key: 'fid', label: 'FID', decimals: 0, grid: 6, metricName: 'FID' },
  { key: 'cls', label: 'CLS', decimals: 3, grid: 4, metricName: 'CLS' },
  { key: 'fcp', label: 'FCP', decimals: 0, grid: 4, metricName: 'FCP' },
  { key: 'ttfb', label: 'TTFB', decimals: 0, grid: 4, metricName: 'TTFB' },
];

const DESKTOP_METRICS: Array<{
  key: MetricKey;
  label: string;
  decimals: number;
  grid: number;
  metricName: MetricName;
}> = [
  { key: 'lcp', label: 'LCP (Largest Contentful Paint)', decimals: 0, grid: 6, metricName: 'LCP' },
  { key: 'fid', label: 'FID (First Input Delay)', decimals: 0, grid: 6, metricName: 'FID' },
  { key: 'cls', label: 'CLS', decimals: 3, grid: 4, metricName: 'CLS' },
  { key: 'fcp', label: 'FCP', decimals: 0, grid: 4, metricName: 'FCP' },
  { key: 'ttfb', label: 'TTFB', decimals: 0, grid: 4, metricName: 'TTFB' },
];

const formatNumber = (num: number | undefined, decimals = 1) => {
  if (num === undefined) return '-';
  return num.toFixed(decimals);
};

const getRating = (metricName: MetricName, value: number | undefined): MetricRating => {
  if (value === undefined) return 'needs-improvement';
  const thresholds = METRIC_THRESHOLDS[metricName];
  if (value <= thresholds.good) return 'good';
  if (value <= thresholds.ok) return 'needs-improvement';
  return 'poor';
};

const getRatingColor = (rating: MetricRating, theme: ReturnType<typeof useTheme>) => {
  switch (rating) {
    case 'good':
      return theme.palette.success.main;
    case 'poor':
      return theme.palette.error.main;
    default:
      return theme.palette.warning.main;
  }
};

const MetricItem: React.FC<{
  label: string;
  value: number | undefined;
  decimals: number;
  ratingColor: string;
  variant: 'body1' | 'h6';
}> = ({ label, value, decimals, ratingColor, variant }) => (
  <MetricCard>
    <Typography variant="caption" color="text.secondary">
      {label}
    </Typography>
    <Typography
      variant={variant}
      fontWeight={600}
      data-testid="performance-metric-value"
      sx={{ color: ratingColor }}
    >
      {formatNumber(value, decimals)}{decimals === 0 ? 'ms' : ''}
    </Typography>
  </MetricCard>
);

const MetricsGrid: React.FC<{
  metrics: typeof MOBILE_METRICS;
  webVitals: WebVitalsState;
  theme: ReturnType<typeof useTheme>;
  variant: 'body1' | 'h6';
}> = ({ metrics, webVitals, theme, variant }) => (
  <Grid container spacing={1}>
    {metrics.map((metric) => (
      <Grid item xs={metric.grid} key={metric.key}>
        {(() => {
          const value = webVitals[metric.key];
          const rating = getRating(metric.metricName, value);
          return (
        <MetricItem
          label={metric.label}
          value={value}
          decimals={metric.decimals}
          ratingColor={getRatingColor(rating, theme)}
          variant={variant}
        />
          );
        })()}
      </Grid>
    ))}
  </Grid>
);

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
  const canViewMetrics = hasDevAccess ||
    (import.meta.env.VITE_SHOW_PERFORMANCE_METRICS === 'true') ||
    (window as MetricsWindow).__FORCE_SHOW_METRICS__;

  // Hide widget if user doesn't have access
  if (!canViewMetrics) {
    return null;
  }

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
            <MetricsGrid
              metrics={MOBILE_METRICS}
              webVitals={webVitals}
              theme={theme}
              variant="body1"
            />
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
            <MetricsGrid
              metrics={DESKTOP_METRICS}
              webVitals={webVitals}
              theme={theme}
              variant="h6"
            />
          </Stack>
        </Box>
      )}
    </Box>
  );
};

export default PerformanceMetrics;
