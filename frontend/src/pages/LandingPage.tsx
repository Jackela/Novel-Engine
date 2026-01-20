/**
 * LandingPage - Welcome page for the application
 */
import { useEffect } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { Rocket, Monitor, BarChart3, Shield, BookOpen, AlertCircle } from 'lucide-react';
import { Button, Card, CardContent, Badge } from '@/shared/components/ui';
import { useAuth } from '@/features/auth';

const FEATURES = [
  {
    icon: Monitor,
    title: 'Live Orchestration',
    desc: 'Real-time control over narrative turns and character decisions.',
  },
  {
    icon: BarChart3,
    title: 'Adaptive Analytics',
    desc: 'Deep insight into plot progression and character relationships.',
  },
  {
    icon: Shield,
    title: 'Secure Environment',
    desc: 'Air-gapped simulation sandbox for safe narrative testing.',
  },
];

function FeatureCard({ icon: Icon, title, desc }: { icon: typeof Monitor; title: string; desc: string }) {
  return (
    <div className="flex items-start gap-3" data-testid="feature-card">
      <div className="w-9 h-9 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
        <Icon className="h-4 w-4 text-primary" />
      </div>
      <div>
        <h3 className="font-semibold">{title}</h3>
        <p className="text-sm text-muted-foreground">{desc}</p>
      </div>
    </div>
  );
}

function FeaturePanel() {
  return (
    <Card>
      <CardContent className="p-6 space-y-6">
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-widest text-muted-foreground">Capabilities</p>
          <h2 className="text-lg font-semibold">Built for operators, not dashboards.</h2>
          <p className="text-sm text-muted-foreground">
            Minimal surfaces, precise hierarchy, and legible telemetry across every scale.
          </p>
        </div>

        <div className="h-px bg-border" />

        <div className="space-y-4">
          {FEATURES.map((feature) => (
            <FeatureCard key={feature.title} {...feature} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function HeroBadge() {
  return (
    <div
      data-testid="version-chip"
      className="inline-flex items-center gap-2 px-4 py-2 rounded-full border bg-background text-sm font-medium tracking-wider uppercase"
    >
      <BookOpen className="h-4 w-4 text-primary" />
      Novel Engine
    </div>
  );
}

function HeroTitle() {
  return (
    <h1 className="text-4xl sm:text-5xl md:text-6xl font-semibold tracking-tight leading-tight">
      Narrative Engine
      <span className="block text-primary">calm control for complex stories.</span>
    </h1>
  );
}

function HeroDescription() {
  return (
    <p className="text-lg text-muted-foreground max-w-xl leading-relaxed">
      Direct complex storylines across Meridian Station. Monitor character networks, guide event
      cascades, and watch your narrative evolve in real time.
    </p>
  );
}

interface HeroActionsProps {
  isLoading: boolean;
  error: Error | null;
  onLaunch: () => void;
}

function HeroActions({ isLoading, error, onLaunch }: HeroActionsProps) {
  const navigate = useNavigate();

  return (
    <div className="space-y-4">
      {error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-destructive/10 text-destructive max-w-lg">
          <AlertCircle className="h-4 w-4" />
          <span className="text-sm">{error.message || 'Failed to connect to backend.'}</span>
          <Button variant="ghost" size="sm" onClick={onLaunch} disabled={isLoading}>
            Retry
          </Button>
        </div>
      )}
      <div className="flex flex-col sm:flex-row gap-3">
        <Button
          size="lg"
          onClick={onLaunch}
          disabled={isLoading}
          data-testid="cta-launch"
          className="rounded-full px-8"
        >
          <Rocket className="h-4 w-4 mr-2" />
          {isLoading ? 'Launching...' : 'Launch Engine'}
        </Button>
        <Button
          variant="ghost"
          onClick={() => navigate({ to: '/login' })}
          className="text-muted-foreground"
        >
          Already have an account? Login
        </Button>
      </div>
    </div>
  );
}

export default function LandingPage() {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading, error, loginAsGuest } = useAuth();

  useEffect(() => {
    if (isAuthenticated) {
      navigate({ to: '/dashboard' });
    }
  }, [isAuthenticated, navigate]);

  const handleLaunch = async () => {
    await loginAsGuest();
  };

  return (
    <main
      id="main-content"
      className="min-h-screen flex items-center py-16 md:py-20"
    >
      <div className="container mx-auto px-4 max-w-6xl">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-10 md:gap-16 items-center">
          {/* Hero Section */}
          <div className="md:col-span-7 space-y-8">
            <HeroBadge />
            <HeroTitle />
            <HeroDescription />
            <HeroActions isLoading={isLoading} error={error} onLaunch={handleLaunch} />
          </div>

          {/* Feature Panel */}
          <div className="md:col-span-5">
            <FeaturePanel />
          </div>
        </div>
      </div>
    </main>
  );
}
