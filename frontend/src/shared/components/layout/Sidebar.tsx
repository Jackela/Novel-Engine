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
import { cn } from '@/lib/utils';

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

export function Sidebar({ open, collapsed, onClose, onToggleCollapse }: SidebarProps) {
  const routerState = useRouterState();
  const currentPath = routerState.location.pathname;

  return (
    <aside
      className={cn(
        'fixed inset-y-0 left-0 z-50 flex flex-col border-r border-border bg-card',
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
      <SidebarHeader
        collapsed={collapsed}
        onClose={onClose}
        onToggleCollapse={onToggleCollapse}
      />
      <SidebarNav collapsed={collapsed} currentPath={currentPath} onClose={onClose} />
      <SidebarFooter collapsed={collapsed} />
    </aside>
  );
}

interface SidebarHeaderProps {
  collapsed: boolean;
  onClose: () => void;
  onToggleCollapse: () => void;
}

function SidebarHeader({ collapsed, onClose, onToggleCollapse }: SidebarHeaderProps) {
  return (
    <div className="flex h-16 items-center justify-between border-b border-border px-4">
      {!collapsed && (
        <Link
          to="/"
          className="text-xl font-bold text-foreground transition-colors hover:text-primary"
        >
          Novel Engine
        </Link>
      )}

      <button
        type="button"
        className="rounded-md p-2 hover:bg-accent lg:hidden"
        onClick={onClose}
        aria-label="Close sidebar"
      >
        <X className="h-5 w-5" />
      </button>

      <button
        type="button"
        className="hidden rounded-md p-2 hover:bg-accent lg:flex"
        onClick={onToggleCollapse}
        aria-label={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
      >
        {collapsed ? (
          <ChevronRight className="h-5 w-5" />
        ) : (
          <ChevronLeft className="h-5 w-5" />
        )}
      </button>
    </div>
  );
}

interface SidebarNavProps {
  collapsed: boolean;
  currentPath: string;
  onClose: () => void;
}

function SidebarNav({ collapsed, currentPath, onClose }: SidebarNavProps) {
  return (
    <nav className="flex-1 space-y-1 overflow-y-auto p-2">
      {navItems.map((item) => (
        <SidebarNavItem
          key={item.path}
          collapsed={collapsed}
          currentPath={currentPath}
          onClose={onClose}
          item={item}
        />
      ))}
    </nav>
  );
}

interface SidebarNavItemProps {
  item: (typeof navItems)[number];
  collapsed: boolean;
  currentPath: string;
  onClose: () => void;
}

function SidebarNavItem({
  item,
  collapsed,
  currentPath,
  onClose,
}: SidebarNavItemProps) {
  const isActive = currentPath === item.path;
  const Icon = item.icon;

  return (
    <Link
      to={item.path}
      className={cn(
        'flex items-center gap-3 rounded-lg px-3 py-2',
        'transition-colors duration-200',
        'hover:bg-accent hover:text-accent-foreground',
        isActive ? 'bg-primary/10 font-medium text-primary' : 'text-muted-foreground',
        collapsed && 'justify-center'
      )}
      onClick={onClose}
      aria-current={isActive ? 'page' : undefined}
    >
      <Icon className="h-5 w-5 flex-shrink-0" />
      {!collapsed && <span>{item.label}</span>}
    </Link>
  );
}

function SidebarFooter({ collapsed }: { collapsed: boolean }) {
  return (
    <div className="border-t border-border p-4">
      {!collapsed && (
        <p className="text-center text-xs text-muted-foreground">Novel Engine v3.0</p>
      )}
    </div>
  );
}
