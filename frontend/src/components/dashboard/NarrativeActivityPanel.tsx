import React, { useState } from 'react';
import { Box, Tabs, Tab, useTheme, useMediaQuery, Stack } from '@mui/material';
import GridTile from '../layout/GridTile';
import type { DensityMode } from '@/utils/density';
import NarrativeTimeline, { type NarrativeTimelineProps } from './NarrativeTimeline';
import RealTimeActivity, { type RealTimeActivityProps } from './RealTimeActivity';

interface NarrativeActivityPanelProps {
  timelineProps?: NarrativeTimelineProps;
  activityProps?: RealTimeActivityProps;
  density?: DensityMode;
}

const NarrativeActivityPanel: React.FC<NarrativeActivityPanelProps> = ({ timelineProps, activityProps, density = 'relaxed' }) => {
  const theme = useTheme();
  const isDesktop = useMediaQuery(theme.breakpoints.up('lg'));
  const isTablet = useMediaQuery(theme.breakpoints.between('md', 'lg'));
  const [activeTab, setActiveTab] = useState<'timeline' | 'activity'>('timeline');

  const renderTabs = () => (
    <Tabs
      value={activeTab}
      onChange={(_, value) => setActiveTab(value)}
      textColor="primary"
      indicatorColor="primary"
      variant="fullWidth"
      sx={{ mb: 1 }}
      aria-label="Narrative and activity tabs"
    >
      <Tab value="timeline" label="Narrative" />
      <Tab value="activity" label="Activity" />
    </Tabs>
  );

  let body: React.ReactNode;

  if (isDesktop) {
    const spacing = density === 'compact' ? 1.5 : 2;
    body = (
      <Stack direction="row" spacing={spacing} sx={{ height: '100%' }}>
        <Box flex={1} minHeight={0}>
          <NarrativeTimeline variant="embedded" {...timelineProps} />
        </Box>
        <Box flex={1} minHeight={0}>
          <RealTimeActivity variant="embedded" density={density} {...activityProps} />
        </Box>
      </Stack>
    );
  } else if (isTablet) {
    const spacing = density === 'compact' ? 0.75 : 1;
    body = (
      <Stack spacing={spacing} sx={{ height: '100%' }}>
        <Box flex={1} minHeight={0}>
          <NarrativeTimeline variant="embedded" {...timelineProps} />
        </Box>
        <Box flex={1} minHeight={0}>
          <RealTimeActivity variant="embedded" density={density} {...activityProps} />
        </Box>
      </Stack>
    );
  } else {
    body = (
      <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        {renderTabs()}
        <Box flex={1} minHeight={0}>
          {activeTab === 'timeline' ? (
            <NarrativeTimeline variant="embedded" {...timelineProps} />
          ) : (
            <RealTimeActivity variant="embedded" density={density} {...activityProps} />
          )}
        </Box>
      </Box>
    );
  }

  return (
    <GridTile title="Narrative & Activity" className="narrative-activity-panel" data-testid="narrative-activity-panel">
      <Box data-density={density}>{body}</Box>
    </GridTile>
  );
};

export default NarrativeActivityPanel;
