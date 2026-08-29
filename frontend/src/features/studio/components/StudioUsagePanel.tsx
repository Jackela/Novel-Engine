import { RefreshCw } from 'lucide-react';

import type { ProjectUsage } from '@/app/types/studio';

import { useProjectUsage } from '../hooks/useProjectUsage';
import { UsageModelTable } from './UsageModelTable';

const formatCount = (value: number) => value.toLocaleString('en-US');

function UsageTotalCard({ label, value }: { label: string; value: number }) {
  return (
    <div aria-label={`${label}: ${formatCount(value)}`} className="usage-total-card" role="group">
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
  const totals: ProjectUsage | null = usage;

  return (
    <div aria-busy={isLoading} className="inspector-content">
      <header className="inspector-heading">
        <div>
          <h2>Usage</h2>
          <p>Cumulative AI token usage.</p>
        </div>
        <button
          aria-busy={isLoading}
          aria-label={isLoading ? 'Refreshing usage' : 'Refresh usage'}
          className="icon-command"
          disabled={isLoading}
          onClick={() => void reload()}
          title="Refresh usage"
          type="button"
        >
          <RefreshCw />
        </button>
      </header>
      {error ? (
        <div aria-live="assertive" className="inspector-error" role="alert">
          {error}
        </div>
      ) : null}
      {totals ? (
        <>
          <div className="usage-totals">
            <UsageTotalCard label="Requests" value={totals.request_count} />
            <UsageTotalCard label="Prompt tokens" value={totals.prompt_tokens} />
            <UsageTotalCard label="Completion tokens" value={totals.completion_tokens} />
          </div>
          {totals.per_model.length ? (
            <UsageModelTable rows={totals.per_model} />
          ) : (
            <p className="empty-panel">No usage recorded yet.</p>
          )}
        </>
      ) : (
        <p className="empty-panel">{isLoading ? 'Loading usage…' : 'No usage recorded yet.'}</p>
      )}
    </div>
  );
}
