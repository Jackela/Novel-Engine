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
  return <span className={`status-pill status-pill--${tone}`}>{children}</span>;
}
