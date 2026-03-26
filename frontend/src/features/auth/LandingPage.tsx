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
      navigate('/dashboard');
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Unable to create guest session.');
    } finally {
      setIsLaunching(false);
    }
  };

  return (
    <main className="landing" data-testid="landing-page">
      <section className="landing__hero">
        <p className="landing__eyebrow">Novel Engine / Session Control</p>
        <h1 className="landing__title" data-testid="landing-title">
          Launch a living narrative room with guest access, orchestration control, and live event telemetry.
        </h1>
        <p className="landing__copy">
          The frontend is a source-first shell: one session model, one dashboard model, one
          service layer, and a direct path from entry to orchestration.
        </p>

        <div className="landing__actions">
          <Button onClick={handleLaunch} disabled={isLaunching} data-testid="launch-guest">
            {isLaunching ? 'Opening session...' : 'Launch guest session'}
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
          <p>`/` and `/dashboard` are stable entry points for Playwright and for users.</p>
        </article>
        <article className="landing-card">
          <h2>Canonical backend only</h2>
          <p>Guest sessions, orchestration status, and event flow are driven by the real API.</p>
        </article>
      </section>
    </main>
  );
}
