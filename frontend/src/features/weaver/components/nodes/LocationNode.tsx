/**
 * LocationNode - React Flow node for locations
 */
import type { NodeProps, Node } from '@xyflow/react';
import { Handle, Position } from '@xyflow/react';
import { MapPin } from 'lucide-react';
import { Card, CardContent, Badge } from '@/shared/components/ui';
import { cn } from '@/lib/utils';

export interface LocationNodeData {
  name: string;
  type: 'city' | 'building' | 'wilderness' | 'dungeon' | 'other';
  description: string;
}

export type LocationNodeType = Node<LocationNodeData>;

const locationTypeLabels: Record<LocationNodeData['type'], string> = {
  city: 'City',
  building: 'Building',
  wilderness: 'Wilderness',
  dungeon: 'Dungeon',
  other: 'Location',
};

export function LocationNode({ data, id, selected }: NodeProps<LocationNodeType>) {
  return (
    <Card
      className={cn(
        'w-52 cursor-grab active:cursor-grabbing shadow-md bg-emerald-50 dark:bg-emerald-950/30',
        selected && 'ring-2 ring-primary ring-offset-2 ring-offset-background'
      )}
      data-testid="weaver-node"
      data-node-type="location"
      data-node-id={id}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-emerald-500"
        data-testid="weaver-handle-target"
      />
      <CardContent className="p-3">
        <div className="flex items-start gap-2 mb-2">
          <MapPin className="h-4 w-4 text-emerald-600 mt-0.5" />
          <div className="flex-1">
            <h4 className="font-medium text-sm">{data.name}</h4>
            <Badge variant="outline" className="text-xs mt-1 border-emerald-300">
              {locationTypeLabels[data.type]}
            </Badge>
          </div>
        </div>
        <p className="text-xs text-muted-foreground line-clamp-2">{data.description}</p>
      </CardContent>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-emerald-500"
        data-testid="weaver-handle-source"
      />
    </Card>
  );
}
