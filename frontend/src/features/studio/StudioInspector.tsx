import { Bot, Briefcase, History, ShieldCheck } from 'lucide-react';
import type { Dispatch, FormEvent, SetStateAction } from 'react';

import type { Review, Revision, StudioExport, StudioJob } from '@/app/types/studio';

import { StudioCopilotPanel } from './components/StudioCopilotPanel';
import { StudioHistoryPanel } from './components/StudioHistoryPanel';
import { StudioJobsPanel } from './components/StudioJobsPanel';
import { StudioReviewPanel } from './components/StudioReviewPanel';
import { StudioSettingsPanel } from './components/StudioSettingsPanel';
import type { InspectorTab } from './studioConstants';

export interface SettingsFormState {
  title: string;
  description: string;
  provider: string;
}

interface StudioInspectorProps {
  error: string | null;
  exports: StudioExport[];
  inspector: InspectorTab;
  instruction: string;
  jobs: StudioJob[];
  latestReview: Review | null;
  loadedRevisionId: string | null;
  proposal: StudioJob | null;
  revisions: Revision[];
  settingsForm: SettingsFormState;
  onAcceptProposal: () => void;
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
  revisions,
  settingsForm,
  onAcceptProposal,
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
}: StudioInspectorProps) {
  return (
    <aside className="studio-inspector">
      <nav className="inspector-tabs">
        <button
          className={inspector === 'copilot' ? 'active' : ''}
          onClick={() => setInspector('copilot')}
          type="button"
        >
          <Bot /> Copilot
        </button>
        <button
          className={inspector === 'review' ? 'active' : ''}
          onClick={() => setInspector('review')}
          type="button"
        >
          <ShieldCheck /> Review
        </button>
        <button
          className={inspector === 'history' ? 'active' : ''}
          onClick={() => setInspector('history')}
          type="button"
        >
          <History /> History
        </button>
        <button
          className={inspector === 'jobs' ? 'active' : ''}
          onClick={() => setInspector('jobs')}
          type="button"
        >
          <Briefcase /> Jobs
        </button>
      </nav>

      {error ? <div className="inspector-error">{error}</div> : null}

      {inspector === 'copilot' && (
        <StudioCopilotPanel
          instruction={instruction}
          setInstruction={setInstruction}
          proposal={proposal}
          setProposal={setProposal}
          onRunProposal={onRunProposal}
          onAcceptProposal={onAcceptProposal}
        />
      )}
      {inspector === 'review' && (
        <StudioReviewPanel latestReview={latestReview} onRunReview={onRunReview} />
      )}
      {inspector === 'history' && (
        <StudioHistoryPanel
          revisions={revisions}
          loadedRevisionId={loadedRevisionId}
          exports={exports}
          onRestoreRevision={onRestoreRevision}
        />
      )}
      {inspector === 'jobs' && (
        <StudioJobsPanel jobs={jobs} onLoadJobs={onLoadJobs} onRetryJob={onRetryJob} />
      )}
      {inspector === 'settings' && (
        <StudioSettingsPanel
          settingsForm={settingsForm}
          setSettingsForm={setSettingsForm}
          onUpdateSettings={onUpdateSettings}
        />
      )}
    </aside>
  );
}
