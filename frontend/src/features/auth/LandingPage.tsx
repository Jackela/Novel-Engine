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
          Launch a long-form novel workspace with guest access, story generation, and continuity review.
        </h1>
        <p className="landing__copy">
          The frontend is a source-first author shell: one session model, one story pipeline, one
          continuity loop, and a direct path from inspiration to publishable chapters.
        </p>

        <div className="landing__actions">
          <Button onClick={handleLaunch} disabled={isLaunching} data-testid="launch-guest">
            {isLaunching ? 'Opening workspace...' : 'Launch author workspace'}
          </Button>
          <Link className="button button--secondary" to="/login">
            Sign in
          </Link>
        </div>

        {error ? <p className="form-error">{error}</p> : null}
      </section>

      <section className="landing__grid">
        <article className="landing-card">
          <h2>Single source app shell</h2>
          <p>Plain React, TypeScript, and CSS. No hidden imports, no UI framework lock-in.</p>
        </article>
        <article className="landing-card">
          <h2>Directly testable routes</h2>
          <p>`/` and `/story` are stable entry points for Playwright and for writers.</p>
        </article>
        <article className="landing-card">
          <h2>Canonical backend only</h2>
          <p>Guest sessions, story generation, and continuity review are driven by the real API.</p>
        </article>
      </section>
    </main>
  );
}
