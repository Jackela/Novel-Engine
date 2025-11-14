import React from 'react';
import { Box, Paper, Stack, Typography, Chip, useTheme, useMediaQuery } from '@mui/material';
import { styled } from '@mui/material/styles';
import { Timeline as TimelineIcon, Bolt as BoltIcon, AutoGraph as AutoGraphIcon } from '@mui/icons-material';

type PipelineState = 'idle' | 'running' | 'paused' | 'stopped';

interface SummaryStripProps {
  lastUpdate: Date;
  pipelineStatus: PipelineState;
  isLive: boolean;
  isOnline: boolean;
}

const SummaryContainer = styled(Paper)(({ theme }) => ({
  width: '100%',
  padding: theme.spacing(2),
  border: `1px solid ${theme.palette.divider}`,
  borderRadius: theme.shape.borderRadius * 1.5,
  backgroundColor: theme.palette.background.paper,
}));

const MetricCard = styled(Box)(({ theme }) => ({
  flex: 1,
  minWidth: 180,
  borderRadius: theme.shape.borderRadius,
  border: `1px solid ${theme.palette.divider}`,
  padding: theme.spacing(1.5),
  display: 'flex',
  flexDirection: 'column',
  gap: theme.spacing(1),
}));

const SummaryStrip: React.FC<SummaryStripProps> = ({ lastUpdate, pipelineStatus, isLive, isOnline }) => {
  const theme = useTheme();
  const isTablet = useMediaQuery(theme.breakpoints.between('md', 'lg'));

  const statusLabel = (() => {
    switch (pipelineStatus) {
      case 'running':
        return 'Running';
      case 'paused':
        return 'Paused';
      case 'stopped':
        return 'Stopped';
      default:
        return 'Idle';
    }
  })();

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

  return (
    <SummaryContainer elevation={0} data-testid="summary-strip">
      <Stack
        direction={isTablet ? 'column' : 'row'}
        spacing={1.5}
        justifyContent="space-between"
        alignItems={isTablet ? 'stretch' : 'center'}
      >
        <Stack direction="row" spacing={1} alignItems="center">
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
        <Stack
          direction={isTablet ? 'column' : 'row'}
          spacing={1}
          sx={{ width: '100%', flexWrap: 'wrap' }}
        >
          {summaryItems.map((item) => (
            <MetricCard key={item.label}>
              <Stack direction="row" spacing={1} alignItems="center">
                {item.icon}
                <Typography variant="caption" color="text.secondary" textTransform="uppercase" fontWeight={600}>
                  {item.label}
                </Typography>
              </Stack>
              <Typography variant="h6" fontWeight={700}>
                {item.value}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {item.caption}
              </Typography>
            </MetricCard>
          ))}
        </Stack>
      </Stack>
    </SummaryContainer>
  );
};

export default SummaryStrip;
