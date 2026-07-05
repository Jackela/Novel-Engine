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
}

export function StudioCopilotPanel({
  instruction,
  setInstruction,
  proposal,
  setProposal,
  onRunProposal,
  onAcceptProposal,
}: StudioCopilotPanelProps) {
  return (
    <div className="inspector-content">
      <h2>AI proposal</h2>
      <p>Copilot never changes the manuscript until you accept a proposal.</p>
      <textarea
        aria-label="Proposal instruction"
        onChange={(event) => setInstruction(event.target.value)}
        placeholder="Describe the change or direction..."
        rows={5}
        value={instruction}
      />
      <div className="inspector-actions">
        <button className="command" onClick={() => onRunProposal('rewrite')} type="button">
          <Sparkles /> Rewrite
        </button>
        <button className="command" onClick={() => onRunProposal('continue')} type="button">
          Continue
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
            <button className="command command--primary" onClick={onAcceptProposal} type="button">
              <Check /> Accept
            </button>
            <button className="command" onClick={() => setProposal(null)} type="button">
              <X /> Reject
            </button>
          </div>
        </section>
      ) : null}
    </div>
  );
}
