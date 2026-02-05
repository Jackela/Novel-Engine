/**
 * AppShell - Main application layout wrapper for protected routes
 *
 * Why: Provides the consistent app shell with sidebar navigation
 * and top bar. Children are rendered in the main content area.
 */
import { useState } from 'react';
import { cn } from '@/lib/utils';
import { Sidebar } from '@/shared/components/layout/Sidebar';
import { TopBar } from '@/shared/components/layout/TopBar';
import { DecisionDialog } from '@/features/decision/DecisionDialog';
import { ChatInterface } from '@/components/ChatInterface';
import { useMediaQuery } from '@/hooks/useMediaQuery';

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const isDesktop = useMediaQuery('(min-width: 1024px)');

  return (
    <div className="min-h-screen bg-background">
      {/* Mobile sidebar overlay */}
      {!isDesktop && sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Mobile sidebar drawer */}
      {!isDesktop && (
        <div
          className={cn('fixed inset-0 z-50', sidebarOpen ? 'block' : 'hidden')}
          data-testid="sidebar-drawer"
        >
          <Sidebar
            open={sidebarOpen}
            collapsed={false}
            onClose={() => setSidebarOpen(false)}
            onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
          />
        </div>
      )}

      {/* Desktop sidebar */}
      {isDesktop && (
        <div
          className="hidden lg:block lg:h-screen lg:w-64"
          data-testid="sidebar-desktop"
        >
          <Sidebar
            open
            collapsed={sidebarCollapsed}
            onClose={() => setSidebarOpen(false)}
            onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
          />
        </div>
      )}

      {/* Main content area */}
      <div
        className={cn(
          'flex min-h-screen flex-col transition-all duration-300',
          sidebarCollapsed ? 'lg:pl-16' : 'lg:pl-64'
        )}
      >
        <TopBar onMenuClick={() => setSidebarOpen(true)} />

        <main id="main-content" className="flex-1 p-4 lg:p-6" tabIndex={-1}>
          {children}
        </main>
        <DecisionDialog />
        <ChatInterface />
      </div>
    </div>
  );
}

export default AppShell;
