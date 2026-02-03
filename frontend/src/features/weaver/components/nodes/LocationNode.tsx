/**
 * LocationNode - React Flow node for locations
 *
 * Memoized component to prevent unnecessary re-renders during canvas interactions.
 */
import { memo } from 'react';
import type { NodeProps, Node } from '@xyflow/react';
import { Handle, Position } from '@xyflow/react';
import { MapPin } from 'lucide-react';
import { CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { WeaverNodeStatus } from '../../types';
import { WeaverNode } from './WeaverNode';

export interface LocationNodeData extends Record<string, unknown> {
  name: string;
  type: 'city' | 'building' | 'wilderness' | 'dungeon' | 'other';
  description: string;
  status?: WeaverNodeStatus;
}

export type LocationNodeType = Node<LocationNodeData>;

const locationTypeLabels: Record<LocationNodeData['type'], string> = {
  city: 'City',
  building: 'Building',
  wilderness: 'Wilderness',
  dungeon: 'Dungeon',
  other: 'Location',
};

function LocationNodeComponent({ data, id, selected }: NodeProps<LocationNodeType>) {
  return (
    <WeaverNode
      nodeId={id}
      nodeType="location"
      status={data.status}
      selected={selected}
      className="w-52 cursor-grab active:cursor-grabbing"
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-weaver-glow"
        data-testid="weaver-handle-target"
      />
      <CardContent className="p-3">
        <div className="mb-2 flex items-start gap-2">
          <MapPin className="mt-0.5 h-4 w-4 text-weaver-glow" />
          <div className="flex-1">
            <h4 className="text-sm font-medium">{data.name}</h4>
            <Badge variant="outline" className="mt-1 border-weaver-border text-xs">
              {locationTypeLabels[data.type]}
            </Badge>
          </div>
        </div>
        <p className="line-clamp-2 text-xs text-muted-foreground">{data.description}</p>
      </CardContent>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-weaver-glow"
        data-testid="weaver-handle-source"
      />
    </WeaverNode>
  );
}

export const LocationNode = memo(LocationNodeComponent);
