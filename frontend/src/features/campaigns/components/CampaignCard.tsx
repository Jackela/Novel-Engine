/**
 * CampaignCard - Display card for a campaign
 */
import { Play, Pause, Edit, Trash2, Users, Clock } from 'lucide-react';
import { Card, CardContent, Badge, Button } from '@/shared/components/ui';
import { cn, formatRelativeTime } from '@/shared/lib/utils';
import type { Campaign, CampaignStatus } from '@/shared/types/campaign';

interface CampaignCardProps {
  campaign: Campaign;
  onStart?: (id: string) => void;
  onPause?: (id: string) => void;
  onEdit?: (campaign: Campaign) => void;
  onDelete?: (id: string) => void;
  onSelect?: (campaign: Campaign) => void;
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
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div>
            <h3 className="font-semibold">{campaign.name}</h3>
            <Badge className={cn('text-xs mt-1', statusColors[campaign.status])}>
              {statusLabels[campaign.status]}
            </Badge>
          </div>

          {/* Actions */}
          <div className="flex gap-1">
            {campaign.status === 'active' && onPause && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={(e) => {
                  e.stopPropagation();
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
                onClick={(e) => {
                  e.stopPropagation();
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
                onClick={(e) => {
                  e.stopPropagation();
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
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(campaign.id);
                }}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>

        {/* Description */}
        <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
          {campaign.description}
        </p>

        {/* Meta */}
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
      </CardContent>
    </Card>
  );
}
