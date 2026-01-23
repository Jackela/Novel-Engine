import type { WeaverNodeStatus } from '../../types';

export const nodeStatusClasses: Record<WeaverNodeStatus, string> = {
  idle: 'node-idle',
  active: 'node-active',
  loading: 'node-loading',
  error: 'node-error',
};

export const resolveNodeStatus = (
  status?: WeaverNodeStatus,
  selected?: boolean
): WeaverNodeStatus => {
  if (status && status !== 'idle') return status;
  if (selected) return 'active';
  return status ?? 'idle';
};
