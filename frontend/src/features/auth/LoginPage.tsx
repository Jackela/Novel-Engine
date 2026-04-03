import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { Button } from '@/components/Button';
import { useAuth } from '@/features/auth/useAuth';

export function LoginPage() {
  const navigate = useNavigate();
  const { signIn, signInAsGuest } = useAuth();
  const [email, setEmail] = useState('operator@novel.engine');
  const [password, setPassword] = useState('demo-password');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      await signIn({ email, password });
      navigate('/story');
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
      await signInAsGuest();
      navigate('/story');
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Unable to create guest session.');
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
    </main>
  );
}
