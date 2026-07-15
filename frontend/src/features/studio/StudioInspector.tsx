import { ChevronDown } from 'lucide-react';
import { useId, type Dispatch, type FormEvent, type SetStateAction } from 'react';

import type {
  ExportFormat,
  ProviderInfo,
  Review,
  Revision,
  StudioExport,
  StudioJob,
} from '@/app/types/studio';

import { StudioInspectorPanels } from './StudioInspectorPanels';
import { StudioInspectorTabs } from './StudioInspectorTabs';
import { type InspectorTab } from './studioConstants';

export interface SettingsFormState {
  title: string;
  description: string;
  provider: string;
}

export interface InspectorPendingState {
  proposal: {
    running: boolean;
    accepting: boolean;
  };
  review: boolean;
  jobs: {
    loading: boolean;
    retrying: boolean;
  };
  settings: boolean;
}

const DEFAULT_INSPECTOR_PENDING: InspectorPendingState = {
  proposal: { running: false, accepting: false },
  review: false,
  jobs: { loading: false, retrying: false },
  settings: false,
};

interface StudioInspectorProps {
  error: string | null;
  exports: StudioExport[];
  inspector: InspectorTab;
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
  setInspector: Dispatch<SetStateAction<InspectorTab>>;
  setInstruction: Dispatch<SetStateAction<string>>;
  setProposal: Dispatch<SetStateAction<StudioJob | null>>;
  setSettingsForm: Dispatch<SetStateAction<SettingsFormState>>;
  exportingFormat?: ExportFormat | null;
  failedFormat?: ExportFormat | null;
  pending?: InspectorPendingState;
  errorForExport?: string | null;
}

export function StudioInspector({
  error,
  exports,
  inspector,
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
  setInspector,
  setInstruction,
  setProposal,
  setSettingsForm,
  exportingFormat = null,
  failedFormat = null,
  pending = DEFAULT_INSPECTOR_PENDING,
  errorForExport = null,
}: StudioInspectorProps) {
  const inspectorId = useId();
  const tabId = (tab: Exclude<InspectorTab, 'settings'>) => `${inspectorId}-${tab}-tab`;
  const panelId = (tab: Exclude<InspectorTab, 'settings'>) => `${inspectorId}-${tab}-panel`;

  return (
    <aside className="studio-inspector">
      <details className="studio-inspector__disclosure" open>
        <summary className="studio-inspector__summary">
          <span>Inspector</span>
          <ChevronDown aria-hidden="true" />
        </summary>
        <div className="studio-inspector__content">
          {inspector !== 'settings' && (
            <StudioInspectorTabs
              inspector={inspector}
              tabId={tabId}
              panelId={panelId}
              setInspector={setInspector}
            />
          )}

          {error && inspector !== 'export' ? (
            <div aria-live="assertive" className="inspector-error" role="alert">
              {error}
            </div>
          ) : null}

          <StudioInspectorPanels
            inspector={inspector}
            tabId={tabId}
            panelId={panelId}
            exports={exports}
            instruction={instruction}
            jobs={jobs}
            latestReview={latestReview}
            loadedRevisionId={loadedRevisionId}
            proposal={proposal}
            providers={providers}
            revisions={revisions}
            settingsForm={settingsForm}
            onAcceptProposal={onAcceptProposal}
            onExport={onExport}
            onRetryExport={onRetryExport}
            onLoadJobs={onLoadJobs}
            onRestoreRevision={onRestoreRevision}
            onRetryJob={onRetryJob}
            onRunProposal={onRunProposal}
            onRunReview={onRunReview}
            onUpdateSettings={onUpdateSettings}
            setInstruction={setInstruction}
            setProposal={setProposal}
            setSettingsForm={setSettingsForm}
            exportingFormat={exportingFormat}
            failedFormat={failedFormat}
            pending={pending}
            errorForExport={errorForExport}
          />
        </div>
      </details>
    </aside>
  );
}
