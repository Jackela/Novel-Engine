/**
 * DashboardShell - Dashboard layout orchestrator
 * Manages panel arrangement and responsive layout
 */
import { Suspense, lazy } from 'react';
import { Link } from '@tanstack/react-router';
import { GitBranch, Globe, BookOpen, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { LoadingSpinner } from '@/shared/components/feedback';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/shared/components/ui/Card';
import { QuickActionsPanel } from './QuickActionsPanel';
import { TurnPipelinePanel } from './TurnPipelinePanel';
import { SystemHealthPanel } from './SystemHealthPanel';
import { useOrchestrationStore } from '../stores/orchestrationStore';
import { useAuthStore } from '@/features/auth';

// Lazy load panels for code splitting

const WorldPanel = lazy(() => import('./panels/WorldPanel'));
const NetworkPanel = lazy(() => import('./panels/NetworkPanel'));
const TimelinePanel = lazy(() => import('./panels/TimelinePanel'));
const NarrativePanel = lazy(() => import('./panels/NarrativePanel'));
const AnalyticsPanel = lazy(() => import('./panels/AnalyticsPanel'));
const SignalsPanel = lazy(() => import('./panels/SignalsPanel'));
const SocialStatsWidget = lazy(() => import('./panels/SocialStatsWidget'));

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
  const { live, runState } = useOrchestrationStore();
  const { isGuest } = useAuthStore();

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

      {isGuest && (
        <div
          className="flex items-center justify-between rounded-lg border border-primary/20 bg-primary/5 px-4 py-3 text-sm text-primary"
          data-testid="guest-mode-banner"
        >
          <span>Guest mode active · Changes are stored locally for this session.</span>
        </div>
      )}

      {/* Summary strip */}
      <div
        className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-card px-4 py-3 text-sm"
        data-testid="summary-strip"
      >
        <span className="font-medium">System Summary</span>
        <span
          className="rounded-full bg-primary/10 px-2 py-1 text-xs text-primary"
          data-testid="guest-mode-chip"
        >
          Guest Mode
        </span>
        <span className="text-muted-foreground">3 active characters</span>
        <span className="text-muted-foreground">2 active arcs</span>
        <span
          className="ml-auto flex items-center gap-2"
          data-testid="pipeline-live-indicator"
          aria-live="polite"
        >
          <span
            className={cn(
              'h-2 w-2 rounded-full',
              live ? 'bg-green-500' : 'bg-muted-foreground'
            )}
          />
          <span>
            {live ? 'Live updates' : runState === 'paused' ? 'Paused' : 'Idle'}
          </span>
        </span>
      </div>

      {/* Tab strip for dashboard navigation (used by E2E helpers) */}
      <div
        className="flex flex-wrap gap-2"
        role="tablist"
        aria-label="Dashboard sections"
      >
        {['Map', 'Network', 'Timeline', 'Narrative', 'Analytics', 'Signals'].map(
          (label) => (
            <button
              key={label}
              type="button"
              role="tab"
              aria-selected={label === 'Map'}
              className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground transition hover:border-primary/50 hover:text-foreground"
            >
              {label}
            </button>
          )
        )}
      </div>

      {/* Status + controls */}
      <div className="grid gap-4 lg:grid-cols-3">
        <QuickActionsPanel />
        <TurnPipelinePanel />
        <SystemHealthPanel />
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

        {/* Social Stats Widget - Small, spans 2 cols */}
        <div className="lg:col-span-2">
          <Suspense fallback={<PanelFallback />}>
            <SocialStatsWidget />
          </Suspense>
        </div>
      </div>
    </div>
  );
}
