/**
 * CharacterNode - React Flow node for characters
 */
import type { NodeProps, Node } from '@xyflow/react';
import { Handle, Position } from '@xyflow/react';
import { Card, CardContent, Badge } from '@/shared/components/ui';
import { cn } from '@/lib/utils';

export interface CharacterNodeData {
  name: string;
  role: string;
  traits: string[];
}

export type CharacterNodeType = Node<CharacterNodeData>;

export function CharacterNode({ data, id, selected }: NodeProps<CharacterNodeType>) {
  return (
    <Card
      className={cn(
        'w-64 cursor-grab active:cursor-grabbing shadow-md',
        selected && 'ring-2 ring-primary ring-offset-2 ring-offset-background'
      )}
      data-testid="weaver-node"
      data-node-type="character"
      data-node-id={id}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-muted-foreground"
        data-testid="weaver-handle-target"
      />
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <h4 className="font-semibold">{data.name}</h4>
          <Badge variant="secondary" className="text-xs">
            {data.role}
          </Badge>
        </div>
        <div className="flex flex-wrap gap-1">
          {data.traits.map((trait) => (
            <Badge key={trait} variant="outline" className="text-xs">
              {trait}
            </Badge>
          ))}
        </div>
      </CardContent>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-muted-foreground"
        data-testid="weaver-handle-source"
      />
    </Card>
  );
}
