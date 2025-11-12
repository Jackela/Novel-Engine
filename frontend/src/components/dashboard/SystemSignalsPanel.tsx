import React, { useState } from 'react';
import { Box, Tabs, Tab, useTheme, useMediaQuery, Stack } from '@mui/material';
import GridTile from '../layout/GridTile';
import PerformanceMetrics, { type PerformanceMetricsProps } from './PerformanceMetrics';
import EventCascadeFlow, { type EventCascadeFlowProps } from './EventCascadeFlow';
import type { DensityMode } from '@/utils/density';

interface SystemSignalsPanelProps {
  performanceProps?: PerformanceMetricsProps;
  eventProps?: EventCascadeFlowProps;
  density?: DensityMode;
}

const SystemSignalsPanel: React.FC<SystemSignalsPanelProps> = ({ performanceProps, eventProps, density = 'relaxed' }) => {
  const theme = useTheme();
  const isDesktop = useMediaQuery(theme.breakpoints.up('lg'));
  const isTablet = useMediaQuery(theme.breakpoints.between('md', 'lg'));
  const [activeTab, setActiveTab] = useState<'performance' | 'events'>('performance');

  const renderTabs = () => (
    <Tabs
      value={activeTab}
      onChange={(_, value) => setActiveTab(value)}
      textColor="primary"
      indicatorColor="primary"
      variant="fullWidth"
      sx={{ mb: 1 }}
      aria-label="System signals tabs"
    >
      <Tab value="performance" label="Performance" />
      <Tab value="events" label="Events" />
    </Tabs>
  );

  let body: React.ReactNode;

  if (isDesktop) {
    const spacing = density === 'compact' ? 1.5 : 2;
    body = (
      <Stack direction="row" spacing={spacing} sx={{ height: '100%' }}>
        <Box flex={1} minHeight={0}>
          <PerformanceMetrics variant="embedded" {...performanceProps} />
        </Box>
        <Box flex={1} minHeight={0}>
          <EventCascadeFlow variant="embedded" {...eventProps} />
        </Box>
      </Stack>
    );
  } else if (isTablet) {
    const spacing = density === 'compact' ? 0.75 : 1;
    body = (
      <Stack spacing={spacing} sx={{ height: '100%' }}>
        <Box flex={1} minHeight={0}>
          <PerformanceMetrics variant="embedded" {...performanceProps} />
        </Box>
        <Box flex={1} minHeight={0}>
          <EventCascadeFlow variant="embedded" {...eventProps} />
        </Box>
      </Stack>
    );
  } else {
    body = (
      <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        {renderTabs()}
        <Box flex={1} minHeight={0}>
          {activeTab === 'performance' ? (
            <PerformanceMetrics variant="embedded" {...performanceProps} />
          ) : (
            <EventCascadeFlow variant="embedded" {...eventProps} />
          )}
        </Box>
      </Box>
    );
  }

  return (
    <GridTile title="System Signals" className="system-signals-panel" data-testid="system-signals-panel">
      <Box data-density={density}>{body}</Box>
    </GridTile>
  );
};

export default SystemSignalsPanel;
