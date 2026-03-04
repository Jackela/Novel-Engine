/**
 * RumorVeracityBadge Component
 *
 * Displays a veracity badge with icon and label based on truth value.
 * Extracted from TavernBoard to reduce JSX nesting depth.
 */
import React from 'react';
import {
  CheckCircle,
  HelpCircle,
  AlertTriangle,
  XCircle,
} from 'lucide-react';
import { Badge } from '@/shared/components/ui/Badge';

interface RumorVeracityBadgeProps {
  truthValue: number;
}

type VeracityTier = 'Confirmed' | 'Likely True' | 'Uncertain' | 'Likely False' | 'False';

interface VeracityConfig {
  label: VeracityTier;
  colorClass: string;
  icon: React.ReactNode;
  description: string;
}

// Color coding based on truth value ranges
const VERACITY_CONFIGS: Record<VeracityTier, VeracityConfig> = {
  Confirmed: {
    label: 'Confirmed',
    colorClass: 'bg-green-500/20 text-green-700 dark:text-green-300 border-green-500/30',
    icon: <CheckCircle className="h-3.5 w-3.5" aria-hidden="true" />,
    description: 'Verified truth (80-100%)',
  },
  'Likely True': {
    label: 'Likely True',
    colorClass: 'bg-lime-500/20 text-lime-700 dark:text-lime-300 border-lime-500/30',
    icon: <CheckCircle className="h-3.5 w-3.5" aria-hidden="true" />,
    description: 'Probably true (60-79%)',
  },
  Uncertain: {
    label: 'Uncertain',
    colorClass: 'bg-yellow-500/20 text-yellow-700 dark:text-yellow-300 border-yellow-500/30',
    icon: <HelpCircle className="h-3.5 w-3.5" aria-hidden="true" />,
    description: 'Unknown validity (40-59%)',
  },
  'Likely False': {
    label: 'Likely False',
    colorClass: 'bg-orange-500/20 text-orange-700 dark:text-orange-300 border-orange-500/30',
    icon: <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />,
    description: 'Probably false (20-39%)',
  },
  False: {
    label: 'False',
    colorClass: 'bg-gray-500/20 text-gray-700 dark:text-gray-300 border-gray-500/30',
    icon: <XCircle className="h-3.5 w-3.5" aria-hidden="true" />,
    description: 'Verified false or debunked (0-19%)',
  },
};

/**
 * Get veracity tier based on truth value percentage.
 */
function getVeracityTier(truthValue: number): VeracityTier {
  if (truthValue >= 80) return 'Confirmed';
  if (truthValue >= 60) return 'Likely True';
  if (truthValue >= 40) return 'Uncertain';
  if (truthValue >= 20) return 'Likely False';
  return 'False';
}

export function RumorVeracityBadge({ truthValue }: RumorVeracityBadgeProps) {
  const veracityTier = getVeracityTier(truthValue);
  const config = VERACITY_CONFIGS[veracityTier];

  return (
    <Badge
      variant="outline"
      className={`flex items-center gap-1.5 px-2 py-1 ${config.colorClass}`}
      aria-label={`Truth value: ${config.label}. ${config.description}`}
      title={config.description}
    >
      {config.icon}
      <span className="text-xs font-medium">{config.label}</span>
    </Badge>
  );
}
