import { useTranslation } from "@/app/i18n/useTranslation";

interface AppCrashFallbackProps {
  /** Raw error message kept visible under the readable copy; null hides it. */
  readonly detail: string | null;
}

/**
 * DR-046: the shared top-level crash panel rendered by both the React class
 * boundary in `main.tsx` and the router error element in `router.tsx`, so the
 * last-resort copy follows the active UI language like every panel. It
 * renders only the readable message; the crash itself is not retried here —
 * the copy asks for a page refresh, which is the only recovery a top-level
 * boundary can offer without discarding evidence.
 */
export function AppCrashFallback({ detail }: AppCrashFallbackProps) {
  const { t } = useTranslation();
  return (
    <div className="entry">
      <div className="entry__panel">
        <h1>{t("shell.error.heading")}</h1>
        <p>{t("shell.error.body")}</p>
        {detail ? <p className="ui-form-error">{detail}</p> : null}
      </div>
    </div>
  );
}
