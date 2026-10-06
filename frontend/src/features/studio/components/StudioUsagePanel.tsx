import { RefreshCw } from "lucide-react";
import type { MessageKey } from "@/app/i18n/dictionaries/en";
import { formatCount } from "@/app/i18n/format";
import { useTranslation } from "@/app/i18n/useTranslation";
import type { ProjectUsage } from "@/app/types/studio";

import { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";
import { useProjectUsage } from "../hooks/useProjectUsage";
import { UsageDailyBars } from "./UsageDailyBars";
import { UsageModelTable } from "./UsageModelTable";

function UsageTotalCard({ labelKey, value }: { labelKey: MessageKey; value: number }) {
  const { t } = useTranslation();
  const label = t(labelKey);
  return (
    // biome-ignore lint/a11y/useSemanticElements: this stat card is not a form control group; <fieldset> would misrepresent semantics and drag in default fieldset styling.
    <div
      aria-label={t("usage.total.cardLabel", { label, value: formatCount(value) })}
      className="usage__total-card"
      role="group"
    >
      <strong>{formatCount(value)}</strong>
      <span>{label}</span>
    </div>
  );
}

/**
 * The DR-028 disclosures: token totals fold completed attempts only, and any
 * count that came from the word-count estimate instead of a provider report is
 * named as such — never silently presented as a provider number.
 */
function UsageProvenanceNotices({ totals }: { totals: ProjectUsage }) {
  const { t } = useTranslation();
  return (
    <>
      {totals.failed_attempt_count > 0 ? (
        <p className="usage__notice" role="note">
          {t("usage.failedAttempts.notice", {
            count: formatCount(totals.failed_attempt_count),
          })}
        </p>
      ) : null}
      {totals.estimated_requests > 0 ? (
        <p className="usage__notice" role="note">
          {t("usage.estimated.notice", {
            estimated: formatCount(totals.estimated_requests),
            counted: formatCount(totals.request_count),
          })}
        </p>
      ) : null}
    </>
  );
}

interface StudioUsagePanelProps {
  projectId: string;
  /** True while the Usage tab is the selected inspector tab (#377). */
  active: boolean;
}

/**
 * Project-level cumulative AI usage (#377, DR-028): the completed-attempt
 * totals cards plus failed-attempt and estimated-count disclosures, the
 * per-model detail table, and the trailing-30-day bars. Data loads lazily
 * when the tab first activates.
 */
export function StudioUsagePanel({ projectId, active }: StudioUsagePanelProps) {
  const { usage, isLoading, error, reload } = useProjectUsage(projectId, active);
  const { t } = useTranslation();
  const runRefreshWithFocusRestoration = useCommandFocusRestoration(isLoading);
  const totals: ProjectUsage | null = usage;

  return (
    <div aria-busy={isLoading} className="studio-inspector__panel">
      <header className="studio-inspector__heading">
        <div>
          <h2>{t("usage.heading")}</h2>
          <p>{t("usage.hint")}</p>
        </div>
        <button
          aria-busy={isLoading}
          aria-label={isLoading ? t("usage.action.refreshing") : t("usage.action.refresh")}
          className="ui-command--icon"
          disabled={isLoading}
          onClick={(event) => {
            void runRefreshWithFocusRestoration(event.currentTarget, reload);
          }}
          title={t("usage.action.refresh")}
          type="button"
        >
          <RefreshCw />
        </button>
      </header>
      {error ? (
        <div aria-live="assertive" className="studio-inspector__error" role="alert">
          {error}
        </div>
      ) : null}
      {totals ? (
        <>
          <div className="usage__totals">
            <UsageTotalCard labelKey="usage.total.requests" value={totals.request_count} />
            <UsageTotalCard
              labelKey="usage.total.failedAttempts"
              value={totals.failed_attempt_count}
            />
            <UsageTotalCard labelKey="usage.total.promptTokens" value={totals.prompt_tokens} />
            <UsageTotalCard
              labelKey="usage.total.completionTokens"
              value={totals.completion_tokens}
            />
          </div>
          <UsageProvenanceNotices totals={totals} />
          {totals.daily?.some((bucket) => bucket.request_count > 0) ? (
            <UsageDailyBars buckets={totals.daily} />
          ) : null}
          {totals.per_model.length ? (
            <UsageModelTable rows={totals.per_model} />
          ) : (
            <p className="studio-inspector__empty">{t("usage.empty")}</p>
          )}
        </>
      ) : (
        <p className="studio-inspector__empty">
          {isLoading ? t("usage.status.loading") : t("usage.empty")}
        </p>
      )}
    </div>
  );
}
