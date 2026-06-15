import { useEffect, useState, type FormEvent } from 'react';
import { BookOpen, LogIn, Sparkles } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import { api } from '@/app/api';
import type { SetupStatus } from '@/app/types/studio';

export function EntryPage() {
  const navigate = useNavigate();
  const [setup, setSetup] = useState<SetupStatus | null>(null);
  const [username, setUsername] = useState('author');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let mounted = true;
    void api
      .session()
      .then(() => {
        if (mounted) navigate('/projects', { replace: true });
      })
      .catch(() =>
        api
          .setupStatus()
          .then((status) => {
            if (mounted) setSetup(status);
          })
          .catch((reason: unknown) => {
            if (mounted) {
              setError(reason instanceof Error ? reason.message : 'Unable to reach Novel Studio.');
            }
          }),
      );
    return () => {
      mounted = false;
    };
  }, [navigate]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (!setup?.owner_configured) {
        await api.setupOwner(username, password);
      }
      await api.login(username, password);
      navigate('/projects');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to continue.');
    } finally {
      setBusy(false);
    }
  };

  const guest = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.guest();
      navigate('/projects');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to open guest studio.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="entry">
      <section className="entry__panel">
        <div className="entry__brand">
          <BookOpen aria-hidden="true" />
          <span>Novel Studio</span>
        </div>
        <h1>{setup?.owner_configured ? 'Open your writing studio' : 'Create the local owner'}</h1>
        <p>
          Your projects, Markdown revisions, reviews, and exports stay in this self-hosted instance.
        </p>
        <form className="entry__form" onSubmit={submit}>
          <label>
            <span>Username</span>
            <input
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
            />
          </label>
          <label>
            <span>Password</span>
            <input
              autoComplete={setup?.owner_configured ? 'current-password' : 'new-password'}
              minLength={10}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>
          {error ? <p className="form-error">{error}</p> : null}
          <button className="command command--primary" disabled={busy || !setup} type="submit">
            <LogIn aria-hidden="true" />
            {busy ? 'Opening...' : setup?.owner_configured ? 'Sign in' : 'Create owner'}
          </button>
        </form>
        <div className="entry__divider">
          <span>or</span>
        </div>
        <button className="command" disabled={busy} onClick={() => void guest()} type="button">
          <Sparkles aria-hidden="true" />
          Try a 24-hour guest studio
        </button>
        <footer>Novel Studio {__APP_VERSION__}</footer>
      </section>
    </main>
  );
}
