import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Chip,
  IconButton,
  Button,
  Stack,
  Box,
  styled
} from '@mui/material';
import { alpha } from '@mui/material/styles';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import type { Campaign } from '@/types/campaign';

interface CampaignCardProps {
  campaign: Campaign;
  onResume?: (id: string) => void;
  onMenu?: (id: string) => void;
}

const StyledCard = styled(Card)(({ theme }) => ({
  backgroundColor: theme.palette.background.paper,
  border: `1px solid ${theme.palette.divider}`,
  transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out',
  '&:hover': {
    transform: 'translateY(-4px)',
    boxShadow: theme.shadows[3],
    borderColor: theme.palette.primary.main,
  }
}));

const StatusChip = styled(Chip)<{ status: string }>(({ theme, status }) => {
  const getColors = () => {
    switch (status) {
      case 'active':
        return {
          bg: alpha(theme.palette.success.main, 0.12),
          color: theme.palette.success.main,
          border: theme.palette.success.main
        };
      case 'completed':
        return {
          bg: alpha(theme.palette.info.main, 0.12),
          color: theme.palette.info.main,
          border: theme.palette.info.main
        };
      default:
        return {
          bg: alpha(theme.palette.text.secondary, 0.12),
          color: theme.palette.text.secondary,
          border: theme.palette.text.secondary
        };
    }
  };

  const colors = getColors();

  return {
    backgroundColor: colors.bg,
    color: colors.color,
    border: `1px solid ${colors.border}`,
    fontWeight: 600
  };
});

export const CampaignCard: React.FC<CampaignCardProps> = ({ campaign, onResume, onMenu }) => {
  return (
    <StyledCard>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" mb={2}>
          <Box>
            <Typography variant="h6" fontWeight="bold" gutterBottom>
              {campaign.name}
            </Typography>
            <StatusChip
              label={campaign.status.toUpperCase()}
              size="small"
              status={campaign.status}
            />
          </Box>
          <IconButton 
            size="small" 
            sx={{ color: 'text.secondary' }}
            onClick={() => onMenu?.(campaign.id)}
            aria-label="Campaign options"
          >
            <MoreVertIcon />
          </IconButton>
        </Stack>

        <Typography 
          variant="body2" 
          color="text.secondary" 
          paragraph 
          sx={{ minHeight: '3em' }}
        >
          {campaign.description}
        </Typography>

        <Stack direction="row" justifyContent="space-between" alignItems="center" mt={2}>
          <Typography variant="caption" color="text.secondary">
            Turn {campaign.current_turn} • Updated {new Date(campaign.updated_at).toLocaleDateString()}
          </Typography>
          <Button
            variant="outlined"
            size="small"
            startIcon={<PlayArrowIcon />}
            sx={{ borderColor: (theme) => theme.palette.divider, color: 'text.primary' }}
            onClick={() => onResume?.(campaign.id)}
          >
            Resume
          </Button>
        </Stack>
      </CardContent>
    </StyledCard>
  );
};
