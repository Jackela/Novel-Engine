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
  background: 'linear-gradient(180deg, rgba(255, 255, 255, 0.03) 0%, rgba(255, 255, 255, 0.0) 100%)',
  border: '1px solid rgba(255, 255, 255, 0.08)',
  boxShadow: '0 4px 20px rgba(0, 0, 0, 0.2)',
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
  background: 'rgba(255, 255, 255, 0.02)',
  border: '1px solid rgba(255, 255, 255, 0.05)',
  backdropFilter: 'blur(10px)',
  transition: 'all 0.2s ease-in-out',
  '&:hover': {
    transform: 'translateY(-2px)',
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
  },
}));

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

  const metricsContent = (
    <Stack
      direction={isTablet ? 'column' : 'row'}
      spacing={1.25}
      justifyContent="space-between"
      alignItems={isTablet ? 'flex-start' : 'center'}
      sx={{ minWidth: 0 }}
    >
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
        {summaryItems.map((item) => (
          <MetricCard key={item.label} className="glass-card">
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
  );

  return (
    <SummaryContainer {...containerProps} className="glass-panel">
      {metricsContent}
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
