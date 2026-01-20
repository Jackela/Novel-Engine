/**
 * SignalsPanel - Real-time activity signals
 * Shows live events and system activity
 */
import { Activity, AlertCircle, CheckCircle, Info } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/shared/components/ui/Card';

const signals = [
  {
    id: 1,
    type: 'success',
    message: 'Turn #42 completed',
    time: '10s ago',
  },
  {
    id: 2,
    type: 'info',
    message: 'Character decision pending',
    time: '45s ago',
  },
  {
    id: 3,
    type: 'warning',
    message: 'High token usage detected',
    time: '2m ago',
  },
];

const iconMap = {
  success: CheckCircle,
  info: Info,
  warning: AlertCircle,
};

const colorMap = {
  success: 'text-green-500',
  info: 'text-blue-500',
  warning: 'text-yellow-500',
};

export default function SignalsPanel() {
  return (
    <Card className="h-full" data-testid="signals-panel">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Activity className="h-4 w-4 text-primary" />
          Signals
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {signals.map((signal) => {
            const Icon = iconMap[signal.type as keyof typeof iconMap];
            const colorClass = colorMap[signal.type as keyof typeof colorMap];

            return (
              <div
                key={signal.id}
                className="flex items-start gap-2 p-2 rounded-lg bg-muted/30"
              >
                <Icon className={`h-4 w-4 mt-0.5 ${colorClass}`} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm truncate">{signal.message}</p>
                  <p className="text-xs text-muted-foreground">{signal.time}</p>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
