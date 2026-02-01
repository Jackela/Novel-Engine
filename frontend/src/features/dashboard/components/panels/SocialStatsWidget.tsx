/**
 * SocialStatsWidget - Social network statistics panel
 *
 * Displays key character metrics from social network analysis:
 * - Most Connected: Character with the most relationships
 * - Most Hated: Character with lowest average trust/romance
 * - Most Loved: Character with highest trust/romance weighted score
 *
 * Fetches data from /api/social/analysis endpoint.
 */
import { useEffect, useState } from 'react';
import { Users, Heart, HeartCrack, Network } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/shared/components/ui/Card';
import { getSocialAnalysis } from '@/lib/api';
import type { SocialAnalysisResponse } from '@/types/schemas';

interface StatItem {
  label: string;
  value: string | null;
  icon: React.ElementType;
  color: string;
  bgColor: string;
}

export default function SocialStatsWidget() {
  const [analysis, setAnalysis] = useState<SocialAnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchAnalysis() {
      try {
        const data = await getSocialAnalysis();
        setAnalysis(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load social analysis');
      } finally {
        setLoading(false);
      }
    }
    void fetchAnalysis();
  }, []);

  // Build stats from analysis data
  const stats: StatItem[] = [
    {
      label: 'Most Connected',
      value: analysis?.most_connected ?? null,
      icon: Network,
      color: 'text-blue-500',
      bgColor: 'bg-blue-500/10',
    },
    {
      label: 'Most Hated',
      value: analysis?.most_hated ?? null,
      icon: HeartCrack,
      color: 'text-red-500',
      bgColor: 'bg-red-500/10',
    },
    {
      label: 'Most Loved',
      value: analysis?.most_loved ?? null,
      icon: Heart,
      color: 'text-pink-500',
      bgColor: 'bg-pink-500/10',
    },
  ];

  // Format character ID to display name (e.g., "aria-shadowbane" -> "Aria Shadowbane")
  const formatCharacterName = (id: string | null): string => {
    if (!id) return 'None';
    return id
      .split('-')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <Card className="h-full" data-testid="social-stats-widget">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Users className="h-4 w-4 text-primary" />
          Social Network
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="animate-pulse rounded-lg bg-muted/30 p-3 h-14" />
            ))}
          </div>
        ) : error ? (
          <div className="text-sm text-muted-foreground text-center py-4">{error}</div>
        ) : (
          <div className="space-y-3">
            {stats.map((stat) => (
              <div
                key={stat.label}
                className="flex items-center justify-between rounded-lg bg-muted/30 p-3"
              >
                <div className="flex items-center gap-3">
                  <div className={`rounded-md p-1.5 ${stat.bgColor}`}>
                    <stat.icon className={`h-4 w-4 ${stat.color}`} />
                  </div>
                  <span className="text-sm text-muted-foreground">{stat.label}</span>
                </div>
                <span className="text-sm font-medium truncate max-w-[120px]">
                  {formatCharacterName(stat.value)}
                </span>
              </div>
            ))}

            {/* Network summary */}
            {analysis && (
              <div className="mt-4 grid grid-cols-2 gap-2 text-center">
                <div className="rounded-lg bg-muted/50 p-2">
                  <p className="text-lg font-bold">{analysis.total_characters}</p>
                  <p className="text-xs text-muted-foreground">Characters</p>
                </div>
                <div className="rounded-lg bg-muted/50 p-2">
                  <p className="text-lg font-bold">{analysis.total_relationships}</p>
                  <p className="text-xs text-muted-foreground">Relationships</p>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
