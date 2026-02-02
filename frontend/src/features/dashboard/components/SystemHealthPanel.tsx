/**
 * SystemHealthPanel - Simple system health summary for dashboard tests
 */
import { ShieldCheck, Activity, Gauge } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/shared/components/ui/Card';

export function SystemHealthPanel() {
  return (
    <Card className="h-full min-h-[140px]" data-testid="system-health">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <ShieldCheck className="h-4 w-4 text-primary" />
          System Health
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between rounded-md bg-muted/30 px-3 py-2 text-sm">
          <span className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-green-500" />
            Engine Status
          </span>
          <span className="font-medium text-green-500">Healthy</span>
        </div>
        <div className="flex items-center justify-between rounded-md bg-muted/30 px-3 py-2 text-sm">
          <span className="flex items-center gap-2">
            <Gauge className="h-4 w-4 text-blue-500" />
            Load
          </span>
          <span className="font-medium">42%</span>
        </div>
      </CardContent>
    </Card>
  );
}
