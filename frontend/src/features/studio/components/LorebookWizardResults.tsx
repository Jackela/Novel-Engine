import { useTranslation } from "@/app/i18n/useTranslation";
import type { LoreConfirmResult } from "../hooks/lorebookConfirm";

interface LorebookWizardResultsProps {
  readonly results: LoreConfirmResult[];
  readonly onRetryAliases: (key: string) => void | Promise<void>;
  onStartOver: () => void;
}

const OUTCOME_MESSAGE_KEYS = {
  created: "lore.results.created",
  "created-with-failed-aliases": "lore.results.createdWithFailedAliases",
  failed: "lore.results.failed",
} as const;

/**
 * The wizard's confirmation report (#614): each selected candidate's outcome
 * is reported independently — created, created-with-failed-aliases (aliases
 * kept for retry, never silently dropped), or failed — with a retry command
 * for failed alias writes and a start-over command that clears the session.
 */
export function LorebookWizardResults({
  results,
  onRetryAliases,
  onStartOver,
}: LorebookWizardResultsProps) {
  const { t } = useTranslation();

  return (
    <section aria-label={t("lore.results.heading")} className="lore-wizard__section">
      <h3>{t("lore.results.heading")}</h3>
      <ul className="lore-wizard__results">
        {results.map((result) => (
          <li key={result.key} className="lore-wizard__result">
            <span>
              <strong>{result.title}</strong>
              <span className="lore-wizard__muted">{t(OUTCOME_MESSAGE_KEYS[result.outcome])}</span>
            </span>
            {result.outcome === "created-with-failed-aliases" ? (
              <>
                <span className="lore-wizard__error" role="alert">
                  {result.error ?? t("lore.results.createdWithFailedAliases")}
                </span>
                <span className="lore-wizard__muted">
                  {t("lore.results.retryHint", { aliases: result.aliases.join(", ") })}
                </span>
                <button
                  className="ui-command"
                  onClick={() => void onRetryAliases(result.key)}
                  type="button"
                >
                  {t("lore.results.action.retryAliases")}
                </button>
              </>
            ) : null}
            {result.outcome === "failed" ? (
              <span className="lore-wizard__error" role="alert">
                {result.error ?? t("lore.results.failed")}
              </span>
            ) : null}
          </li>
        ))}
      </ul>
      <div className="studio-inspector__actions">
        <button className="ui-command" onClick={onStartOver} type="button">
          {t("lore.results.action.startOver")}
        </button>
      </div>
    </section>
  );
}
