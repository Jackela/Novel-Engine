/**
 * EventNode - React Flow node for story events
 *
 * Memoized component to prevent unnecessary re-renders during canvas interactions.
 */
import { memo } from 'react';
import type { NodeProps, Node } from '@xyflow/react';
import { Handle, Position } from '@xyflow/react';
import { Calendar, Zap } from 'lucide-react';
import { CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { WeaverNodeStatus } from '../../types';
import { resolveNodeStatus } from './nodeStyles';
import { WeaverNode } from './WeaverNode';

export interface EventNodeData extends Record<string, unknown> {
  title: string;
  type: 'action' | 'dialogue' | 'discovery' | 'conflict' | 'resolution';
  description: string;
  timestamp?: string;
  status?: WeaverNodeStatus;
}

export type EventNodeType = Node<EventNodeData>;

const eventTypeStyles: Record<EventNodeData['type'], string> = {
  action: 'border-l-weaver-glow',
  dialogue: 'border-l-weaver-neon',
  discovery: 'border-l-emerald-400',
  conflict: 'border-l-weaver-error',
  resolution: 'border-l-cyan-300',
};

const eventTypeLabels: Record<EventNodeData['type'], string> = {
  action: 'Action',
  dialogue: 'Dialogue',
  discovery: 'Discovery',
  conflict: 'Conflict',
  resolution: 'Resolution',
};

function EventNodeComponent({ data, id, selected }: NodeProps<EventNodeType>) {
  const status = resolveNodeStatus(data.status, selected);
  const eventAccent = status === 'error' ? '' : eventTypeStyles[data.type];
  return (
    <WeaverNode
      nodeId={id}
      nodeType="event"
      status={status}
      className={cn('w-56 cursor-grab border-l-4 active:cursor-grabbing', eventAccent)}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-weaver-border"
        data-testid="weaver-handle-target"
      />
      <CardContent className="p-3">
        <div className="mb-2 flex items-start justify-between">
          <div className="flex items-center gap-1.5">
            <Zap className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">{data.title}</span>
          </div>
          <Badge variant="outline" className="text-xs">
            {eventTypeLabels[data.type]}
          </Badge>
        </div>
        <p className="mb-2 line-clamp-2 text-xs text-muted-foreground">
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
        className="!bg-weaver-border"
        data-testid="weaver-handle-source"
      />
    </WeaverNode>
  );
}

export const EventNode = memo(EventNodeComponent);
