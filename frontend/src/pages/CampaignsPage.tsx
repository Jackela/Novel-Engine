import React from 'react';
import { Box } from '@mui/material';
import { CampaignList } from '@/features/campaigns';

const CampaignsPage: React.FC = () => {
  return (
    <Box sx={{ p: 3 }}>
      <CampaignList />
    </Box>
  );
};

export default CampaignsPage;
