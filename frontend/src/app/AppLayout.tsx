import { NavLink, Outlet } from 'react-router-dom';

import { useAuth } from '@/features/auth/useAuth';

function navLinkClassName({ isActive }: { isActive: boolean }) {
  return `app-shell__nav-link${isActive ? ' app-shell__nav-link--active' : ''}`;
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
      : session?.workspaceId ?? 'Start from landing or login';

  return (
    <div className="app-shell">
      <div className="app-shell__aurora app-shell__aurora--left" />
      <div className="app-shell__aurora app-shell__aurora--right" />
      <header className="app-shell__chrome" data-testid="app-shell-chrome">
        <div className="app-shell__brand">
          <p className="app-shell__brand-mark">Novel Engine</p>
          <div>
            <strong>Author shell</strong>
            <p>One entry surface, one story API, one immutable run trail.</p>
          </div>
        </div>

        <nav className="app-shell__nav" data-testid="app-shell-nav">
          <NavLink className={navLinkClassName} to="/">
            Home
          </NavLink>
          <NavLink className={navLinkClassName} to="/login">
            Login
          </NavLink>
          {session ? (
            <NavLink className={navLinkClassName} to="/story">
              Workshop
            </NavLink>
          ) : null}
        </nav>

        <div className="app-shell__session" data-testid="app-shell-session">
          <strong>{sessionLabel}</strong>
          <span>{sessionMeta}</span>
        </div>
      </header>
      <Outlet />
    </div>
  );
}
