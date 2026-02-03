import type { Edge, Node } from '@xyflow/react';

export type WeaverNodeStatus = 'idle' | 'active' | 'loading' | 'error';

export type WeaverNodeData = {
  label: string;
  status?: WeaverNodeStatus;
};

export type WeaverNode = Node<WeaverNodeData>;
export type WeaverEdge = Edge;

/**
 * Scene node data interface
 */
export interface SceneNodeData extends Record<string, unknown> {
  title: string;
  sceneType: string;
  content: string;
  summary: string;
  visualPrompt: string;
  status?: WeaverNodeStatus;
  errorMessage?: string;
  /** Plotlines associated with this scene (DIR-050) */
  plotlines?: Array<{ id: string; name: string; color: string }>;
}
