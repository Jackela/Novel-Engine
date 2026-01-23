/**
 * DashboardShell - Dashboard layout orchestrator
 * Manages panel arrangement and responsive layout
 */
import { Suspense } from 'react';
import { cn } from '@/lib/utils';
import { LoadingSpinner } from '@/shared/components/feedback';

// Lazy load panels for code splitting
import { lazy } from 'react';

const WorldPanel = lazy(() => import('./panels/WorldPanel'));
const NetworkPanel = lazy(() => import('./panels/NetworkPanel'));
const TimelinePanel = lazy(() => import('./panels/TimelinePanel'));
const NarrativePanel = lazy(() => import('./panels/NarrativePanel'));
const AnalyticsPanel = lazy(() => import('./panels/AnalyticsPanel'));
const SignalsPanel = lazy(() => import('./panels/SignalsPanel'));

// Panel loading fallback
function PanelFallback() {
  return (
    <div className="flex h-full min-h-[200px] items-center justify-center">
      <LoadingSpinner size="sm" />
    </div>
  );
}

export function DashboardShell() {
  return (
    <div className="space-y-6" data-testid="dashboard-layout">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Monitor your narrative engine in real-time
          </p>
        </div>
      </div>

      {/* Bento grid layout */}
      <div
        className={cn(
          'grid gap-4',
          // Mobile: single column
          'grid-cols-1',
          // Tablet: 2 columns
          'md:grid-cols-2',
          // Desktop: 4 columns with custom spans
          'lg:grid-cols-4'
        )}
        data-testid="bento-grid"
      >
        {/* World State Panel - Large, spans 2 cols */}
        <div className="lg:col-span-2 lg:row-span-2">
          <Suspense fallback={<PanelFallback />}>
            <WorldPanel />
          </Suspense>
        </div>

        {/* Network Panel - Medium */}
        <div className="lg:col-span-2">
          <Suspense fallback={<PanelFallback />}>
            <NetworkPanel />
          </Suspense>
        </div>

        {/* Timeline Panel - Full width */}
        <div className="lg:col-span-2">
          <Suspense fallback={<PanelFallback />}>
            <TimelinePanel />
          </Suspense>
        </div>

        {/* Narrative Panel - Medium */}
        <div className="lg:col-span-2">
          <Suspense fallback={<PanelFallback />}>
            <NarrativePanel />
          </Suspense>
        </div>

        {/* Analytics Panel - Small */}
        <div>
          <Suspense fallback={<PanelFallback />}>
            <AnalyticsPanel />
          </Suspense>
        </div>

        {/* Signals Panel - Small */}
        <div>
          <Suspense fallback={<PanelFallback />}>
            <SignalsPanel />
          </Suspense>
        </div>
      </div>
    </div>
  );
}
