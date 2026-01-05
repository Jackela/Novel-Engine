import React from 'react';
import { Container } from '@mui/material';
import { CampaignList } from '@/features/campaigns';

const CampaignsPage: React.FC = () => {
  return (
    <Container maxWidth="xl" sx={{ py: { xs: 3, md: 4 } }}>
      <CampaignList />
    </Container>
  );
};

export default CampaignsPage;
