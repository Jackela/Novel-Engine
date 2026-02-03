/**
 * AnalyticsPanel - Performance metrics
 * Shows generation statistics and performance data
 */
import { BarChart3, TrendingUp, Zap } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/shared/components/ui/Card';

const metrics = [
  { label: 'LCP', value: '1.2s', trend: '-8%', icon: Zap },
  { label: 'CLS', value: '0.03', trend: '-0.01', icon: BarChart3 },
  { label: 'INP', value: '180ms', trend: '-12%', icon: TrendingUp },
];

export default function AnalyticsPanel() {
  return (
    <Card className="h-full" data-testid="analytics-panel">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <BarChart3 className="h-4 w-4 text-primary" />
          Analytics
        </CardTitle>
      </CardHeader>
      <CardContent data-testid="performance-metrics">
        <div className="space-y-3">
          {metrics.map((metric) => {
            const Icon = metric.icon;
            const isPositive = metric.trend.startsWith('+');

            return (
              <div
                key={metric.label}
                className="flex items-center justify-between rounded-lg bg-muted/30 p-2"
              >
                <div className="flex items-center gap-2">
                  <Icon className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">{metric.label}</span>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium" data-testid="performance-metric-value">
                    {metric.value}
                  </p>
                  <p
                    className={`text-xs ${isPositive ? 'text-green-500' : 'text-red-500'}`}
                  >
                    {metric.trend}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
