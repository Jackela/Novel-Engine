import { BookOpen, Loader2, LogIn } from "lucide-react";
import { type FormEvent, useCallback, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "@/app/api";
import { useTranslation } from "@/app/i18n/useTranslation";
import { LanguageSwitch } from "@/app/LanguageSwitch";
import { productIdentity, productLabel } from "@/app/productIdentity";
import { ThemeSwitch } from "@/app/ThemeSwitch";

import { toErrorMessage } from "./hooks/toErrorMessage";
import { useCommandFocusRestoration } from "./hooks/useCommandFocusRestoration";
import { useEntryBootstrap } from "./hooks/useEntryBootstrap";

const PASSWORD_AUTOCOMPLETE = {
  existing: "current-password",
  fresh: "new-password",
} as const;

export function EntryPage() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [username, setUsername] = useState("author");
  const [password, setPassword] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitPhase, setSubmitPhase] = useState<"idle" | "running">("idle");
  const busyRef = useRef(false);
  const submitRef = useRef<HTMLButtonElement | null>(null);
  const headingRef = useRef<HTMLHeadingElement | null>(null);
  const onAuthenticated = useCallback(() => {
    navigate("/projects", { replace: true });
  }, [navigate]);
  const { setup, error, isLoading, reload, mountedRef, markOwnerConfigured } =
    useEntryBootstrap(onAuthenticated);
  const runRetryWithFocusRestoration = useCommandFocusRestoration(isLoading);
  const busy = submitPhase === "running";
  const runSubmitWithFocusRestoration = useCommandFocusRestoration(busy);

  const submitCredentials = async () => {
    if (busyRef.current || setup === null) return;
    busyRef.current = true;
    setSubmitPhase("running");
    setSubmitError(null);
    try {
      if (!setup?.owner_configured) {
        await api.setupOwner(username, password);
        if (!mountedRef.current) return;
        markOwnerConfigured();
      }
      await api.login(username, password);
      if (mountedRef.current) navigate("/projects");
    } catch (reason) {
      if (mountedRef.current) {
        setSubmitError(toErrorMessage(reason, t("entry.error.unableToContinue")));
      }
    } finally {
      busyRef.current = false;
      if (mountedRef.current) setSubmitPhase("idle");
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (busyRef.current || submitRef.current === null) return;
    void runSubmitWithFocusRestoration(submitRef.current, submitCredentials);
  };

  return (
    <main className="entry">
      <section className="entry__panel">
        <div className="entry__theme">
          <LanguageSwitch />
          <ThemeSwitch />
        </div>
        <div className="entry__brand">
          <BookOpen aria-hidden="true" />
          <span>{productIdentity.name}</span>
        </div>
        <h1 ref={headingRef} tabIndex={-1}>
          {setup
            ? setup.owner_configured
              ? t("entry.heading.signedIn")
              : t("entry.heading.createOwner")
            : error
              ? t("entry.heading.unavailable")
              : t("entry.heading.loading")}
        </h1>
        <p>{t("entry.intro.selfHosted")}</p>
        <p>{t("entry.intro.trialProvider")}</p>
        {setup ? (
          <form className="entry__form" onSubmit={submit}>
            <label>
              <span>{t("entry.field.username")}</span>
              <input
                autoComplete="username"
                disabled={busy}
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
              />
            </label>
            <label>
              <span>{t("entry.field.password")}</span>
              <input
                autoComplete={
                  setup.owner_configured
                    ? PASSWORD_AUTOCOMPLETE.existing
                    : PASSWORD_AUTOCOMPLETE.fresh
                }
                disabled={busy}
                minLength={10}
                onChange={(event) => setPassword(event.target.value)}
                required
                type="password"
                value={password}
              />
            </label>
            {submitError ? (
              <p aria-live="assertive" className="ui-form-error" role="alert">
                {submitError}
              </p>
            ) : null}
            <button
              aria-busy={busy || undefined}
              className="ui-command ui-command--primary"
              disabled={busy}
              ref={submitRef}
              type="submit"
            >
              <LogIn aria-hidden="true" />
              {busy
                ? setup.owner_configured
                  ? t("entry.action.signingIn")
                  : t("entry.action.creatingOwner")
                : setup.owner_configured
                  ? t("entry.action.signIn")
                  : t("entry.action.createOwner")}
            </button>
          </form>
        ) : error ? (
          <div className="entry__state">
            <p aria-live="assertive" className="ui-form-error" role="alert">
              {error}
            </p>
            <button
              aria-busy={isLoading || undefined}
              aria-label={t("common.action.tryAgain")}
              className="ui-command ui-command--primary"
              disabled={isLoading}
              onClick={(event) => {
                void runRetryWithFocusRestoration(
                  event.currentTarget,
                  reload,
                  () => headingRef.current,
                );
              }}
              type="button"
            >
              {isLoading ? <Loader2 aria-hidden="true" className="ui-spin" /> : null}
              {isLoading ? t("common.action.tryingAgain") : t("common.action.tryAgain")}
            </button>
          </div>
        ) : (
          <p aria-live="polite" className="entry__state" role="status">
            <Loader2 aria-hidden="true" className="ui-spin" /> {t("entry.status.checkingSession")}
          </p>
        )}
        <footer>{productLabel}</footer>
      </section>
    </main>
  );
}
