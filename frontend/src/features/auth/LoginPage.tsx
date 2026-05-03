import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { Button } from '@/components/Button';
import { useAuth } from '@/features/auth/useAuth';
import type { SessionState } from '@/app/types';

function storyLocation(session: SessionState) {
  const searchParams = new URLSearchParams();
  if (session.lastStoryId) {
    searchParams.set('story', session.lastStoryId);
  }
  if (session.lastRunId) {
    searchParams.set('run', session.lastRunId);
  }
  searchParams.set('view', session.lastView ?? 'workspace');
  const query = searchParams.toString();
  return query ? `/story?${query}` : '/story';
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
      navigate(storyLocation(session));
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
      navigate(storyLocation(session));
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
      navigate(storyLocation(session));
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Unable to resume the saved workspace.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="auth-page" data-testid="login-page">
      <div className="auth-page__layout">
        <form className="auth-card" onSubmit={handleSubmit}>
          <p className="panel__eyebrow">Writer access</p>
          <h1 className="auth-card__title">Return to the story workshop</h1>
          <p className="auth-card__copy">
            Sign in against the canonical backend contract or continue with a guest workspace if
            you only need a fast draft session.
          </p>

          <label className="field">
            <span>Email</span>
            <input
              data-testid="login-email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              type="email"
              autoComplete="email"
            />
          </label>

          <label className="field">
            <span>Password</span>
            <input
              data-testid="login-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              autoComplete="current-password"
            />
          </label>

          {error ? <p className="form-error">{error}</p> : null}

          <div className="auth-card__actions">
            <Button type="submit" disabled={isSubmitting} data-testid="login-submit">
              {isSubmitting ? 'Signing in...' : 'Sign in'}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={handleGuest}
              disabled={isSubmitting}
            >
              Continue as guest writer
            </Button>
          </div>

          <Link className="auth-card__back" to="/" data-testid="login-back-to-landing">
            Back to landing
          </Link>
        </form>

        <section className="auth-note" data-testid="login-route-note">
          <p className="panel__eyebrow">What happens next</p>
          <h2 className="panel__title">Session identity is part of the product surface</h2>
          <p>
            Signed-in users move into a stable `user-*` workspace. Guest sessions remain isolated,
            disposable, and valid for flow debugging and first-pass drafting.
          </p>
          <ul>
            <li>The workshop keeps library state, current manuscript state, and run playback separate.</li>
            <li>Publish decisions depend on review gates, not hidden UI state.</li>
            <li>Browser automation uses this page to verify login, guest fallback, and return-to-landing flows.</li>
          </ul>
        </section>
      </div>

      {resumableSessions.length ? (
        <section className="landing__grid" data-testid="login-session-catalog">
          <article className="landing-card landing-card--wide">
            <h2>Resume a saved session</h2>
            <p>Use a previously validated guest or user workspace without re-entering the route manually.</p>
            <ul className="story-list">
              {resumableSessions.map((session) => (
                <li key={session.id} className="story-card">
                  <button
                    className="story-card__button"
                    type="button"
                    onClick={() => void handleResume(session.id)}
                    data-testid={`login-resume-session-${session.id}`}
                  >
                    <div className="story-card__header">
                      <strong>{session.activeWorkspace?.label ?? session.workspaceId}</strong>
                      <span>{session.kind}</span>
                    </div>
                    <p className="story-card__meta">
                      {session.user?.email ?? session.activeWorkspace?.summary ?? session.workspaceId}
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          </article>
        </section>
      ) : null}
    </main>
  );
}
