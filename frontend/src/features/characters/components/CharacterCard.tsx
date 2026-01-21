/**
 * CharacterCard - Display card for a character
 */
import { User, Edit, Trash2 } from 'lucide-react';
import { Card, CardContent, Badge, Button } from '@/shared/components/ui';
import { cn } from '@/shared/lib/utils';
import type { CharacterSummary } from '@/shared/types/character';

interface CharacterCardProps {
  character: CharacterSummary;
  onEdit?: (character: CharacterSummary) => void;
  onDelete?: (id: string) => void;
  onSelect?: (character: CharacterSummary) => void;
  selected?: boolean;
}

const typeBadgeStyles: Record<string, string> = {
  protagonist: 'bg-primary text-primary-foreground',
  antagonist: 'bg-destructive text-destructive-foreground',
  npc: 'bg-accent text-accent-foreground',
};

export function CharacterCard({
  character,
  onEdit,
  onDelete,
  onSelect,
  selected = false,
}: CharacterCardProps) {
  return (
    <Card
      className={cn(
        'cursor-pointer transition-all hover:shadow-md',
        selected && 'ring-2 ring-primary'
      )}
      onClick={() => onSelect?.(character)}
    >
      <CardContent className="p-4">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            {/* Avatar */}
            <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center overflow-hidden">
              <User className="h-6 w-6 text-muted-foreground" />
            </div>
            <div>
              <h3 className="font-semibold text-sm">{character.name}</h3>
              <Badge
                className={cn(
                  'text-xs capitalize',
                  typeBadgeStyles[character.type] || 'bg-muted text-muted-foreground'
                )}
              >
                {character.type}
              </Badge>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-1">
            {onEdit && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={(e) => {
                  e.stopPropagation();
                  onEdit(character);
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
                  onDelete(character.id);
                }}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>

        {/* Meta */}
        <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
          <div className="rounded bg-muted/50 px-2 py-1">
            <div className="text-muted-foreground">Status</div>
            <div className="font-medium capitalize">{character.status}</div>
          </div>
          <div className="rounded bg-muted/50 px-2 py-1">
            <div className="text-muted-foreground">Updated</div>
            <div className="font-medium">{new Date(character.updated_at).toLocaleDateString()}</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
