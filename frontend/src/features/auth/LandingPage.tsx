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
      navigate(storyLocation(session));
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
      navigate(storyLocation(session));
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Unable to resume the saved workspace.');
    } finally {
      setIsLaunching(false);
    }
  };

  return (
    <main className="landing" data-testid="landing-page">
      <section className="landing__hero">
        <p className="landing__eyebrow">Novel Engine / Story Workshop</p>
        <h1 className="landing__title" data-testid="landing-title">
          Build a long-form manuscript from a cold start, keep the run trail visible, and decide publication with evidence.
        </h1>
        <p className="landing__copy">
          The author shell is organized around three surfaces that stay stable under automation and
          human use: entry, manuscript library/current draft, and immutable run playback.
        </p>

        <div className="landing__actions">
          <Button onClick={handleLaunch} disabled={isLaunching} data-testid="launch-guest">
            {isLaunching ? 'Opening workspace...' : 'Launch guest workspace'}
          </Button>
          <Link className="button button--secondary" to="/login" data-testid="landing-sign-in">
            Sign in
          </Link>
        </div>

        {error ? <p className="form-error">{error}</p> : null}
      </section>

      <section className="landing__journey" data-testid="landing-journey">
        <article className="landing-card">
          <h2>1. Enter</h2>
          <p>Start as a guest or sign in with the canonical auth contract.</p>
        </article>
        <article className="landing-card">
          <h2>2. Compose</h2>
          <p>Create manuscripts, switch between them, and run blueprint, outline, drafting, and review in one workspace.</p>
        </article>
        <article className="landing-card">
          <h2>3. Audit</h2>
          <p>Inspect run history, snapshots, artifacts, gates, and publication state without leaving the workshop.</p>
        </article>
      </section>

      <section className="landing__grid">
        <article className="landing-card">
          <h2>Stable entry routes</h2>
          <p>`/`, `/login`, and `/story` are the canonical routes for users and browser automation.</p>
        </article>
        <article className="landing-card">
          <h2>Real backend contract</h2>
          <p>Guest sessions, login, story workflow actions, run playback, and publish gates all hit the real API.</p>
        </article>
        <article className="landing-card">
          <h2>Long-form UAT target</h2>
          <p>The release-grade validation path is a 20-chapter live run with system-gate evidence and editorial review.</p>
        </article>
      </section>

      {resumableSessions.length ? (
        <section className="landing__grid" data-testid="landing-session-catalog">
          <article className="landing-card landing-card--wide">
            <h2>Resume a saved workspace</h2>
            <p>Local storage caches session context, but resuming still revalidates against the live API before entering `/story`.</p>
            <ul className="story-list">
              {resumableSessions.map((session) => (
                <li key={session.id} className="story-card">
                  <button
                    className="story-card__button"
                    type="button"
                    onClick={() => void handleResume(session.id)}
                    data-testid={`landing-resume-session-${session.id}`}
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
