import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { Button } from '@/components/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/features/auth/useAuth';
import type { SessionState } from '@/app/types/auth';

function studioLocation(session: SessionState) {
  const searchParams = new URLSearchParams();
  if (session.lastWorkspaceId) searchParams.set('workspace', session.lastWorkspaceId);
  if (session.lastJobId) searchParams.set('job', session.lastJobId);
  searchParams.set('view', session.lastView ?? 'workspace');
  const query = searchParams.toString();
  return query ? `/studio?${query}` : '/studio';
}

export function LoginPage() {
  const navigate = useNavigate();
  const { sessions, signIn, signInAsGuest, switchSession } = useAuth();
  const [email, setEmail] = useState('operator@novel.engine');
  const [password, setPassword] = useState('demo-password');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const resumableSessions = sessions.slice(0, 4);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const session = await signIn({ email, password });
      navigate(studioLocation(session));
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Unable to sign in.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGuest = async () => {
    setIsSubmitting(true);
    setError(null);

    try {
      const session = await signInAsGuest();
      navigate(studioLocation(session));
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Unable to create guest session.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResume = async (sessionId: string) => {
    setIsSubmitting(true);
    setError(null);

    try {
      const session = await switchSession(sessionId);
      navigate(studioLocation(session));
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Unable to resume the saved workspace.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="mx-auto grid w-full max-w-7xl gap-6 px-4 py-8 md:px-6 md:py-10" data-testid="auth-login-page">
      <div className="grid gap-4 lg:grid-cols-[1.1fr,0.9fr]">
        <Card className="shadow-xl">
          <CardHeader>
            <CardTitle className="text-3xl tracking-tight md:text-4xl">Authenticate and enter studio</CardTitle>
            <CardDescription>
              Sign in against canonical backend auth, or continue as guest for fast flow validation.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="grid gap-4" onSubmit={handleSubmit}>
              <div className="grid gap-2">
                <Label htmlFor="auth-email">Email</Label>
                <Input
                  autoComplete="email"
                  data-testid="auth-login-email"
                  id="auth-email"
                  onChange={(event) => setEmail(event.target.value)}
                  type="email"
                  value={email}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="auth-password">Password</Label>
                <Input
                  autoComplete="current-password"
                  data-testid="auth-login-password"
                  id="auth-password"
                  onChange={(event) => setPassword(event.target.value)}
                  type="password"
                  value={password}
                />
              </div>

              {error ? (
                <p className="text-sm text-destructive" data-testid="auth-login-error">
                  {error}
                </p>
              ) : null}

              <div className="flex flex-wrap gap-2">
                <Button data-testid="auth-login-submit" disabled={isSubmitting} type="submit">
                  {isSubmitting ? 'Signing in...' : 'Sign in'}
                </Button>
                <Button
                  data-testid="auth-login-guest"
                  disabled={isSubmitting}
                  onClick={handleGuest}
                  type="button"
                  variant="secondary"
                >
                  Continue as guest
                </Button>
              </div>

              <Link className="text-sm text-muted-foreground underline-offset-2 hover:underline" data-testid="auth-login-back-home" to="/">
                Back to home
              </Link>
            </form>
          </CardContent>
        </Card>

        <Card data-testid="auth-login-note">
          <CardHeader>
            <CardTitle>Session model</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>Signed-in users run in stable `user-*` workspaces.</p>
            <p>Guest sessions stay isolated and disposable for draft/testing flows.</p>
            <p>The studio preserves library state, mutable workspace state, and immutable playback state separately.</p>
          </CardContent>
        </Card>
      </div>

      {resumableSessions.length ? (
        <Card data-testid="auth-login-session-catalog">
          <CardHeader>
            <CardTitle>Resume a saved session</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2">
            {resumableSessions.map((session) => (
              <button
                className="rounded-lg border border-border/70 bg-secondary/20 px-4 py-3 text-left transition hover:bg-secondary/35"
                data-testid={`auth-login-resume-session-${session.id}`}
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
