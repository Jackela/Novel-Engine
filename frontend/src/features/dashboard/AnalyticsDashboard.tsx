import React, { useState } from 'react';
import {
  Box,
  Typography,
  Chip,
  Stack,
  IconButton,
  Grid,
  useTheme,
  useMediaQuery
} from '@mui/material';
import { styled } from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon
} from '@mui/icons-material';
import { useSelector } from 'react-redux';
import type { RootState } from '@/store/store';
import GridTile from '@/components/layout/GridTile';

const AnalyticsContainer = styled(Box)({
  width: '100%',
  height: '100%',
  position: 'relative',
});

const ExpandButton = styled(IconButton)(({ theme }) => ({
  position: 'absolute',
  top: theme.spacing(1),
  right: theme.spacing(1),
  zIndex: 10,
}));

const PlaceholderContent = styled(Box)(({ theme }) => ({
  textAlign: 'center',
  padding: theme.spacing(2),
}));

const CollapsedView = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  height: '60px',
  padding: theme.spacing(1, 2),
}));

const ExpandedView = styled(Box)(({ theme }) => ({
  padding: theme.spacing(2),
  height: 'calc(100% - 40px)',
  overflowY: 'auto',
}));

interface AnalyticsDashboardProps {
  loading?: boolean;
  error?: boolean;
}

const AnalyticsCollapsed: React.FC<{
  isMobile: boolean;
  analytics: RootState['dashboard']['analytics'];
}> = ({ isMobile, analytics }) => (
  <CollapsedView>
    {isMobile ? (
      <Stack spacing={0.5} alignItems="center">
        <Typography variant="body2" color="text.secondary">
          Quality: {analytics.storyQuality.toFixed(1)}/10 • Engagement: {analytics.engagement.toFixed(0)}%
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Coherence: {analytics.coherence.toFixed(0)}% • {analytics.dataPoints} data points tracked
        </Typography>
      </Stack>
    ) : (
      <Stack direction="row" spacing={2} alignItems="center">
        <Typography variant="body2" color="text.secondary">
          Story Quality: <span style={{ color: 'var(--color-primary)' }}>{analytics.storyQuality.toFixed(1)}</span>/10
        </Typography>
        <Typography variant="body2" color="text.secondary">
          •
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Engagement: <span style={{ color: 'var(--color-success)' }}>{analytics.engagement.toFixed(0)}%</span>
        </Typography>
        <Typography variant="body2" color="text.secondary">
          •
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Coherence: <span style={{ color: 'var(--color-info)' }}>{analytics.coherence.toFixed(0)}%</span>
        </Typography>
      </Stack>
    )}
  </CollapsedView>
);

const AnalyticsExpanded: React.FC<{ analytics: RootState['dashboard']['analytics'] }> = ({ analytics }) => (
  <ExpandedView>
    <PlaceholderContent>
      <Typography variant="h6" color="text.secondary" gutterBottom>
        Comprehensive Analytics
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Detailed analytics including story quality metrics, character development tracking,
        thematic consistency analysis, and player engagement measurements.
      </Typography>

      <Grid container spacing={2} sx={{ mt: 2 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Box textAlign="center">
            <Typography variant="h4" sx={{ color: 'var(--color-primary)' }}>
              {analytics.storyQuality.toFixed(1)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Story Quality
            </Typography>
          </Box>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Box textAlign="center">
            <Typography variant="h4" sx={{ color: 'var(--color-success)' }}>
              {analytics.engagement.toFixed(0)}%
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Engagement
            </Typography>
          </Box>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Box textAlign="center">
            <Typography variant="h4" sx={{ color: 'var(--color-info)' }}>
              {analytics.coherence.toFixed(0)}%
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Coherence
            </Typography>
          </Box>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Box textAlign="center">
            <Typography variant="h4" sx={{ color: 'var(--color-warning)' }}>
              {analytics.complexity.toFixed(1)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Complexity
            </Typography>
          </Box>
        </Grid>
      </Grid>

      <Stack direction="row" spacing={1} justifyContent="center" sx={{ mt: 3 }}>
        <Chip label={`${analytics.dataPoints} Data Points`} size="small" variant="outlined" />
        <Chip label={`${analytics.metricsTracked} Metrics Tracked`} size="small" variant="outlined" />
        <Chip
          label={analytics.status === 'active' ? 'Real-time Analysis' : 'Analysis Idle'}
          size="small"
          variant="outlined"
        />
      </Stack>
    </PlaceholderContent>
  </ExpandedView>
);

const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({ loading, error }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [expanded, setExpanded] = useState(false);

  // Get analytics data from Redux store
  const analytics = useSelector((state: RootState) => state.dashboard.analytics);

  const handleToggle = () => {
    setExpanded(!expanded);
  };

  return (
    <GridTile
      title="Analytics"
      loading={loading}
      error={error}
      onMenuClick={handleToggle}
      className="h-full" // Ensure it takes full height of its container
    >
      <AnalyticsContainer>
        <ExpandButton
          onClick={handleToggle}
          size="small"
          aria-label={expanded ? 'Collapse analytics panel' : 'Expand analytics panel'}
        >
          {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
        </ExpandButton>

        {!expanded ? (
          <AnalyticsCollapsed isMobile={isMobile} analytics={analytics} />
        ) : (
          <AnalyticsExpanded analytics={analytics} />
        )}
      </AnalyticsContainer>
    </GridTile>
  );
};

export default AnalyticsDashboard;
