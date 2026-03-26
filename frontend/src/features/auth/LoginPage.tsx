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
      navigate('/dashboard');
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
      navigate('/dashboard');
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Unable to create guest session.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="auth-page" data-testid="login-page">
      <form className="auth-card" onSubmit={handleSubmit}>
        <p className="panel__eyebrow">Operator access</p>
        <h1 className="auth-card__title">Return to the control room</h1>
        <p className="auth-card__copy">
          Sign in against the backend contract or continue as a guest session.
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
            Continue as guest
          </Button>
        </div>

        <Link className="auth-card__back" to="/">
          Back to landing
        </Link>
      </form>
    </main>
  );
}
