import type { Edge, Node } from '@xyflow/react';

export type WeaverNodeData = {
  label: string;
};

export type WeaverNode = Node<WeaverNodeData>;
export type WeaverEdge = Edge;
