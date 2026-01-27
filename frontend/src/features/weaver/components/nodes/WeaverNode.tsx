/**
 * WeaverNode - Shared wrapper for Weaver node visuals and state styling
 */
import type { ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';
import { Card } from '@/shared/components/ui';
import { cn } from '@/lib/utils';
import type { WeaverNodeStatus } from '../../types';
import { nodeStatusClasses, resolveNodeStatus } from './nodeStyles';

interface WeaverNodeProps {
  nodeId: string;
  nodeType: string;
  status?: WeaverNodeStatus | undefined;
  selected?: boolean;
  className?: string;
  children: ReactNode;
}

export function WeaverNode({
  nodeId,
  nodeType,
  status,
  selected,
  className,
  children,
}: WeaverNodeProps) {
  const resolvedStatus = resolveNodeStatus(status, selected);
  return (
    <Card
      className={cn('weaver-node', nodeStatusClasses[resolvedStatus], className)}
      data-testid="weaver-node"
      data-node-type={nodeType}
      data-node-id={nodeId}
      data-node-status={resolvedStatus}
    >
      {resolvedStatus === 'error' && (
        <div className="weaver-node-alert" aria-label="Node error">
          <AlertTriangle className="h-4 w-4" />
        </div>
      )}
      {children}
    </Card>
  );
}
