import { StudioBeatPanel } from "./components/StudioBeatPanel";
import { StudioCopilotPanel } from "./components/StudioCopilotPanel";
import { StudioInspectorTabPanels } from "./components/StudioInspectorTabPanels";
import { StudioLoreStatusPanel } from "./components/StudioLoreStatusPanel";
import { StudioSettingsPanel } from "./components/StudioSettingsPanel";
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
  // The page model owns Lore and beat eligibility; the panels own document identity.
  const loreStatus = model.loreStatus ? (
    <StudioLoreStatusPanel
      documentId={model.loreStatus.documentId}
      savedStatus={model.loreStatus.savedStatus}
      attemptedStatus={model.loreStatus.attemptedStatus}
      isSaving={model.loreStatus.isSaving}
      onSubmit={model.loreStatus.submit}
    />
  ) : null;
  const beat = model.beat ? (
    <StudioBeatPanel
      projectId={model.beat.projectId}
      documentId={model.beat.documentId}
      beatRef={model.beat.beatRef}
      attemptedTitle={model.beat.attemptedTitle}
      isSaving={model.beat.isSaving}
      error={model.beat.error}
      onLink={model.beat.link}
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
        onExportDiagnostics={model.settings.diagnostics.onExport}
        isExportingDiagnostics={model.settings.diagnostics.isExporting}
        diagnosticsError={model.settings.diagnostics.error}
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
        {inspector === "copilot" ? beat : null}
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
          streamingInterrupted={model.copilot.streamingInterrupted}
          streamingStopped={model.copilot.streamingStopped}
          acceptanceUndo={model.copilot.acceptanceUndo}
          onStopProposal={model.copilot.onStopProposal}
          proposalOutcomeUnknown={model.copilot.proposalOutcomeUnknown}
          proposalAuditStatus={model.copilot.proposalAuditStatus}
          unknownAttemptOperation={model.copilot.unknownAttemptOperation}
          onRetryProposalAudit={model.copilot.onRetryProposalAudit}
        />
      </div>
      <StudioInspectorTabPanels
        inspector={inspector}
        model={model}
        panelId={panelId}
        pending={pending}
        tabId={tabId}
      />
    </>
  );
}
