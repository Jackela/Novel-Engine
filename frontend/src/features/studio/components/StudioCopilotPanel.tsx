import { Check, Sparkles, X } from 'lucide-react';
import type { Dispatch, SetStateAction } from 'react';

import type { StudioJob } from '@/app/types/studio';

interface StudioCopilotPanelProps {
  instruction: string;
  setInstruction: Dispatch<SetStateAction<string>>;
  proposal: StudioJob | null;
  setProposal: Dispatch<SetStateAction<StudioJob | null>>;
  onRunProposal: (operation: 'continue' | 'rewrite') => void;
  onAcceptProposal: () => void;
  /** True while a proposal request is in flight. */
  isRunningProposal?: boolean;
  /** True while accepting the currently displayed proposal. */
  isAcceptingProposal?: boolean;
}

export function StudioCopilotPanel({
  instruction,
  setInstruction,
  proposal,
  setProposal,
  onRunProposal,
  onAcceptProposal,
  isRunningProposal = false,
  isAcceptingProposal = false,
}: StudioCopilotPanelProps) {
  const isBusy = isRunningProposal || isAcceptingProposal;

  return (
    <div aria-busy={isBusy} className="inspector-content">
      <h2>AI proposal</h2>
      <p>Copilot never changes the manuscript until you accept a proposal.</p>
      <textarea
        aria-label="Proposal instruction"
        disabled={isBusy}
        onChange={(event) => setInstruction(event.target.value)}
        placeholder="Describe the change or direction..."
        rows={5}
        value={instruction}
      />
      <div className="inspector-actions">
        <button
          aria-busy={isRunningProposal}
          className="command"
          disabled={isBusy}
          onClick={() => onRunProposal('rewrite')}
          type="button"
        >
          <Sparkles /> Rewrite
        </button>
        <button
          aria-busy={isRunningProposal}
          className="command"
          disabled={isBusy}
          onClick={() => onRunProposal('continue')}
          type="button"
        >
          {isRunningProposal ? 'Generating…' : 'Continue'}
        </button>
      </div>
      {proposal?.result.proposal_markdown ? (
        <section className="proposal">
          <header>
            <strong>Proposed Markdown</strong>
            <span>Preview only</span>
          </header>
          <pre>{proposal.result.proposal_markdown}</pre>
          <div className="inspector-actions">
            <button
              aria-busy={isAcceptingProposal}
              className="command command--primary"
              disabled={isBusy}
              onClick={onAcceptProposal}
              type="button"
            >
              <Check /> Accept
            </button>
            <button
              className="command"
              disabled={isBusy}
              onClick={() => setProposal(null)}
              type="button"
            >
              <X /> Reject
            </button>
          </div>
        </section>
      ) : null}
    </div>
  );
}
