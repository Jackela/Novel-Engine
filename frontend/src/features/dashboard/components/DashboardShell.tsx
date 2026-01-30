/**
 * DashboardShell - Dashboard layout orchestrator
 * Manages panel arrangement and responsive layout
 */
import { Suspense, lazy } from 'react';
import { Link } from '@tanstack/react-router';
import { GitBranch, Globe, BookOpen, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { LoadingSpinner } from '@/shared/components/feedback';
import { Card, CardHeader, CardTitle, CardDescription } from '@/shared/components/ui/Card';

// Lazy load panels for code splitting

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

// Quick navigation cards to main sub-apps
const SUB_APPS = [
  {
    title: 'Story Weaver',
    description: 'Visual node-based story orchestration',
    icon: GitBranch,
    href: '/weaver',
    color: 'text-purple-500',
    bgColor: 'bg-purple-500/10',
  },
  {
    title: 'World Builder',
    description: 'Manage locations, characters, and world state',
    icon: Globe,
    href: '/world',
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/10',
  },
  {
    title: 'Narrative Studio',
    description: 'Write and generate story content',
    icon: BookOpen,
    href: '/story',
    color: 'text-green-500',
    bgColor: 'bg-green-500/10',
  },
] as const;

function QuickNavCards() {
  return (
    <div className="grid gap-4 md:grid-cols-3" data-testid="quick-nav-cards">
      {SUB_APPS.map((app) => (
        <Link key={app.href} to={app.href}>
          <Card className="group cursor-pointer transition-all hover:border-primary/50 hover:shadow-md">
            <CardHeader>
              <div className={cn('mb-2 inline-flex rounded-lg p-2', app.bgColor)}>
                <app.icon className={cn('h-6 w-6', app.color)} />
              </div>
              <CardTitle className="flex items-center justify-between">
                {app.title}
                <ArrowRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-1" />
              </CardTitle>
              <CardDescription>{app.description}</CardDescription>
            </CardHeader>
          </Card>
        </Link>
      ))}
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

      {/* Quick navigation to sub-apps */}
      <QuickNavCards />

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
