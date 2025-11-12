import React from 'react';
import { Box } from '@mui/material';

export interface DashboardZone {
  id: string;
  role: string;
  priority?: number;
  className?: string;
  testId?: string;
  density?: 'relaxed' | 'compact';
  volumeLabel?: string;
  children: React.ReactNode;
}

interface DashboardZonesProps {
  zones: DashboardZone[];
  className?: string;
}

const mergeClassNames = (...parts: Array<string | undefined>) => parts.filter(Boolean).join(' ');

const DashboardZones: React.FC<DashboardZonesProps> = ({ zones, className }) => {
  const orderedZones = React.useMemo(
    () => [...zones].sort((a, b) => (b.priority ?? 0) - (a.priority ?? 0)),
    [zones]
  );

  return (
    <Box className={mergeClassNames('dashboard-zones', className)} data-testid="dashboard-zones">
      {orderedZones.map((zone) => (
        <Box
          key={zone.id}
          component="section"
          className={mergeClassNames(
            'dashboard-zone',
            zone.density ? `density-${zone.density}` : undefined,
            zone.className
          )}
          data-role={zone.role}
          data-density={zone.density ?? 'relaxed'}
          data-volume={zone.volumeLabel}
          data-testid={zone.testId ?? `zone-${zone.id}`}
        >
          {zone.children}
        </Box>
      ))}
    </Box>
  );
};

export default DashboardZones;
