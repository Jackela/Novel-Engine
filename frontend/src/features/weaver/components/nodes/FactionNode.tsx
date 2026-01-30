/**
 * FactionNode - React Flow node for factions
 */
import type { NodeProps, Node } from '@xyflow/react';
import { Handle, Position } from '@xyflow/react';
import { Shield, Users, Swords } from 'lucide-react';
import { CardContent, Badge } from '@/shared/components/ui';
import type { WeaverNodeStatus } from '../../types';
import { WeaverNode } from './WeaverNode';

export interface FactionNodeData extends Record<string, unknown> {
  name: string;
  description: string;
  faction_type: string;
  alignment: string;
  values: string[];
  goals: string[];
  influence: number;
  ally_count: number;
  enemy_count: number;
  status?: WeaverNodeStatus;
  errorMessage?: string;
}

export type FactionNodeType = Node<FactionNodeData>;

const factionTypeLabels: Record<string, string> = {
  kingdom: 'Kingdom',
  empire: 'Empire',
  guild: 'Guild',
  cult: 'Cult',
  corporation: 'Corporation',
  military: 'Military',
  religious: 'Religious',
  criminal: 'Criminal',
  academic: 'Academic',
  merchant: 'Merchant',
  tribal: 'Tribal',
  revolutionary: 'Revolutionary',
  secret_society: 'Secret Society',
  adventurer_group: 'Adventurer Group',
  noble_house: 'Noble House',
};

const alignmentColors: Record<string, string> = {
  lawful_good: 'border-yellow-400/50 text-yellow-200',
  neutral_good: 'border-green-400/50 text-green-200',
  chaotic_good: 'border-cyan-400/50 text-cyan-200',
  lawful_neutral: 'border-blue-400/50 text-blue-200',
  true_neutral: 'border-gray-400/50 text-gray-200',
  chaotic_neutral: 'border-orange-400/50 text-orange-200',
  lawful_evil: 'border-purple-400/50 text-purple-200',
  neutral_evil: 'border-rose-400/50 text-rose-200',
  chaotic_evil: 'border-red-400/50 text-red-200',
};

function formatAlignment(alignment: string): string {
  return alignment
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export function FactionNode({ data, id, selected }: NodeProps<FactionNodeType>) {
  const alignmentClass = alignmentColors[data.alignment] ?? 'border-gray-400/50 text-gray-200';

  return (
    <WeaverNode
      nodeId={id}
      nodeType="faction"
      status={data.status}
      selected={selected}
      className="w-60 cursor-grab active:cursor-grabbing border-amber-500/50 bg-gradient-to-br from-amber-950/80 to-orange-950/80"
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-amber-400"
        data-testid="weaver-handle-target"
      />
      <CardContent className="p-3">
        <div className="mb-2 flex items-start gap-2">
          <Shield className="mt-0.5 h-4 w-4 text-amber-400" />
          <div className="flex-1">
            <h4 className="text-sm font-medium text-amber-100">{data.name}</h4>
            <Badge variant="outline" className="mt-1 border-amber-400/50 text-xs text-amber-200">
              {factionTypeLabels[data.faction_type] ?? data.faction_type}
            </Badge>
          </div>
        </div>
        <p className="mb-2 line-clamp-2 text-xs text-amber-200/70">{data.description}</p>
        <div className="mb-2 flex items-center gap-2">
          <Badge variant="outline" className={`text-xs ${alignmentClass}`}>
            {formatAlignment(data.alignment)}
          </Badge>
        </div>
        <div className="flex items-center justify-between text-xs text-amber-300/60">
          <div className="flex items-center gap-1" title="Influence">
            <span>Influence: {data.influence}%</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1" title="Allies">
              <Users className="h-3 w-3 text-green-400" />
              <span>{data.ally_count}</span>
            </div>
            <div className="flex items-center gap-1" title="Enemies">
              <Swords className="h-3 w-3 text-red-400" />
              <span>{data.enemy_count}</span>
            </div>
          </div>
        </div>
        {data.values.length > 0 ? (
          <div className="mt-2 flex flex-wrap gap-1">
            {data.values.slice(0, 2).map((value) => (
              <Badge key={value} variant="secondary" className="text-xs bg-amber-800/50">
                {value}
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
        className="!bg-amber-400"
        data-testid="weaver-handle-source"
      />
    </WeaverNode>
  );
}
