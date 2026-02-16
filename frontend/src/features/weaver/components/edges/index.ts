/**
 * Custom edge types for Weaver canvas
 */
import { memo } from 'react';
import ForeshadowingEdge from './ForeshadowingEdge';

// Export all edge types
export const edgeTypes = {
  foreshadowing: memo(ForeshadowingEdge),
};

export type { ForeshadowingEdgeData } from './ForeshadowingEdge';
