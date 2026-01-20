/**
 * Sidebar - Navigation sidebar component
 * Responsive: drawer on mobile, fixed on desktop
 */
import { Link, useRouterState } from '@tanstack/react-router';
import {
  LayoutDashboard,
  Users,
  Swords,
  BookOpen,
  GitBranch,
  ChevronLeft,
  ChevronRight,
  X,
} from 'lucide-react';
import { cn } from '@/shared/lib/utils';

interface SidebarProps {
  open: boolean;
  collapsed: boolean;
  onClose: () => void;
  onToggleCollapse: () => void;
}

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/characters', label: 'Characters', icon: Users },
  { path: '/campaigns', label: 'Campaigns', icon: Swords },
  { path: '/stories', label: 'Stories', icon: BookOpen },
  { path: '/weaver', label: 'Weaver', icon: GitBranch },
] as const;

export function Sidebar({
  open,
  collapsed,
  onClose,
  onToggleCollapse,
}: SidebarProps) {
  const routerState = useRouterState();
  const currentPath = routerState.location.pathname;

  return (
    <aside
      className={cn(
        'fixed inset-y-0 left-0 z-50 flex flex-col bg-card border-r border-border',
        'transition-all duration-300 ease-in-out',
        // Mobile: slide in/out
        'lg:translate-x-0',
        open ? 'translate-x-0' : '-translate-x-full',
        // Desktop: collapse/expand
        collapsed ? 'lg:w-16' : 'lg:w-64',
        // Mobile always full width when open
        'w-64'
      )}
      data-testid="sidebar-navigation"
      aria-label="Main navigation"
    >
      {/* Header */}
      <div className="flex items-center justify-between h-16 px-4 border-b border-border">
        {!collapsed && (
          <Link
            to="/dashboard"
            className="text-xl font-bold text-foreground hover:text-primary transition-colors"
          >
            Novel Engine
          </Link>
        )}

        {/* Mobile close button */}
        <button
          type="button"
          className="lg:hidden p-2 rounded-md hover:bg-accent"
          onClick={onClose}
          aria-label="Close sidebar"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Desktop collapse toggle */}
        <button
          type="button"
          className="hidden lg:flex p-2 rounded-md hover:bg-accent"
          onClick={onToggleCollapse}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? (
            <ChevronRight className="h-5 w-5" />
          ) : (
            <ChevronLeft className="h-5 w-5" />
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-2 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = currentPath === item.path;
          const Icon = item.icon;

          return (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg',
                'transition-colors duration-200',
                'hover:bg-accent hover:text-accent-foreground',
                isActive
                  ? 'bg-primary/10 text-primary font-medium'
                  : 'text-muted-foreground',
                collapsed && 'justify-center'
              )}
              onClick={onClose}
              aria-current={isActive ? 'page' : undefined}
            >
              <Icon className="h-5 w-5 flex-shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-border">
        {!collapsed && (
          <p className="text-xs text-muted-foreground text-center">
            Novel Engine v3.0
          </p>
        )}
      </div>
    </aside>
  );
}
