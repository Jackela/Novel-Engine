import { formatCount } from "@/app/i18n/format";
import { useTranslation } from "@/app/i18n/useTranslation";
import type { ProjectUsage } from "@/app/types/studio";

import { useProjectUsage } from "../hooks/useProjectUsage";
import {
  InspectorResourcePanel,
  type InspectorResourcePanelLabels,
} from "./InspectorResourcePanel";
import { StatTotalCard } from "./StatTotalCard";
import { UsageDailyBars } from "./UsageDailyBars";
import { UsageModelTable } from "./UsageModelTable";

/** The usage tab's copy, resolved from one table instead of at every call site. */
const USAGE_PANEL_LABELS: InspectorResourcePanelLabels = {
  heading: "usage.heading",
  hint: "usage.hint",
  refresh: "usage.action.refresh",
  refreshing: "usage.action.refreshing",
  loading: "usage.status.loading",
  empty: "usage.empty",
};

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
 * per-model detail table, and the trailing-30-day bars. Data loads lazily when
 * the tab first activates, and the panel chrome — heading, refresh command,
 * alert and loading/empty fallback — comes from `InspectorResourcePanel`.
 */
export function StudioUsagePanel({ projectId, active }: StudioUsagePanelProps) {
  const { usage, isLoading, error, reload } = useProjectUsage(projectId, active);
  const { t } = useTranslation();

  return (
    <InspectorResourcePanel
      data={usage}
      error={error}
      isLoading={isLoading}
      labels={USAGE_PANEL_LABELS}
      onRefresh={reload}
      renderBody={(projectUsage) => (
        <>
          <div className="usage__totals">
            <StatTotalCard
              family="usage"
              labelKey="usage.total.requests"
              value={projectUsage.request_count}
            />
            <StatTotalCard
              family="usage"
              labelKey="usage.total.failedAttempts"
              value={projectUsage.failed_attempt_count}
            />
            <StatTotalCard
              family="usage"
              labelKey="usage.total.promptTokens"
              value={projectUsage.prompt_tokens}
            />
            <StatTotalCard
              family="usage"
              labelKey="usage.total.completionTokens"
              value={projectUsage.completion_tokens}
            />
          </div>
          <UsageProvenanceNotices totals={projectUsage} />
          {projectUsage.daily?.some((bucket) => bucket.request_count > 0) ? (
            <UsageDailyBars buckets={projectUsage.daily} />
          ) : null}
          {projectUsage.per_model.length ? (
            <UsageModelTable rows={projectUsage.per_model} />
          ) : (
            <p className="studio-inspector__empty">{t("usage.empty")}</p>
          )}
        </>
      )}
    />
  );
}
