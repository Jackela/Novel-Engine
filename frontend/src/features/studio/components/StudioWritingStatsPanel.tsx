import { formatTzOffsetLabel } from "@/app/browserTimezone";
import { formatCount } from "@/app/i18n/format";
import { useTranslation } from "@/app/i18n/useTranslation";

import { useWritingStats } from "../hooks/useWritingStats";
import {
  InspectorResourcePanel,
  type InspectorResourcePanelLabels,
} from "./InspectorResourcePanel";
import { StatsWordsTables } from "./StatsWordsTables";
import { StatTotalCard } from "./StatTotalCard";

/** The stats tab's copy, resolved from one table instead of at every call site. */
const STATS_PANEL_LABELS: InspectorResourcePanelLabels = {
  heading: "stats.heading",
  hint: "stats.hint",
  refresh: "stats.action.refresh",
  refreshing: "stats.action.refreshing",
  loading: "stats.status.loading",
  empty: "stats.empty",
};

interface StudioWritingStatsPanelProps {
  projectId: string;
  /** True while the Stats tab is the selected inspector tab (#653). */
  active: boolean;
}

/**
 * The project writing-statistics panel (#653): streak, chapters started, and
 * today's words as summary cards; the daily/weekly source-attributed tables;
 * and the AI usage summary reusing the usage aggregation's figures. Data loads
 * lazily when the tab first activates, every figure renders a defined zero
 * state for an empty project, and the panel chrome — heading, refresh command,
 * alert and loading/empty fallback — comes from `InspectorResourcePanel`.
 */
export function StudioWritingStatsPanel({ projectId, active }: StudioWritingStatsPanelProps) {
  const { stats, isLoading, error, reload } = useWritingStats(projectId, active);
  const { t } = useTranslation();

  return (
    <InspectorResourcePanel
      data={stats}
      error={error}
      isLoading={isLoading}
      labels={STATS_PANEL_LABELS}
      onRefresh={reload}
      renderBody={(projectStats) => {
        const today = projectStats.daily.at(-1);
        return (
          <>
            <div className="stats__totals">
              <StatTotalCard
                family="stats"
                labelKey="stats.summary.streak"
                value={projectStats.streak_days}
              />
              <StatTotalCard
                family="stats"
                labelKey="stats.summary.chaptersStarted"
                value={projectStats.chapters.started}
              />
              {/*
               * Words today is the net figure of all three sources on the
               * current UTC day — the same sum as the daily table's Total
               * column. Restore deltas stay their own line in that split
               * (history movement, per the design), but this headline card
               * reports the day's net movement, so a restore rollback offsets
               * it exactly as it offsets the day's total.
               */}
              <StatTotalCard
                family="stats"
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
                started: formatCount(projectStats.chapters.started),
                total: formatCount(projectStats.chapters.total),
              })}
            </p>
            {/*
             * DR-045: the server buckets every row on the boundary the request
             * carried, and echoes it back — the label states which boundary the
             * figures above were computed on instead of leaving "today" implicit.
             */}
            <p className="stats__note">
              {t("stats.timezone.hint", {
                zone: formatTzOffsetLabel(projectStats.tz_offset_minutes),
              })}
            </p>
            <StatsWordsTables daily={projectStats.daily} weekly={projectStats.weekly} />
            <section aria-label={t("stats.usage.heading")} className="stats__section">
              <h3>{t("stats.usage.heading")}</h3>
              <div className="stats__totals">
                <StatTotalCard
                  family="stats"
                  labelKey="usage.total.requests"
                  value={projectStats.usage.request_count}
                />
                <StatTotalCard
                  family="stats"
                  labelKey="usage.total.promptTokens"
                  value={projectStats.usage.prompt_tokens}
                />
                <StatTotalCard
                  family="stats"
                  labelKey="usage.total.completionTokens"
                  value={projectStats.usage.completion_tokens}
                />
              </div>
            </section>
          </>
        );
      }}
    />
  );
}
