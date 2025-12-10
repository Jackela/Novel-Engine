import React from 'react';
import { Box } from '@mui/material';
import CommandLayout from '../components/layout/CommandLayout';
import { CampaignList } from '@/features/campaigns';

const CampaignsPage: React.FC = () => {
  return (
    <CommandLayout title="Campaign Operations">
      <Box sx={{ p: 3 }}>
        <CampaignList />
      </Box>
    </CommandLayout>
  );
};

export default CampaignsPage;