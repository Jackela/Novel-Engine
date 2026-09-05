import { RefreshCw } from "lucide-react";

import type { ProjectUsage } from "@/app/types/studio";

import { useCommandFocusRestoration } from "../hooks/useCommandFocusRestoration";
import { useProjectUsage } from "../hooks/useProjectUsage";
import { UsageDailyBars } from "./UsageDailyBars";
import { UsageModelTable } from "./UsageModelTable";

const formatCount = (value: number) => value.toLocaleString("en-US");

function UsageTotalCard({ label, value }: { label: string; value: number }) {
  return (
    // biome-ignore lint/a11y/useSemanticElements: this stat card is not a form control group; <fieldset> would misrepresent semantics and drag in default fieldset styling.
    <div aria-label={`${label}: ${formatCount(value)}`} className="usage__total-card" role="group">
      <strong>{formatCount(value)}</strong>
      <span>{label}</span>
    </div>
  );
}

interface StudioUsagePanelProps {
  projectId: string;
  /** True while the Usage tab is the selected inspector tab (#377). */
  active: boolean;
}

/**
 * Project-level cumulative AI usage (#377): three totals cards plus the
 * per-model detail table.  Data loads lazily when the tab first activates.
 */
export function StudioUsagePanel({ projectId, active }: StudioUsagePanelProps) {
  const { usage, isLoading, error, reload } = useProjectUsage(projectId, active);
  const runRefreshWithFocusRestoration = useCommandFocusRestoration(isLoading);
  const totals: ProjectUsage | null = usage;

  return (
    <div aria-busy={isLoading} className="studio-inspector__panel">
      <header className="studio-inspector__heading">
        <div>
          <h2>Usage</h2>
          <p>Cumulative AI token usage.</p>
        </div>
        <button
          aria-busy={isLoading}
          aria-label={isLoading ? "Refreshing usage" : "Refresh usage"}
          className="ui-command--icon"
          disabled={isLoading}
          onClick={(event) => {
            void runRefreshWithFocusRestoration(event.currentTarget, reload);
          }}
          title="Refresh usage"
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
            <UsageTotalCard label="Requests" value={totals.request_count} />
            <UsageTotalCard label="Prompt tokens" value={totals.prompt_tokens} />
            <UsageTotalCard label="Completion tokens" value={totals.completion_tokens} />
          </div>
          {totals.daily?.some((bucket) => bucket.request_count > 0) ? (
            <UsageDailyBars buckets={totals.daily} />
          ) : null}
          {totals.per_model.length ? (
            <UsageModelTable rows={totals.per_model} />
          ) : (
            <p className="studio-inspector__empty">No usage recorded yet.</p>
          )}
        </>
      ) : (
        <p className="studio-inspector__empty">
          {isLoading ? "Loading usage…" : "No usage recorded yet."}
        </p>
      )}
    </div>
  );
}
