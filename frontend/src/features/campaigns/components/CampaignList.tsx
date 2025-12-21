import React from 'react';
import {
  Box,
  Typography,
  Grid,
  Button,
  Stack,
  useTheme
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DescriptionIcon from '@mui/icons-material/Description';

import { useCampaigns } from '../hooks/useCampaigns';
import { CampaignCard } from './CampaignCard';
import AsyncStates from '@/components/common/AsyncStates';
import EmptyState from '@/components/common/EmptyState';

const CampaignList: React.FC = () => {
  const { data: campaigns, isLoading, error } = useCampaigns();
  const theme = useTheme();

  // Handlers (placeholders for now - strictly UI state/events)
  const handleResume = (id: string) => console.log('Resume', id);
  const handleMenu = (id: string) => console.log('Menu', id);
  const handleNew = () => console.log('New Campaign');

  // Success content logic
  const renderContent = () => {
    if (campaigns.length === 0) {
      return (
        <EmptyState
          title="No Active Campaigns"
          description="Start a new adventure by creating your first campaign. Choose a setting, define your protagonist, and begin."
          actionLabel="Create Campaign"
          onAction={handleNew}
          icon={<DescriptionIcon />}
        />
      );
    }

    return (
      <Grid container spacing={3}>
        {campaigns.map((campaign) => (
          <Grid item xs={12} md={6} lg={4} key={campaign.id}>
            <CampaignCard
              campaign={campaign}
              onResume={handleResume}
              onMenu={handleMenu}
            />
          </Grid>
        ))}
      </Grid>
    );
  };

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={4}>
        <Typography variant="h4" sx={{ fontFamily: 'Orbitron', color: 'text.primary' }}>
          Active Campaigns
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleNew}
          sx={{
            background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
          }}
        >
          New Campaign
        </Button>
      </Stack>

      <AsyncStates isLoading={isLoading} error={error}>
        {renderContent()}
      </AsyncStates>
    </Box>
  );
};

export default CampaignList;
