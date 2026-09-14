import { RefreshCw } from "lucide-react";

import type { MessageKey } from "@/app/i18n/dictionaries/en";
import { useTranslation } from "@/app/i18n/useTranslation";

import { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";
import { useWritingStats } from "../hooks/useWritingStats";
import { StatsWordsTables } from "./StatsWordsTables";

const formatCount = (value: number) => value.toLocaleString("en-US");

function StatsTotalCard({ labelKey, value }: { labelKey: MessageKey; value: number }) {
  const { t } = useTranslation();
  const label = t(labelKey);
  return (
    // biome-ignore lint/a11y/useSemanticElements: this stat card is not a form control group; <fieldset> would misrepresent semantics and drag in default fieldset styling.
    <div
      aria-label={t("stats.cardLabel", { label, value: formatCount(value) })}
      className="stats__total-card"
      role="group"
    >
      <strong>{formatCount(value)}</strong>
      <span>{label}</span>
    </div>
  );
}

interface StudioWritingStatsPanelProps {
  projectId: string;
  /** True while the Stats tab is the selected inspector tab (#653). */
  active: boolean;
}

/**
 * The project writing-statistics panel (#653): streak, chapters started, and
 * today's words as summary cards; the daily/weekly source-attributed tables;
 * and the AI usage summary reusing the usage aggregation's figures. Data
 * loads lazily when the tab first activates, and every figure renders a
 * defined zero state for an empty project.
 */
export function StudioWritingStatsPanel({ projectId, active }: StudioWritingStatsPanelProps) {
  const { stats, isLoading, error, reload } = useWritingStats(projectId, active);
  const { t } = useTranslation();
  const runRefreshWithFocusRestoration = useCommandFocusRestoration(isLoading);
  const today = stats?.daily.at(-1);

  return (
    <div aria-busy={isLoading} className="studio-inspector__panel">
      <header className="studio-inspector__heading">
        <div>
          <h2>{t("stats.heading")}</h2>
          <p>{t("stats.hint")}</p>
        </div>
        <button
          aria-busy={isLoading}
          aria-label={isLoading ? t("stats.action.refreshing") : t("stats.action.refresh")}
          className="ui-command--icon"
          disabled={isLoading}
          onClick={(event) => {
            void runRefreshWithFocusRestoration(event.currentTarget, reload);
          }}
          title={t("stats.action.refresh")}
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
      {stats ? (
        <>
          <div className="stats__totals">
            <StatsTotalCard labelKey="stats.summary.streak" value={stats.streak_days} />
            <StatsTotalCard
              labelKey="stats.summary.chaptersStarted"
              value={stats.chapters.started}
            />
            {/*
             * Words today is the net figure of all three sources on the
             * current UTC day — the same sum as the daily table's Total
             * column. Restore deltas stay their own line in that split
             * (history movement, per the design), but this headline card
             * reports the day's net movement, so a restore rollback offsets
             * it exactly as it offsets the day's total.
             */}
            <StatsTotalCard
              labelKey="stats.summary.today"
              value={
                today === undefined
                  ? 0
                  : today.words.author + today.words.ai_accepted + today.words.restore
              }
            />
          </div>
          <p className="stats__chapters-share">
            {t("stats.summary.chaptersShare", {
              started: formatCount(stats.chapters.started),
              total: formatCount(stats.chapters.total),
            })}
          </p>
          <StatsWordsTables daily={stats.daily} weekly={stats.weekly} />
          <section aria-label={t("stats.usage.heading")} className="stats__section">
            <h3>{t("stats.usage.heading")}</h3>
            <div className="stats__totals">
              <StatsTotalCard labelKey="usage.total.requests" value={stats.usage.request_count} />
              <StatsTotalCard
                labelKey="usage.total.promptTokens"
                value={stats.usage.prompt_tokens}
              />
              <StatsTotalCard
                labelKey="usage.total.completionTokens"
                value={stats.usage.completion_tokens}
              />
            </div>
          </section>
        </>
      ) : (
        <p className="studio-inspector__empty">
          {isLoading ? t("stats.status.loading") : t("stats.empty")}
        </p>
      )}
    </div>
  );
}
