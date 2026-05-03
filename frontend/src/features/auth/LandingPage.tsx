import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { Button } from '@/components/Button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/features/auth/useAuth';
import type { SessionState } from '@/app/types';

function studioLocation(session: SessionState) {
  const searchParams = new URLSearchParams();
  if (session.lastStoryId) searchParams.set('story', session.lastStoryId);
  if (session.lastRunId) searchParams.set('run', session.lastRunId);
  searchParams.set('view', session.lastView ?? 'workspace');
  const query = searchParams.toString();
  return query ? `/studio?${query}` : '/studio';
}

export function LandingPage() {
  const navigate = useNavigate();
  const { sessions, signInAsGuest, switchSession } = useAuth();
  const [isLaunching, setIsLaunching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const latestGuestSession = sessions.find((session) => session.kind === 'guest') ?? null;
  const resumableSessions = sessions.slice(0, 4);

  const handleLaunch = async () => {
    setIsLaunching(true);
    setError(null);

    try {
      const session = await signInAsGuest(latestGuestSession?.workspaceId);
      navigate(studioLocation(session));
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Unable to create guest session.');
    } finally {
      setIsLaunching(false);
    }
  };

  const handleResume = async (sessionId: string) => {
    setIsLaunching(true);
    setError(null);

    try {
      const session = await switchSession(sessionId);
      navigate(studioLocation(session));
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Unable to resume the saved workspace.');
    } finally {
      setIsLaunching(false);
    }
  };

  return (
    <main className="mx-auto grid w-full max-w-7xl gap-6 px-4 py-8 md:px-6 md:py-10" data-testid="auth-home-page">
      <section className="relative overflow-hidden rounded-2xl border border-border/70 bg-card/95 p-8 shadow-2xl md:p-12">
        <div className="pointer-events-none absolute -left-16 -top-12 h-56 w-56 rounded-full bg-primary/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-20 -right-12 h-64 w-64 rounded-full bg-chart-2/20 blur-3xl" />

        <Badge className="mb-4" variant="outline">
          Novel Engine / Entry Surface
        </Badge>
        <h1 className="max-w-4xl text-4xl leading-tight font-semibold tracking-tight md:text-6xl" data-testid="auth-home-title">
          Start cold, iterate fast, and keep publication evidence visible from first draft to final gate.
        </h1>
        <p className="mt-4 max-w-3xl text-base text-muted-foreground md:text-lg">
          The studio keeps session identity, mutable workspace, and immutable playback separate so the same
          flow works for humans and automation.
        </p>

        <div className="mt-6 flex flex-wrap gap-3">
          <Button
            data-testid="auth-home-launch-guest"
            disabled={isLaunching}
            onClick={handleLaunch}
          >
            {isLaunching ? 'Opening studio...' : 'Launch guest studio'}
          </Button>
          <Link className="inline-flex" data-testid="auth-home-go-login" to="/auth/login">
            <Button type="button" variant="secondary">
              Sign in
            </Button>
          </Link>
        </div>

        {error ? (
          <p className="mt-4 text-sm text-destructive" data-testid="auth-home-error">
            {error}
          </p>
        ) : null}
      </section>

      <section className="grid gap-4 md:grid-cols-3" data-testid="auth-home-journey">
        <Card>
          <CardHeader>
            <CardTitle>1. Enter</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Guest or signed-in sessions both resolve to a canonical studio contract.
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>2. Compose</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Create drafts, run pipeline stages, revise, export, and publish in one surface.
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>3. Audit</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Playback is immutable and addressable so run evidence survives refresh and deep links.
          </CardContent>
        </Card>
      </section>

      {resumableSessions.length ? (
        <Card data-testid="auth-home-session-catalog">
          <CardHeader>
            <CardTitle>Resume saved session</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2">
            {resumableSessions.map((session) => (
              <button
                className="rounded-lg border border-border/70 bg-secondary/20 px-4 py-3 text-left transition hover:bg-secondary/35"
                data-testid={`auth-home-resume-session-${session.id}`}
                key={session.id}
                onClick={() => void handleResume(session.id)}
                type="button"
              >
                <p className="text-sm font-medium">
                  {session.activeWorkspace?.label ?? session.workspaceId}
                </p>
                <p className="text-xs text-muted-foreground">
                  {session.user?.email ?? session.activeWorkspace?.summary ?? session.workspaceId}
                </p>
              </button>
            ))}
          </CardContent>
        </Card>
      ) : null}
    </main>
  );
}
