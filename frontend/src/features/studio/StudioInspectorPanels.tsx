import { StudioCopilotPanel } from './components/StudioCopilotPanel';
import { StudioExportPanel } from './components/StudioExportPanel';
import { StudioHistoryPanel } from './components/StudioHistoryPanel';
import { StudioJobsPanel } from './components/StudioJobsPanel';
import { StudioUsagePanel } from './components/StudioUsagePanel';
import { StudioReviewPanel } from './components/StudioReviewPanel';
import { StudioSettingsPanel } from './components/StudioSettingsPanel';
import { type InspectorTab } from './studioConstants';
import type { InspectorPendingState, StudioInspectorModel } from './studioInspectorTypes';

interface StudioInspectorPanelsProps {
  inspector: InspectorTab;
  tabId: (tab: Exclude<InspectorTab, 'settings'>) => string;
  panelId: (tab: Exclude<InspectorTab, 'settings'>) => string;
  pending: InspectorPendingState;
  model: StudioInspectorModel;
}

export function StudioInspectorPanels({
  inspector,
  tabId,
  panelId,
  pending,
  model,
}: StudioInspectorPanelsProps) {
  if (inspector === 'settings') {
    return (
      <StudioSettingsPanel
        settingsForm={model.settings.settingsForm}
        setSettingsForm={model.settings.setSettingsForm}
        onUpdateSettings={model.settings.onUpdateSettings}
        providers={model.settings.providers}
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
          instruction={model.copilot.instruction}
          setInstruction={model.copilot.setInstruction}
          proposal={model.copilot.proposal}
          setProposal={model.copilot.setProposal}
          onRunProposal={model.copilot.onRunProposal}
          onAcceptProposal={model.copilot.onAcceptProposal}
          isRunningProposal={pending.proposal.running}
          isAcceptingProposal={pending.proposal.accepting}
          streamingText={model.copilot.streamingText}
          onStopProposal={model.copilot.onStopProposal}
        />
      </div>
      <div
        aria-labelledby={tabId('export')}
        hidden={inspector !== 'export'}
        id={panelId('export')}
        role="tabpanel"
      >
        <StudioExportPanel
          exports={model.export.exports}
          exportingFormat={model.export.exportingFormat}
          onExport={model.export.onExport}
          error={model.export.errorForExport}
          failedFormat={model.export.failedFormat}
          onRetry={model.export.onRetryExport}
        />
      </div>
      <div
        aria-labelledby={tabId('review')}
        hidden={inspector !== 'review'}
        id={panelId('review')}
        role="tabpanel"
      >
        <StudioReviewPanel
          latestReview={model.review.latestReview}
          onRunReview={model.review.onRunReview}
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
          revisions={model.history.revisions}
          loadedRevisionId={model.history.loadedRevisionId}
          onRestoreRevision={model.history.onRestoreRevision}
          restoringRevisionId={pending.history?.restoringRevisionId}
        />
      </div>
      <div
        aria-labelledby={tabId('jobs')}
        hidden={inspector !== 'jobs'}
        id={panelId('jobs')}
        role="tabpanel"
      >
        <StudioJobsPanel
          jobs={model.jobs.jobs}
          onLoadJobs={model.jobs.onLoadJobs}
          onRetryJob={model.jobs.onRetryJob}
          isLoading={pending.jobs.loading}
          retryingJobId={
            pending.jobs.retryingJobId ??
            (pending.jobs.retrying
              ? (model.jobs.jobs.find(
                  (job) => job.status === 'failed' || job.status === 'interrupted',
                )?.id ?? '__retrying__')
              : null)
          }
        />
      </div>
      <div
        aria-labelledby={tabId('usage')}
        hidden={inspector !== 'usage'}
        id={panelId('usage')}
        role="tabpanel"
      >
        <StudioUsagePanel active={inspector === 'usage'} projectId={model.usage.projectId} />
      </div>
    </>
  );
}
