import type { Edge, Node } from '@xyflow/react';

export type WeaverNodeStatus = 'idle' | 'active' | 'loading' | 'error';

export type WeaverNodeData = {
  label: string;
  status?: WeaverNodeStatus;
};

export type WeaverNode = Node<WeaverNodeData>;
export type WeaverEdge = Edge;
