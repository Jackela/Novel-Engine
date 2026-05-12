import { NavLink, Outlet } from 'react-router-dom';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { useAuth } from '@/features/auth/useAuth';

function navLinkClassName({ isActive }: { isActive: boolean }) {
  return cn(
    'inline-flex items-center rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground',
    isActive && 'bg-secondary text-foreground',
  );
}

export function AppLayout() {
  const { session } = useAuth();
  const sessionLabel =
    session?.kind === 'user'
      ? session.user?.name ?? 'Signed in author'
      : session
        ? 'Guest workspace'
        : 'No active session';
  const sessionMeta =
    session?.kind === 'user'
      ? session.user?.email ?? session.workspaceId
      : session?.workspaceId ?? 'Start from home or auth login';

  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(75%_70%_at_20%_0%,hsl(var(--primary)/0.22),transparent_70%),radial-gradient(55%_55%_at_80%_10%,hsl(var(--chart-2)/0.22),transparent_70%),hsl(var(--background))]">
      <header
        className="sticky top-0 z-20 border-b border-border/60 bg-background/80 backdrop-blur"
        data-testid="shell-chrome"
      >
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-6 px-4 py-3 md:px-6">
          <div className="flex items-center gap-3">
            <Badge variant="outline">Novel Engine</Badge>
            <div className="hidden md:block">
              <p className="text-sm font-semibold">Studio Surface</p>
              <p className="text-xs text-muted-foreground">Canonical auth, story, and playback flow</p>
            </div>
          </div>

          <nav className="flex items-center gap-1" data-testid="shell-nav">
            <NavLink className={navLinkClassName} to="/">
              Home
            </NavLink>
            <NavLink className={navLinkClassName} to="/auth/login">
              Auth
            </NavLink>
            {session ? (
              <NavLink className={navLinkClassName} to="/studio">
                Studio
              </NavLink>
            ) : null}
          </nav>

          <div className="hidden min-w-0 max-w-sm text-right md:block" data-testid="shell-session">
            <p className="truncate text-sm font-medium">{sessionLabel}</p>
            <p className="truncate text-xs text-muted-foreground">{sessionMeta}</p>
          </div>
        </div>
      </header>

      <Outlet />
    </div>
  );
}
