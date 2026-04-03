import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { Button } from '@/components/Button';
import { useAuth } from '@/features/auth/useAuth';

export function LandingPage() {
  const navigate = useNavigate();
  const { signInAsGuest } = useAuth();
  const [isLaunching, setIsLaunching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLaunch = async () => {
    setIsLaunching(true);
    setError(null);

    try {
      await signInAsGuest();
      navigate('/story');
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Unable to create guest session.');
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
    </main>
  );
}
