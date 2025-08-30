import React from 'react';
import { Box, useTheme, useMediaQuery } from '@mui/material';
import { styled } from '@mui/material/styles';

const GridContainer = styled(Box)(({ theme }) => ({
  display: 'grid',
  width: '100%',
  maxWidth: '1200px',
  margin: '0 auto',
  padding: theme.spacing(3),
  
  // Desktop (≥1200px): 12-column grid  
  [theme.breakpoints.up('xl')]: {
    gridTemplateColumns: 'repeat(12, 1fr)',
    gap: '24px 20px',
    padding: theme.spacing(3),
  },
  
  // Large Desktop (≥1024px): 12-column grid
  [theme.breakpoints.between('lg', 'xl')]: {
    gridTemplateColumns: 'repeat(12, 1fr)',
    gap: '24px 20px',
    padding: theme.spacing(3),
  },
  
  // Tablet (768px - 1199px): 8-column grid
  [theme.breakpoints.between('md', 'lg')]: {
    gridTemplateColumns: 'repeat(8, 1fr)',
    gap: '20px 16px',
    padding: theme.spacing(2.5),
  },
  
  // Mobile (≤767px): Single column
  [theme.breakpoints.down('md')]: {
    gridTemplateColumns: '1fr',
    gap: '16px 12px',
    padding: theme.spacing(2),
  },
}));

interface BentoGridProps {
  children: React.ReactNode;
}

const BentoGrid: React.FC<BentoGridProps> = ({ children }) => {
  const theme = useTheme();
  const isDesktop = useMediaQuery(theme.breakpoints.up('lg'));
  const isTablet = useMediaQuery(theme.breakpoints.between('md', 'lg'));
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  return (
    <GridContainer>
      {children}
    </GridContainer>
  );
};

export default BentoGrid;