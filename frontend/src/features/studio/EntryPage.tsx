import { BookOpen, LogIn } from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "@/app/api";
import type { SetupStatus } from "@/app/types/studio";

import { toErrorMessage } from "./hooks/toErrorMessage";

const PASSWORD_AUTOCOMPLETE = {
  existing: "current-password",
  fresh: "new-password",
} as const;

export function EntryPage() {
  const navigate = useNavigate();
  const [setup, setSetup] = useState<SetupStatus | null>(null);
  const [username, setUsername] = useState("author");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let mounted = true;
    void api
      .session()
      .then(() => {
        if (mounted) navigate("/projects", { replace: true });
      })
      .catch(() =>
        api
          .setupStatus()
          .then((status) => {
            if (mounted) setSetup(status);
          })
          .catch((reason: unknown) => {
            if (mounted) {
              setError(toErrorMessage(reason, "Unable to reach Novel Engine."));
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
      navigate("/projects");
    } catch (reason) {
      setError(toErrorMessage(reason, "Unable to continue."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="entry">
      <section className="entry__panel">
        <div className="entry__brand">
          <BookOpen aria-hidden="true" />
          <span>Novel Engine</span>
        </div>
        <h1>{setup?.owner_configured ? "Open your writing studio" : "Create the local owner"}</h1>
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
              autoComplete={
                setup?.owner_configured
                  ? PASSWORD_AUTOCOMPLETE.existing
                  : PASSWORD_AUTOCOMPLETE.fresh
              }
              minLength={10}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>
          {error ? <p className="ui-form-error">{error}</p> : null}
          <button
            className="ui-command ui-command--primary"
            disabled={busy || !setup}
            type="submit"
          >
            <LogIn aria-hidden="true" />
            {busy ? "Opening..." : setup?.owner_configured ? "Sign in" : "Create owner"}
          </button>
        </form>
        <footer>Novel Engine {__APP_VERSION__}</footer>
      </section>
    </main>
  );
}
