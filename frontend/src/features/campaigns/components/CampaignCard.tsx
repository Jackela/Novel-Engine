/**
 * CampaignCard - Display card for a campaign
 */
import { Play, Pause, Edit, Trash2, Users, Clock } from 'lucide-react';
import { Card, CardContent, Badge, Button } from '@/shared/components/ui';
import { cn, formatRelativeTime } from '@/lib/utils';
import type { Campaign, CampaignStatus } from '@/shared/types/campaign';

interface CampaignCardProps {
  campaign: Campaign;
  onStart?: ((id: string) => void) | undefined;
  onPause?: ((id: string) => void) | undefined;
  onEdit?: ((campaign: Campaign) => void) | undefined;
  onDelete?: ((id: string) => void) | undefined;
  onSelect?: ((campaign: Campaign) => void) | undefined;
}

const statusColors: Record<CampaignStatus, string> = {
  draft: 'bg-muted text-muted-foreground',
  active: 'bg-success text-success-foreground',
  paused: 'bg-warning text-warning-foreground',
  completed: 'bg-primary text-primary-foreground',
  archived: 'bg-secondary text-secondary-foreground',
};

const statusLabels: Record<CampaignStatus, string> = {
  draft: 'Draft',
  active: 'Active',
  paused: 'Paused',
  completed: 'Completed',
  archived: 'Archived',
};

export function CampaignCard({
  campaign,
  onStart,
  onPause,
  onEdit,
  onDelete,
  onSelect,
}: CampaignCardProps) {
  return (
    <Card
      className="cursor-pointer transition-all hover:shadow-md"
      onClick={() => onSelect?.(campaign)}
    >
      <CardContent className="p-4">
        <CampaignHeader
          campaign={campaign}
          onStart={onStart}
          onPause={onPause}
          onEdit={onEdit}
          onDelete={onDelete}
        />

        {/* Description */}
        <p className="mb-3 line-clamp-2 text-sm text-muted-foreground">
          {campaign.description}
        </p>

        {/* Meta */}
        <CampaignMeta campaign={campaign} />
      </CardContent>
    </Card>
  );
}

function CampaignHeader({
  campaign,
  onStart,
  onPause,
  onEdit,
  onDelete,
}: CampaignCardProps) {
  return (
    <div className="mb-3 flex items-start justify-between">
      <div>
        <h3 className="font-semibold">{campaign.name}</h3>
        <Badge className={cn('mt-1 text-xs', statusColors[campaign.status])}>
          {statusLabels[campaign.status]}
        </Badge>
      </div>
      <CampaignActions
        campaign={campaign}
        onStart={onStart}
        onPause={onPause}
        onEdit={onEdit}
        onDelete={onDelete}
      />
    </div>
  );
}

function CampaignActions({
  campaign,
  onStart,
  onPause,
  onEdit,
  onDelete,
}: CampaignCardProps) {
  return (
    <div className="flex gap-1">
      {campaign.status === 'active' && onPause && (
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={(event) => {
            event.stopPropagation();
            onPause(campaign.id);
          }}
        >
          <Pause className="h-4 w-4" />
        </Button>
      )}
      {(campaign.status === 'draft' || campaign.status === 'paused') && onStart && (
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-success"
          onClick={(event) => {
            event.stopPropagation();
            onStart(campaign.id);
          }}
        >
          <Play className="h-4 w-4" />
        </Button>
      )}
      {onEdit && (
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={(event) => {
            event.stopPropagation();
            onEdit(campaign);
          }}
        >
          <Edit className="h-4 w-4" />
        </Button>
      )}
      {onDelete && (
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-destructive"
          onClick={(event) => {
            event.stopPropagation();
            onDelete(campaign.id);
          }}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
}

function CampaignMeta({ campaign }: Pick<CampaignCardProps, 'campaign'>) {
  return (
    <div className="flex items-center gap-4 text-xs text-muted-foreground">
      <div className="flex items-center gap-1">
        <Users className="h-3 w-3" />
        <span>{campaign.characterIds.length} characters</span>
      </div>
      <div className="flex items-center gap-1">
        <Clock className="h-3 w-3" />
        <span>Turn {campaign.currentTurn}</span>
      </div>
      <span className="ml-auto">{formatRelativeTime(campaign.updatedAt)}</span>
    </div>
  );
}
