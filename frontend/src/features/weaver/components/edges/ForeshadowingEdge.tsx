/**
 * ForeshadowingEdge - Custom edge for visualizing Chekhov's Gun connections (DIR-053)
 *
 * Displays dashed curved lines between setup and payoff scenes with color-coded status:
 * - Gold/Yellow: PLANTED (setup active, awaiting payoff)
 * - Green: PAID_OFF (setup successfully resolved)
 * - Red: ABANDONED (setup dropped without payoff)
 */
import { memo } from 'react';
import { EdgeLabelRenderer, type EdgeProps, getBezierPath } from '@xyflow/react';
import type { ForeshadowingResponse } from '@/types/schemas';

// Status color mapping
const STATUS_COLORS = {
  planted: {
    stroke: 'rgb(234, 179, 8)', // gold-500
    bg: 'rgba(234, 179, 8, 0.1)',
    label: 'bg-yellow-500/10 border-yellow-500 text-yellow-500',
  },
  paid_off: {
    stroke: 'rgb(34, 197, 94)', // green-500
    bg: 'rgba(34, 197, 94, 0.1)',
    label: 'bg-green-500/10 border-green-500 text-green-500',
  },
  abandoned: {
    stroke: 'rgb(239, 68, 68)', // red-500
    bg: 'rgba(239, 68, 68, 0.1)',
    label: 'bg-red-500/10 border-red-500 text-red-500',
  },
} as const;

// Edge data interface
export interface ForeshadowingEdgeData {
  foreshadowing: ForeshadowingResponse;
}

/**
 * Custom edge component for foreshadowing connections
 *
 * Features:
 * - Dashed line with status-based coloring
 * - Curved bezier path for visual clarity
 * - Tooltip showing description on hover
 * - Arrow marker at payoff end
 */
function ForeshadowingEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected,
}: EdgeProps) {
  const foreshadowing = (data as ForeshadowingEdgeData | undefined)?.foreshadowing;
  if (!foreshadowing) {
    return null;
  }

  const status = foreshadowing.status as keyof typeof STATUS_COLORS;
  const colors = STATUS_COLORS[status] || STATUS_COLORS.planted;

  // Calculate curved path
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  // Calculate midpoint for label
  const midX = (sourceX + targetX) / 2;
  const midY = (sourceY + targetY) / 2;

  return (
    <>
      {/* Edge path */}
      <path
        id={id}
        d={edgePath}
        fill="none"
        stroke={colors.stroke}
        strokeWidth={selected ? 3 : 2}
        strokeDasharray="5,5" // Dashed line
        className="opacity-80 transition-opacity hover:opacity-100"
        style={
          selected ? { filter: `drop-shadow(0 0 4px ${colors.stroke})` } : undefined
        }
      />

      {/* Edge label with description tooltip */}
      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${midX}px, ${midY}px)`,
            pointerEvents: 'all',
          }}
          className="group"
        >
          {/* Tooltip on hover */}
          <div className="absolute bottom-full left-1/2 z-50 mb-2 hidden -translate-x-1/2 group-hover:block">
            <div
              className={`${colors.label} max-w-xs rounded-lg border px-3 py-2 shadow-lg`}
            >
              <p className="mb-1 text-xs font-medium">Foreshadowing</p>
              <p className="whitespace-pre-wrap text-xs">{foreshadowing.description}</p>
              <p className="mt-1 text-xs opacity-70">
                Status: {status.replace('_', ' ').toUpperCase()}
              </p>
            </div>
            {/* Arrow */}
            <div className="mx-auto -mt-1 h-2 w-2 rotate-45 bg-current" />
          </div>

          {/* Visual indicator dot */}
          <div
            className={`h-3 w-3 rounded-full border-2 transition-all ${
              selected ? 'scale-125' : 'group-hover:scale-110'
            }`}
            style={{
              backgroundColor: colors.bg,
              borderColor: colors.stroke,
            }}
            title={foreshadowing.description}
          />
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

/**
 * Memoized edge component to prevent unnecessary re-renders
 */
export default memo(ForeshadowingEdge);
