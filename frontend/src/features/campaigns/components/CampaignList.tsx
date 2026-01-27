/**
 * CampaignList - List display of campaigns
 */
import { Plus, Filter } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/shared/components/ui';
import { LoadingSpinner, EmptyState } from '@/shared/components/feedback';
import { CampaignCard } from './CampaignCard';
import type { Campaign, CampaignStatus } from '@/shared/types/campaign';

interface CampaignListProps {
  campaigns: Campaign[];
  isLoading?: boolean;
  onCreateNew?: () => void;
  onStart?: (id: string) => void;
  onPause?: (id: string) => void;
  onEdit?: (campaign: Campaign) => void;
  onDelete?: (id: string) => void;
  onSelect?: (campaign: Campaign) => void;
}

const statusFilters: { value: CampaignStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'active', label: 'Active' },
  { value: 'paused', label: 'Paused' },
  { value: 'draft', label: 'Draft' },
  { value: 'completed', label: 'Completed' },
];

export function CampaignList({
  campaigns,
  isLoading = false,
  onCreateNew,
  onStart,
  onPause,
  onEdit,
  onDelete,
  onSelect,
}: CampaignListProps) {
  const [statusFilter, setStatusFilter] = useState<CampaignStatus | 'all'>('all');

  const filteredCampaigns =
    statusFilter === 'all'
      ? campaigns
      : campaigns.filter((c) => c.status === statusFilter);

  if (isLoading) {
    return <LoadingSpinner fullScreen text="Loading campaigns..." />;
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <div className="flex gap-1">
            {statusFilters.map((filter) => (
              <Button
                key={filter.value}
                variant={statusFilter === filter.value ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setStatusFilter(filter.value)}
              >
                {filter.label}
              </Button>
            ))}
          </div>
        </div>
        {onCreateNew && (
          <Button onClick={onCreateNew}>
            <Plus className="mr-2 h-4 w-4" />
            New Campaign
          </Button>
        )}
      </div>

      {/* List or Empty State */}
      {filteredCampaigns.length === 0 ? (
        <EmptyState
          title={
            statusFilter === 'all' ? 'No campaigns yet' : `No ${statusFilter} campaigns`
          }
          description={
            statusFilter === 'all'
              ? 'Create your first campaign to start your narrative adventure'
              : 'Try changing the filter to see other campaigns'
          }
          {...(statusFilter === 'all' && onCreateNew
            ? { action: { label: 'Create Campaign', onClick: onCreateNew } }
            : {})}
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredCampaigns.map((campaign) => (
            <CampaignCard
              key={campaign.id}
              campaign={campaign}
              {...(onStart ? { onStart } : {})}
              {...(onPause ? { onPause } : {})}
              {...(onEdit ? { onEdit } : {})}
              {...(onDelete ? { onDelete } : {})}
              {...(onSelect ? { onSelect } : {})}
            />
          ))}
        </div>
      )}
    </div>
  );
}
