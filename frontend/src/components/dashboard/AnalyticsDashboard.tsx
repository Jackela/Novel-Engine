import React, { useState } from 'react';
import { 
  Box, 
  Typography, 
  Chip, 
  Stack, 
  Collapse, 
  IconButton,
  Grid,
  useTheme,
  useMediaQuery 
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { 
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon 
} from '@mui/icons-material';
import GridTile from '../layout/GridTile';

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

const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({ loading, error }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [expanded, setExpanded] = useState(false);

  const handleToggle = () => {
    setExpanded(!expanded);
  };

  const getGridPosition = () => {
    if (expanded) {
      return {
        desktop: { column: '1 / 13', height: '400px' },
        tablet: { column: '1 / 9', height: '360px' },
        mobile: { height: '300px' },
      };
    } else {
      return {
        desktop: { column: '1 / 13', height: '60px' },
        tablet: { column: '1 / 9', height: '60px' },
        mobile: { height: '100px' }, // Increased for mobile visibility
      };
    }
  };

  return (
    <GridTile
      title="Analytics"
      position={getGridPosition()}
      loading={loading}
      error={error}
      onMenuClick={handleToggle}
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
          <CollapsedView>
            {isMobile ? (
              // Mobile: Stacked metrics
              <Stack spacing={0.5} alignItems="center">
                <Typography variant="body2" color="text.secondary">
                  Quality: 8.3/10 • Engagement: 92%
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Coherence: 94% • 47 data points tracked
                </Typography>
              </Stack>
            ) : (
              // Desktop: Horizontal metrics
              <Stack direction="row" spacing={2} alignItems="center">
                <Typography variant="body2" color="text.secondary">
                  Story Quality: 8.3/10
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  •
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Engagement: 92%
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  •
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Coherence: 94%
                </Typography>
              </Stack>
            )}
          </CollapsedView>
        ) : (
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
                    <Typography variant="h4" color="primary">
                      8.3
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Story Quality
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="success.main">
                      92%
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Engagement
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="info.main">
                      94%
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Coherence
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="warning.main">
                      7.8
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Complexity
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
              
              <Stack direction="row" spacing={1} justifyContent="center" sx={{ mt: 3 }}>
                <Chip label="47 Data Points" size="small" variant="outlined" />
                <Chip label="5 Metrics Tracked" size="small" variant="outlined" />
                <Chip label="Real-time Analysis" size="small" variant="outlined" />
              </Stack>
            </PlaceholderContent>
          </ExpandedView>
        )}
      </AnalyticsContainer>
    </GridTile>
  );
};

export default AnalyticsDashboard;
