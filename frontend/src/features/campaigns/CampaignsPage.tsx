/**
 * CampaignsPage - Campaign management page
 */
import { CampaignList } from './components/CampaignList';
import {
  useCampaigns,
  useStartCampaign,
  usePauseCampaign,
  useDeleteCampaign,
} from './api/campaignApi';
import { ErrorState } from '@/shared/components/feedback';
import type { Campaign } from '@/shared/types/campaign';

export default function CampaignsPage() {
  const { data: campaigns = [], isLoading, error } = useCampaigns();
  const startMutation = useStartCampaign();
  const pauseMutation = usePauseCampaign();
  const deleteMutation = useDeleteCampaign();

  const handleStart = async (id: string) => {
    await startMutation.mutateAsync(id);
  };

  const handlePause = async (id: string) => {
    await pauseMutation.mutateAsync(id);
  };

  const handleDelete = async (id: string) => {
    if (window.confirm('Are you sure you want to delete this campaign?')) {
      await deleteMutation.mutateAsync(id);
    }
  };

  const handleSelect = (campaign: Campaign) => {
    // Navigate to campaign detail or dashboard
    window.location.href = `/dashboard?campaign=${campaign.id}`;
  };

  if (error) {
    return (
      <ErrorState
        title="Failed to load campaigns"
        message={error.message}
        onRetry={() => window.location.reload()}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Campaigns</h1>
        <p className="text-muted-foreground">
          Manage your narrative campaigns and adventures
        </p>
      </div>

      {/* Campaign List */}
      <CampaignList
        campaigns={campaigns}
        isLoading={isLoading}
        onCreateNew={() => {}}
        onStart={handleStart}
        onPause={handlePause}
        onDelete={handleDelete}
        onSelect={handleSelect}
      />
    </div>
  );
}
