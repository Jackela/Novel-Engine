/**
 * WorldNode - React Flow node for world settings
 */
import type { NodeProps, Node } from '@xyflow/react';
import { Handle, Position } from '@xyflow/react';
import { Globe, Sparkles, Cog } from 'lucide-react';
import { CardContent, Badge } from '@/shared/components/ui';
import type { WeaverNodeStatus } from '../../types';
import { WeaverNode } from './WeaverNode';

export interface WorldNodeData extends Record<string, unknown> {
  name: string;
  description: string;
  genre: string;
  era: string;
  tone: string;
  themes: string[];
  magic_level: number;
  technology_level: number;
  status?: WeaverNodeStatus;
  errorMessage?: string;
}

export type WorldNodeType = Node<WorldNodeData>;

export function WorldNode({ data, id, selected }: NodeProps<WorldNodeType>) {
  return (
    <WeaverNode
      nodeId={id}
      nodeType="world"
      status={data.status}
      selected={selected}
      className="w-72 cursor-grab active:cursor-grabbing border-purple-500/50 bg-gradient-to-br from-purple-950/80 to-indigo-950/80"
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-purple-400"
        data-testid="weaver-handle-target"
      />
      <CardContent className="p-4">
        <div className="mb-3 flex items-center gap-2">
          <Globe className="h-5 w-5 text-purple-400" />
          <h4 className="font-semibold text-purple-100">{data.name}</h4>
        </div>
        <p className="mb-3 line-clamp-2 text-xs text-purple-200/80">
          {data.description}
        </p>
        <div className="mb-2 flex flex-wrap gap-1">
          <Badge variant="outline" className="border-purple-400/50 text-xs text-purple-200">
            {data.genre}
          </Badge>
          <Badge variant="outline" className="border-indigo-400/50 text-xs text-indigo-200">
            {data.era}
          </Badge>
          <Badge variant="outline" className="border-violet-400/50 text-xs text-violet-200">
            {data.tone}
          </Badge>
        </div>
        <div className="flex items-center gap-3 text-xs text-purple-300/70">
          <div className="flex items-center gap-1" title="Magic Level">
            <Sparkles className="h-3 w-3" />
            <span>{data.magic_level}/10</span>
          </div>
          <div className="flex items-center gap-1" title="Technology Level">
            <Cog className="h-3 w-3" />
            <span>{data.technology_level}/10</span>
          </div>
        </div>
        {data.themes.length > 0 ? (
          <div className="mt-2 flex flex-wrap gap-1">
            {data.themes.slice(0, 3).map((theme) => (
              <Badge key={theme} variant="secondary" className="text-xs bg-purple-800/50">
                {theme}
              </Badge>
            ))}
          </div>
        ) : null}
        {data.errorMessage ? (
          <p className="mt-2 text-xs text-red-400">{data.errorMessage}</p>
        ) : null}
      </CardContent>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-purple-400"
        data-testid="weaver-handle-source"
      />
    </WeaverNode>
  );
}
