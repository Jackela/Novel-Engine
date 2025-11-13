import React from 'react';
import { Box } from '@mui/material';
import { styled } from '@mui/material/styles';

const GridContainer = styled(Box)(({ theme }) => ({
  display: 'grid',
  width: '100%',
  maxWidth: '1400px',
  margin: '0 auto',
  gridAutoFlow: 'row dense',
  gridAutoRows: 'minmax(160px, auto)',
  gap: theme.spacing(2.5),
  padding: 0,

  [theme.breakpoints.up('lg')]: {
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: theme.spacing(3),
  },

  [theme.breakpoints.between('md', 'lg')]: {
    gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
    gap: theme.spacing(2.5),
  },

  [theme.breakpoints.down('md')]: {
    gridTemplateColumns: '1fr',
    gap: theme.spacing(2),
  },
}));

interface BentoGridProps {
  children: React.ReactNode;
}

const BentoGrid: React.FC<BentoGridProps> = ({ children }) => {

  return (
    <GridContainer data-testid="bento-grid">
      {children}
    </GridContainer>
  );
};

export default BentoGrid;
