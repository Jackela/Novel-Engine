import React from 'react';
import { Box, Stack, Typography, Chip, useTheme, useMediaQuery } from '@mui/material';
import { styled } from '@mui/material/styles';
import { Timeline as TimelineIcon, Bolt as BoltIcon, AutoGraph as AutoGraphIcon } from '@mui/icons-material';

type PipelineState = 'idle' | 'running' | 'paused' | 'stopped';

interface SummaryStripProps {
  lastUpdate: Date;
  pipelineStatus: PipelineState;
  isLive: boolean;
  isOnline: boolean;
  actions?: React.ReactNode;
  embedded?: boolean;
}

const SummaryContainer = styled(Box)(({ theme }) => ({
  width: '100%',
  padding: theme.spacing(3),
  borderRadius: theme.shape.borderRadius * 2,
  display: 'flex',
  flexDirection: 'column',
  gap: theme.spacing(2.5),
  minHeight: 0,
  background: theme.palette.background.paper,
  border: `1px solid ${theme.palette.divider}`,
  boxShadow: theme.shadows[1],
}));

const MetricCard = styled(Box)(({ theme }) => ({
  flex: 1,
  minWidth: 180,
  borderRadius: theme.shape.borderRadius,
  padding: theme.spacing(2.5),
  display: 'flex',
  flexDirection: 'column',
  gap: theme.spacing(1.5),
  minHeight: 110,
  background: theme.palette.background.default,
  border: `1px solid ${theme.palette.divider}`,
  transition: 'all 0.2s ease-in-out',
  '&:hover': {
    transform: 'translateY(-2px)',
    backgroundColor: theme.palette.background.paper,
  },
}));

const statusLabelMap: Record<PipelineState, string> = {
  running: 'Running',
  paused: 'Paused',
  stopped: 'Stopped',
  idle: 'Idle',
};

const SummaryHeader: React.FC<{ isLive: boolean; isOnline: boolean }> = ({ isLive, isOnline }) => (
  <Stack direction="row" spacing={1} alignItems="center" sx={{ flexShrink: 0 }}>
    <Typography variant="subtitle2" fontWeight={700}>
      Command Overview
    </Typography>
    <Chip
      label={isLive ? 'LIVE' : isOnline ? 'ONLINE' : 'OFFLINE'}
      color={isLive ? 'success' : isOnline ? 'default' : 'error'}
      size="small"
      sx={{ fontWeight: 700, letterSpacing: '0.05em' }}
    />
  </Stack>
);

const SummaryMetric: React.FC<{
  label: string;
  value: string;
  caption: string;
  icon: React.ReactNode;
}> = ({ label, value, caption, icon }) => (
  <MetricCard>
    <Stack direction="row" spacing={1} alignItems="center">
      {icon}
      <Typography variant="caption" color="text.secondary" textTransform="uppercase" fontWeight={600}>
        {label}
      </Typography>
    </Stack>
    <Typography variant="h6" fontWeight={700}>
      {value}
    </Typography>
    <Typography variant="caption" color="text.secondary">
      {caption}
    </Typography>
  </MetricCard>
);

const SummaryMetrics: React.FC<{
  isTablet: boolean;
  items: Array<{ label: string; value: string; caption: string; icon: React.ReactNode }>;
  isLive: boolean;
  isOnline: boolean;
}> = ({ isTablet, items, isLive, isOnline }) => (
  <Stack
    direction={isTablet ? 'column' : 'row'}
    spacing={1.25}
    justifyContent="space-between"
    alignItems={isTablet ? 'flex-start' : 'center'}
    sx={{ minWidth: 0 }}
  >
    <SummaryHeader isLive={isLive} isOnline={isOnline} />
    <Stack
      direction="row"
      spacing={1}
      sx={{
        width: '100%',
        flexWrap: 'wrap',
        minWidth: 0,
        '& > *': { flex: '1 1 0', minWidth: 160 },
      }}
    >
      {items.map((item) => (
        <SummaryMetric key={item.label} {...item} />
      ))}
    </Stack>
  </Stack>
);

const SummaryStrip: React.FC<SummaryStripProps> = ({
  lastUpdate,
  pipelineStatus,
  isLive,
  isOnline,
  actions,
  embedded = false,
}) => {
  const theme = useTheme();
  const isTablet = useMediaQuery(theme.breakpoints.between('md', 'lg'));
  const hasActions = Boolean(actions);

  const statusLabel = statusLabelMap[pipelineStatus] ?? 'Idle';

  const summaryItems = [
    {
      label: 'Run State',
      value: isOnline ? statusLabel : 'Offline',
      caption: isLive ? 'Live orchestration' : isOnline ? 'Standing by' : 'Connection lost',
      icon: <BoltIcon fontSize="small" color="primary" />,
    },
    {
      label: 'Activity Stream',
      value: isLive ? 'High' : 'Moderate',
      caption: 'Realtime events per minute',
      icon: <TimelineIcon fontSize="small" color="secondary" />,
    },
    {
      label: 'Last Sync',
      value: lastUpdate.toLocaleTimeString(),
      caption: 'Auto refresh every 10s',
      icon: <AutoGraphIcon fontSize="small" color="success" />,
    },
  ];

  const containerProps = {
    elevation: embedded ? 0 : 1,
    'data-testid': 'summary-strip',
    sx: hasActions
      ? {
          display: 'grid',
          gridTemplateColumns: {
            lg: 'minmax(0, 3fr) minmax(280px, auto)',
            md: '1fr',
          },
          alignItems: 'stretch',
          gap: 2,
          maxHeight: { lg: 180, md: 'none' },
          overflow: 'hidden',
        }
      : {},
  } as const;

  return (
    <SummaryContainer {...containerProps}>
      <SummaryMetrics
        isTablet={isTablet}
        items={summaryItems}
        isLive={isLive}
        isOnline={isOnline}
      />
      {hasActions && (
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            minWidth: 0,
          }}
        >
          {actions}
        </Box>
      )}
    </SummaryContainer>
  );
};

export default SummaryStrip;
