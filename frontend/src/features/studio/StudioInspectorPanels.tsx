import { StudioCopilotPanel } from "./components/StudioCopilotPanel";
import { StudioExportPanel } from "./components/StudioExportPanel";
import { StudioHistoryPanel } from "./components/StudioHistoryPanel";
import { StudioJobsPanel } from "./components/StudioJobsPanel";
import { StudioLoreStatusPanel } from "./components/StudioLoreStatusPanel";
import { StudioReviewPanel } from "./components/StudioReviewPanel";
import { StudioSettingsPanel } from "./components/StudioSettingsPanel";
import { StudioUsagePanel } from "./components/StudioUsagePanel";
import type { InspectorTab } from "./studioConstants";
import type { InspectorPendingState, StudioInspectorModel } from "./studioInspectorTypes";

interface StudioInspectorPanelsProps {
  inspector: InspectorTab;
  tabId: (tab: Exclude<InspectorTab, "settings">) => string;
  panelId: (tab: Exclude<InspectorTab, "settings">) => string;
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
  // The page model owns Lore eligibility; the panel owns document identity.
  const loreStatus = model.loreStatus ? (
    <StudioLoreStatusPanel
      documentId={model.loreStatus.documentId}
      savedStatus={model.loreStatus.savedStatus}
      attemptedStatus={model.loreStatus.attemptedStatus}
      isSaving={model.loreStatus.isSaving}
      onSubmit={model.loreStatus.submit}
    />
  ) : null;

  if (inspector === "settings") {
    return (
      <StudioSettingsPanel
        settingsForm={model.settings.settingsForm}
        setSettingsForm={model.settings.setSettingsForm}
        onUpdateSettings={model.settings.onUpdateSettings}
        providers={model.settings.providers}
        isSaving={pending.settings}
        error={model.settings.error}
      />
    );
  }

  return (
    <>
      <div
        aria-labelledby={tabId("copilot")}
        hidden={inspector !== "copilot"}
        id={panelId("copilot")}
        role="tabpanel"
      >
        {inspector === "copilot" ? loreStatus : null}
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
          proposalOutcomeUnknown={model.copilot.proposalOutcomeUnknown}
          proposalAuditStatus={model.copilot.proposalAuditStatus}
          unknownAttemptOperation={model.copilot.unknownAttemptOperation}
          onRetryProposalAudit={model.copilot.onRetryProposalAudit}
        />
      </div>
      <div
        aria-labelledby={tabId("export")}
        hidden={inspector !== "export"}
        id={panelId("export")}
        role="tabpanel"
      >
        <StudioExportPanel
          exports={model.export.exports}
          exportingFormat={model.export.exportingFormat}
          retryingFormat={model.export.retryingFormat}
          onExport={model.export.onExport}
          error={model.export.errorForExport}
          failedFormat={model.export.failedFormat}
          onRetry={model.export.onRetryExport}
        />
      </div>
      <div
        aria-labelledby={tabId("review")}
        hidden={inspector !== "review"}
        id={panelId("review")}
        role="tabpanel"
      >
        <StudioReviewPanel
          latestReview={model.review.latestReview}
          onRunReview={model.review.onRunReview}
          isRunning={pending.review}
        />
      </div>
      <div
        aria-labelledby={tabId("history")}
        hidden={inspector !== "history"}
        id={panelId("history")}
        role="tabpanel"
      >
        <StudioHistoryPanel
          revisions={model.history.revisions}
          loadedRevisionId={model.history.loadedRevisionId}
          onRestoreRevision={model.history.onRestoreRevision}
          restoringRevisionId={pending.history?.restoringRevisionId}
          historyInitialized={model.history.historyInitialized}
          hasOlderRevisions={model.history.hasOlderRevisions}
          isLoadingOlder={model.history.isLoadingOlder}
          isLoadingHistory={model.history.isLoadingHistory}
          onLoadOlderRevisions={model.history.onLoadOlderRevisions}
        />
      </div>
      <div
        aria-labelledby={tabId("jobs")}
        hidden={inspector !== "jobs"}
        id={panelId("jobs")}
        role="tabpanel"
      >
        <StudioJobsPanel
          jobs={model.jobs.jobs}
          hasOlderJobs={model.jobs.hasOlderJobs}
          onLoadJobs={model.jobs.onLoadJobs}
          onLoadOlderJobs={model.jobs.onLoadOlderJobs}
          onRetryJob={model.jobs.onRetryJob}
          isLoading={pending.jobs.loading}
          loadingInitiator={pending.jobs.loadingInitiator}
          retryGated={pending.jobs.retryGated}
          retryingJobId={
            pending.jobs.retryingJobId ??
            (pending.jobs.retrying
              ? (model.jobs.jobs.find(
                  (job) => job.status === "failed" || job.status === "interrupted",
                )?.id ?? "__retrying__")
              : null)
          }
        />
      </div>
      <div
        aria-labelledby={tabId("usage")}
        hidden={inspector !== "usage"}
        id={panelId("usage")}
        role="tabpanel"
      >
        <StudioUsagePanel active={inspector === "usage"} projectId={model.usage.projectId} />
      </div>
    </>
  );
}
