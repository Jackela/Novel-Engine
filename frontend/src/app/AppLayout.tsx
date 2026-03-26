import { Outlet } from 'react-router-dom';

export function AppLayout() {
  return (
    <div className="app-shell">
      <div className="app-shell__aurora app-shell__aurora--left" />
      <div className="app-shell__aurora app-shell__aurora--right" />
      <Outlet />
    </div>
  );
}
