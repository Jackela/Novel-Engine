import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import type { z } from 'zod';
import type { CharacterPsychologySchema } from '@/types/schemas';

type CharacterPsychology = z.infer<typeof CharacterPsychologySchema>;

type Props = {
  psychology: CharacterPsychology | null | undefined;
};

// OCEAN trait labels with abbreviated display names
const TRAIT_LABELS: Record<keyof CharacterPsychology, { short: string; full: string }> = {
  openness: { short: 'O', full: 'Openness' },
  conscientiousness: { short: 'C', full: 'Conscientiousness' },
  extraversion: { short: 'E', full: 'Extraversion' },
  agreeableness: { short: 'A', full: 'Agreeableness' },
  neuroticism: { short: 'N', full: 'Neuroticism' },
};

function getTraitLevel(value: number): string {
  if (value <= 30) return 'Low';
  if (value <= 70) return 'Average';
  return 'High';
}

function formatChartData(psychology: CharacterPsychology) {
  return (Object.keys(TRAIT_LABELS) as Array<keyof CharacterPsychology>).map((trait) => ({
    trait: TRAIT_LABELS[trait].short,
    fullName: TRAIT_LABELS[trait].full,
    value: psychology[trait],
    level: getTraitLevel(psychology[trait]),
  }));
}

type CustomTooltipProps = {
  active?: boolean;
  payload?: Array<{
    payload: {
      fullName: string;
      value: number;
      level: string;
    };
  }>;
};

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  const firstPayload = payload[0];
  if (!firstPayload) return null;

  const data = firstPayload.payload;
  return (
    <div className="bg-popover border rounded-md px-3 py-2 shadow-md">
      <p className="font-medium">{data.fullName}</p>
      <p className="text-sm text-muted-foreground">
        Score: {data.value} ({data.level})
      </p>
    </div>
  );
}

export default function PsychologyChart({ psychology }: Props) {
  if (!psychology) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground text-sm">
        No psychology data available.
      </div>
    );
  }

  const chartData = formatChartData(psychology);

  return (
    <div className="space-y-4">
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={chartData} cx="50%" cy="50%" outerRadius="80%">
            <PolarGrid stroke="hsl(var(--border))" />
            <PolarAngleAxis
              dataKey="trait"
              tick={{ fill: 'hsl(var(--foreground))', fontSize: 12 }}
            />
            <PolarRadiusAxis
              angle={90}
              domain={[0, 100]}
              tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }}
              tickCount={5}
            />
            <Radar
              name="Psychology"
              dataKey="value"
              stroke="hsl(var(--primary))"
              fill="hsl(var(--primary))"
              fillOpacity={0.3}
              strokeWidth={2}
            />
            <Tooltip content={<CustomTooltip />} />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div className="text-xs text-muted-foreground space-y-1">
        <p className="font-medium mb-2">OCEAN Traits Legend:</p>
        <div className="grid grid-cols-2 gap-1">
          {(Object.keys(TRAIT_LABELS) as Array<keyof CharacterPsychology>).map((trait) => (
            <div key={trait} className="flex items-center gap-2">
              <span className="font-medium w-4">{TRAIT_LABELS[trait].short}</span>
              <span>= {TRAIT_LABELS[trait].full}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
