/**
 * CharacterNode - Custom React Flow node for character entities
 *
 * Why: Provides a themed, interactive node representation for characters
 * in the relationship graph. Matches shadcn/ui design system.
 */
import { memo } from 'react';
import { Handle, Position, type NodeProps, type Node } from '@xyflow/react';
import { User } from 'lucide-react';
import { Badge } from '@/shared/components/ui';
import { cn } from '@/lib/utils';

export interface CharacterNodeData extends Record<string, unknown> {
  name: string;
  archetype?: string;
  avatarUrl?: string;
}

export type CharacterNodeType = Node<CharacterNodeData>;

/**
 * CharacterNode displays a character with avatar placeholder, name, and archetype badge.
 * Styled to match shadcn/ui Card component aesthetic.
 */
function CharacterNodeComponent({ data, selected }: NodeProps<CharacterNodeType>) {
  return (
    <>
      <Handle
        type="target"
        position={Position.Top}
        className="!h-2 !w-2 !rounded-full !border-2 !border-primary !bg-background"
      />

      <div
        className={cn(
          'min-w-[140px] rounded-lg border bg-card p-3 shadow-md transition-all',
          'hover:shadow-lg',
          selected
            ? 'border-primary ring-2 ring-primary ring-offset-2 ring-offset-background'
            : 'border-border'
        )}
      >
        <div className="flex items-center gap-3">
          {/* Avatar placeholder */}
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-muted">
            {data.avatarUrl ? (
              <img
                src={data.avatarUrl}
                alt={data.name}
                className="h-full w-full rounded-full object-cover"
              />
            ) : (
              <User className="h-5 w-5 text-muted-foreground" />
            )}
          </div>

          <div className="min-w-0 flex-1">
            {/* Character name */}
            <p className="truncate text-sm font-medium text-foreground">{data.name}</p>

            {/* Archetype badge */}
            {data.archetype && (
              <Badge variant="secondary" className="mt-1 text-[10px]">
                {data.archetype}
              </Badge>
            )}
          </div>
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="!h-2 !w-2 !rounded-full !border-2 !border-primary !bg-background"
      />
    </>
  );
}

export const CharacterNode = memo(CharacterNodeComponent);

export default CharacterNode;
