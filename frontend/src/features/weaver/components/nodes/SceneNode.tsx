/**
 * SceneNode - React Flow node for scenes
 *
 * Memoized component to prevent unnecessary re-renders during canvas interactions.
 *
 * DIR-050: Shows plotline indicators as colored dots.
 */
import { memo } from 'react';
import type { NodeProps, Node } from '@xyflow/react';
import { Handle, Position } from '@xyflow/react';
import { CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { SceneNodeData } from '../../types';
import { WeaverNode } from './WeaverNode';

export type SceneNodeType = Node<SceneNodeData>;

const sceneTypeBadgeVariant: Record<
  string,
  'default' | 'secondary' | 'destructive' | 'outline'
> = {
  opening: 'default',
  action: 'secondary',
  dialogue: 'outline',
  climax: 'destructive',
  resolution: 'default',
};

/**
 * Plotline indicators - colored dots showing which plotlines this scene belongs to.
 *
 * Why: Provides visual context for narrative threads in the Weaver graph.
 * Shows up to 5 colored dots; if more, shows a "+N" indicator.
 */
function PlotlineIndicators({
  plotlines,
}: {
  plotlines?: Array<{ id: string; name: string; color: string }>;
}) {
  if (!plotlines || plotlines.length === 0) {
    return null;
  }

  const MAX_VISIBLE = 5;
  const visible = plotlines.slice(0, MAX_VISIBLE);
  const extraCount = plotlines.length - MAX_VISIBLE;

  return (
    <div
      className="flex items-center gap-1"
      title={plotlines.map((p) => p.name).join(', ')}
    >
      {visible.map((plotline) => (
        <div
          key={plotline.id}
          className="h-2 w-2 rounded-full border border-white/20"
          style={{ backgroundColor: plotline.color }}
          title={plotline.name}
        />
      ))}
      {extraCount > 0 && (
        <span className="text-xs text-muted-foreground">+{extraCount}</span>
      )}
    </div>
  );
}

function SceneNodeComponent({ data, id, selected }: NodeProps<SceneNodeType>) {
  const badgeVariant = sceneTypeBadgeVariant[data.sceneType] ?? 'secondary';

  return (
    <WeaverNode
      nodeId={id}
      nodeType="scene"
      status={data.status}
      selected={selected}
      className="w-72 cursor-grab active:cursor-grabbing"
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-weaver-border"
        data-testid="weaver-handle-target"
      />
      <CardContent className="p-4">
        <div className="mb-2 flex items-center justify-between gap-2">
          <h4 className="flex-1 truncate text-sm font-semibold">{data.title}</h4>
          <Badge variant={badgeVariant} className="shrink-0 text-xs capitalize">
            {data.sceneType}
          </Badge>
        </div>
        {data.summary ? (
          <p className="line-clamp-2 text-xs text-muted-foreground">{data.summary}</p>
        ) : null}
        {/* Plotline indicators (DIR-050) */}
        {data.plotlines && data.plotlines.length > 0 && (
          <div className="mt-2 flex items-center gap-2">
            <PlotlineIndicators plotlines={data.plotlines} />
          </div>
        )}
        {data.visualPrompt && data.status === 'idle' ? (
          <p className="mt-2 truncate text-xs italic text-muted-foreground/70">
            Visual: {data.visualPrompt}
          </p>
        ) : null}
        {data.errorMessage ? (
          <p className="mt-2 text-xs text-weaver-error">{data.errorMessage}</p>
        ) : null}
      </CardContent>
      <Handle
        type="source"
        position={Position.Right}
        className="!bg-weaver-border"
        data-testid="weaver-handle-source"
      />
    </WeaverNode>
  );
}

export const SceneNode = memo(SceneNodeComponent);
