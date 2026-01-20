/**
 * EventNode - React Flow node for story events
 */
import type { NodeProps, Node } from '@xyflow/react';
import { Handle, Position } from '@xyflow/react';
import { Calendar, Zap } from 'lucide-react';
import { Card, CardContent, Badge } from '@/shared/components/ui';
import { cn } from '@/shared/lib/utils';

export interface EventNodeData {
  title: string;
  type: 'action' | 'dialogue' | 'discovery' | 'conflict' | 'resolution';
  description: string;
  timestamp?: string;
}

export type EventNodeType = Node<EventNodeData>;

const eventTypeStyles: Record<EventNodeData['type'], string> = {
  action: 'border-l-orange-500',
  dialogue: 'border-l-blue-500',
  discovery: 'border-l-green-500',
  conflict: 'border-l-red-500',
  resolution: 'border-l-purple-500',
};

const eventTypeLabels: Record<EventNodeData['type'], string> = {
  action: 'Action',
  dialogue: 'Dialogue',
  discovery: 'Discovery',
  conflict: 'Conflict',
  resolution: 'Resolution',
};

export function EventNode({ data, id, selected }: NodeProps<EventNodeType>) {
  return (
    <Card
      className={cn(
        'w-56 cursor-grab active:cursor-grabbing shadow-md border-l-4',
        eventTypeStyles[data.type],
        selected && 'ring-2 ring-primary ring-offset-2 ring-offset-background'
      )}
      data-testid="weaver-node"
      data-node-type="event"
      data-node-id={id}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-muted-foreground"
        data-testid="weaver-handle-target"
      />
      <CardContent className="p-3">
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-1.5">
            <Zap className="h-4 w-4 text-muted-foreground" />
            <span className="font-medium text-sm">{data.title}</span>
          </div>
          <Badge variant="outline" className="text-xs">
            {eventTypeLabels[data.type]}
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground line-clamp-2 mb-2">
          {data.description}
        </p>
        {data.timestamp && (
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Calendar className="h-3 w-3" />
            <span>{data.timestamp}</span>
          </div>
        )}
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
