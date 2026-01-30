/**
 * CharacterNode - React Flow node for characters
 *
 * Memoized component to prevent unnecessary re-renders during canvas interactions.
 * Only re-renders when node data, id, or selected state changes.
 */
import { memo } from 'react';
import type { NodeProps, Node } from '@xyflow/react';
import { Handle, Position } from '@xyflow/react';
import { CardContent, Badge } from '@/shared/components/ui';
import type { WeaverNodeStatus } from '../../types';
import { WeaverNode } from './WeaverNode';

export interface CharacterNodeData extends Record<string, unknown> {
  name: string;
  role: string;
  traits: string[];
  status?: WeaverNodeStatus;
  tagline?: string;
  bio?: string;
  visualPrompt?: string;
  errorMessage?: string;
}

export type CharacterNodeType = Node<CharacterNodeData>;

function CharacterNodeComponent({ data, id, selected }: NodeProps<CharacterNodeType>) {
  return (
    <WeaverNode
      nodeId={id}
      nodeType="character"
      status={data.status}
      selected={selected}
      className="w-64 cursor-grab active:cursor-grabbing"
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-weaver-border"
        data-testid="weaver-handle-target"
      />
      <CardContent className="p-4">
        <div className="mb-2 flex items-center justify-between">
          <h4 className="font-semibold">{data.name}</h4>
          <Badge variant="secondary" className="text-xs">
            {data.role}
          </Badge>
        </div>
        {data.tagline ? (
          <p className="text-xs text-muted-foreground">{data.tagline}</p>
        ) : null}
        {data.bio ? (
          <p className="mt-2 text-xs text-muted-foreground">{data.bio}</p>
        ) : null}
        {data.errorMessage ? (
          <p className="mt-2 text-xs text-weaver-error">{data.errorMessage}</p>
        ) : null}
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
        className="!bg-weaver-border"
        data-testid="weaver-handle-source"
      />
    </WeaverNode>
  );
}

export const CharacterNode = memo(CharacterNodeComponent);
