/**
 * CharacterCard - Display card for a character
 */
import { User, Edit, Trash2, MoreVertical } from 'lucide-react';
import { Card, CardContent, Badge, Button } from '@/shared/components/ui';
import { cn } from '@/shared/lib/utils';
import type { Character, CharacterRole } from '@/shared/types/character';

interface CharacterCardProps {
  character: Character;
  onEdit?: (character: Character) => void;
  onDelete?: (id: string) => void;
  onSelect?: (character: Character) => void;
  selected?: boolean;
}

const roleColors: Record<CharacterRole, string> = {
  protagonist: 'bg-primary text-primary-foreground',
  antagonist: 'bg-destructive text-destructive-foreground',
  supporting: 'bg-secondary text-secondary-foreground',
  minor: 'bg-muted text-muted-foreground',
  npc: 'bg-accent text-accent-foreground',
};

const roleLabels: Record<CharacterRole, string> = {
  protagonist: 'Protagonist',
  antagonist: 'Antagonist',
  supporting: 'Supporting',
  minor: 'Minor',
  npc: 'NPC',
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
              {character.imageUrl ? (
                <img
                  src={character.imageUrl}
                  alt={character.name}
                  className="h-full w-full object-cover"
                />
              ) : (
                <User className="h-6 w-6 text-muted-foreground" />
              )}
            </div>
            <div>
              <h3 className="font-semibold text-sm">{character.name}</h3>
              <Badge className={cn('text-xs', roleColors[character.role])}>
                {roleLabels[character.role]}
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

        {/* Description */}
        <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
          {character.description}
        </p>

        {/* Traits */}
        {character.traits.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {character.traits.slice(0, 3).map((trait) => (
              <Badge key={trait} variant="outline" className="text-xs">
                {trait}
              </Badge>
            ))}
            {character.traits.length > 3 && (
              <Badge variant="outline" className="text-xs">
                +{character.traits.length - 3}
              </Badge>
            )}
          </div>
        )}

        {/* Stats preview */}
        <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
          <div className="text-center p-1 rounded bg-muted/50">
            <div className="font-medium">{character.stats.strength}</div>
            <div className="text-muted-foreground">STR</div>
          </div>
          <div className="text-center p-1 rounded bg-muted/50">
            <div className="font-medium">{character.stats.intelligence}</div>
            <div className="text-muted-foreground">INT</div>
          </div>
          <div className="text-center p-1 rounded bg-muted/50">
            <div className="font-medium">{character.stats.charisma}</div>
            <div className="text-muted-foreground">CHA</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
