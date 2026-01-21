import type { ReactNode } from 'react';

type WeaverLayoutProps = {
  children: ReactNode;
};

export function WeaverLayout({ children }: WeaverLayoutProps) {
  return (
    <div className="min-h-screen w-full bg-background text-foreground">
      <main className="h-full w-full">{children}</main>
    </div>
  );
}
