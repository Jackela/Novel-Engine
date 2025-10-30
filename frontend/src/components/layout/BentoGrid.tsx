import React from 'react';
import { Box, useTheme, useMediaQuery } from '@mui/material';
import { styled } from '@mui/material/styles';

const GridContainer = styled(Box)(({ theme }) => ({
  display: 'grid',
  width: '100%',
  maxWidth: '1400px',
  margin: '0 auto',
  
  // Desktop (≥1200px): 12-column grid  
  [theme.breakpoints.up('lg')]: {
    gridTemplateColumns: 'repeat(12, 1fr)',
    gap: theme.spacing(3, 2.5),
    padding: 0,
  },
  
  // Tablet (900px - 1199px): 8-column grid
  [theme.breakpoints.between('md', 'lg')]: {
    gridTemplateColumns: 'repeat(8, 1fr)',
    gap: theme.spacing(2.5, 2),
    padding: 0,
  },
  
  // Mobile (<900px): Single column
  [theme.breakpoints.down('md')]: {
    gridTemplateColumns: '1fr',
    gap: theme.spacing(2),
    padding: 0,
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