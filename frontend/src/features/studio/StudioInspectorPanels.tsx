import type { FormEvent, Dispatch, SetStateAction } from 'react';

import type {
  ExportFormat,
  ProviderInfo,
  Review,
  Revision,
  StudioExport,
  StudioJob,
} from '@/app/types/studio';

import { StudioCopilotPanel } from './components/StudioCopilotPanel';
import { StudioExportPanel } from './components/StudioExportPanel';
import { StudioHistoryPanel } from './components/StudioHistoryPanel';
import { StudioJobsPanel } from './components/StudioJobsPanel';
import { StudioReviewPanel } from './components/StudioReviewPanel';
import { StudioSettingsPanel } from './components/StudioSettingsPanel';
import { type InspectorTab } from './studioConstants';
import type { InspectorPendingState, SettingsFormState } from './StudioInspector';

interface StudioInspectorPanelsProps {
  inspector: InspectorTab;
  tabId: (tab: Exclude<InspectorTab, 'settings'>) => string;
  panelId: (tab: Exclude<InspectorTab, 'settings'>) => string;
  exports: StudioExport[];
  instruction: string;
  jobs: StudioJob[];
  latestReview: Review | null;
  loadedRevisionId: string | null;
  proposal: StudioJob | null;
  providers: ProviderInfo[];
  revisions: Revision[];
  settingsForm: SettingsFormState;
  onAcceptProposal: () => void;
  onExport?: (format: ExportFormat) => void;
  onRetryExport?: (format: ExportFormat) => void;
  onLoadJobs: () => void;
  onRestoreRevision: (revisionId: string) => void;
  onRetryJob: (jobId: string) => void;
  onRunProposal: (operation: 'continue' | 'rewrite') => void;
  onRunReview: () => void;
  onUpdateSettings: (event: FormEvent) => void;
  setInstruction: Dispatch<SetStateAction<string>>;
  setProposal: Dispatch<SetStateAction<StudioJob | null>>;
  setSettingsForm: Dispatch<SetStateAction<SettingsFormState>>;
  exportingFormat: ExportFormat | null;
  failedFormat: ExportFormat | null;
  pending: InspectorPendingState;
  errorForExport: string | null;
}

export function StudioInspectorPanels({
  inspector,
  tabId,
  panelId,
  exports,
  instruction,
  jobs,
  latestReview,
  loadedRevisionId,
  proposal,
  providers,
  revisions,
  settingsForm,
  onAcceptProposal,
  onExport,
  onRetryExport,
  onLoadJobs,
  onRestoreRevision,
  onRetryJob,
  onRunProposal,
  onRunReview,
  onUpdateSettings,
  setInstruction,
  setProposal,
  setSettingsForm,
  exportingFormat,
  failedFormat,
  pending,
  errorForExport,
}: StudioInspectorPanelsProps) {
  if (inspector === 'settings') {
    return (
      <StudioSettingsPanel
        settingsForm={settingsForm}
        setSettingsForm={setSettingsForm}
        onUpdateSettings={onUpdateSettings}
        providers={providers}
        isSaving={pending.settings}
      />
    );
  }

  return (
    <>
      <div
        aria-labelledby={tabId('copilot')}
        hidden={inspector !== 'copilot'}
        id={panelId('copilot')}
        role="tabpanel"
      >
        <StudioCopilotPanel
          instruction={instruction}
          setInstruction={setInstruction}
          proposal={proposal}
          setProposal={setProposal}
          onRunProposal={onRunProposal}
          onAcceptProposal={onAcceptProposal}
          isRunningProposal={pending.proposal.running}
          isAcceptingProposal={pending.proposal.accepting}
        />
      </div>
      <div
        aria-labelledby={tabId('export')}
        hidden={inspector !== 'export'}
        id={panelId('export')}
        role="tabpanel"
      >
        <StudioExportPanel
          exports={exports}
          exportingFormat={exportingFormat}
          onExport={onExport}
          error={errorForExport}
          failedFormat={failedFormat}
          onRetry={onRetryExport}
        />
      </div>
      <div
        aria-labelledby={tabId('review')}
        hidden={inspector !== 'review'}
        id={panelId('review')}
        role="tabpanel"
      >
        <StudioReviewPanel
          latestReview={latestReview}
          onRunReview={onRunReview}
          isRunning={pending.review}
        />
      </div>
      <div
        aria-labelledby={tabId('history')}
        hidden={inspector !== 'history'}
        id={panelId('history')}
        role="tabpanel"
      >
        <StudioHistoryPanel
          revisions={revisions}
          loadedRevisionId={loadedRevisionId}
          exports={[]}
          onRestoreRevision={onRestoreRevision}
        />
      </div>
      <div
        aria-labelledby={tabId('jobs')}
        hidden={inspector !== 'jobs'}
        id={panelId('jobs')}
        role="tabpanel"
      >
        <StudioJobsPanel
          jobs={jobs}
          onLoadJobs={onLoadJobs}
          onRetryJob={onRetryJob}
          isLoading={pending.jobs.loading}
          retryingJobId={
            pending.jobs.retrying
              ? (jobs.find((job) => job.status === 'failed' || job.status === 'interrupted')?.id ??
                '__retrying__')
              : null
          }
        />
      </div>
    </>
  );
}
