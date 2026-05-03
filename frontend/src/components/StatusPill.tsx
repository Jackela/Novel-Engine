import { Badge } from '@/components/ui/badge';

interface StatusPillProps {
  tone:
    | 'healthy'
    | 'degraded'
    | 'offline'
    | 'running'
    | 'paused'
    | 'idle'
    | 'draft'
    | 'completed';
  children: string;
}

export function StatusPill({ tone, children }: StatusPillProps) {
  const variant =
    tone === 'offline'
      ? 'destructive'
      : tone === 'degraded' || tone === 'paused'
        ? 'secondary'
        : 'outline';

  return (
    <Badge className="uppercase tracking-wide" variant={variant}>
      {children}
    </Badge>
  );
}
