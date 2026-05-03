import type { PropsWithChildren, ReactNode } from 'react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface PanelProps {
  title: string;
  eyebrow?: string;
  actions?: ReactNode;
  testId?: string;
}

export function Panel({
  title,
  eyebrow,
  actions,
  testId,
  children,
}: PropsWithChildren<PanelProps>) {
  return (
    <Card className="border-border/70 bg-card/95 shadow-xl backdrop-blur" data-testid={testId}>
      <CardHeader className="flex flex-row items-start justify-between gap-4 space-y-0">
        <div>
          {eyebrow ? (
            <CardDescription className="text-[0.68rem] uppercase tracking-[0.18em] text-muted-foreground">
              {eyebrow}
            </CardDescription>
          ) : null}
          <CardTitle className="text-lg">{title}</CardTitle>
        </div>
        {actions ? <div className="flex items-start gap-2">{actions}</div> : null}
      </CardHeader>
      <CardContent className="grid gap-4">{children}</CardContent>
    </Card>
  );
}
