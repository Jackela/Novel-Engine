import { translateActive } from "@/app/i18n/translate";
import type { DocumentSummary } from "@/app/types/studio";

import { useLorebookWizard } from "../hooks/useLorebookWizard";
import { LorebookWizardCandidates } from "./LorebookWizardCandidates";
import { LorebookWizardResults } from "./LorebookWizardResults";
import { LorebookWizardSegments } from "./LorebookWizardSegments";

interface LorebookWizardProps {
  readonly projectId: string;
  readonly provider: string;
  readonly documents: DocumentSummary[];
}

/**
 * The lorebook initialization wizard flow (#614): input segments (paste or
 * picked chapter documents) each run as their own extraction Job, completed
 * segments fold into one merged candidate list, and confirmation reports
 * each candidate's two-step outcome. The session lives in this component's
 * hook; unmounting the project abandons it. After a confirmation, Start
 * over clears only the results — the extracted segments stay, so the merged
 * candidates remain reachable for another run.
 */
export function LorebookWizard({ projectId, provider, documents }: LorebookWizardProps) {
  const wizard = useLorebookWizard(projectId, provider);
  const hasResults = wizard.results.length > 0;

  return (
    <div className="lore-wizard">
      <LorebookWizardSegments
        documents={documents}
        segments={wizard.segments}
        onSubmitPaste={(text) =>
          wizard.submitSegment(text, translateActive("lore.input.pasteLabel"))
        }
        onSubmitDocument={(document) => wizard.submitDocumentSegment(document)}
        onRetrySegment={wizard.retrySegment}
      />
      {hasResults ? (
        <LorebookWizardResults
          results={wizard.results}
          onRetryAliases={wizard.retryAliases}
          onStartOver={wizard.clearResults}
        />
      ) : (
        <LorebookWizardCandidates
          candidates={wizard.candidates}
          deselected={wizard.deselected}
          selectedCount={wizard.selectedCandidates.length}
          aliasDrafts={wizard.aliasDrafts}
          isConfirming={wizard.isConfirming}
          aliasesFor={wizard.aliasesFor}
          onToggle={wizard.toggleCandidate}
          onAliasDraft={wizard.setAliasDraft}
          onConfirm={wizard.confirmSelected}
          onAbandon={wizard.reset}
        />
      )}
    </div>
  );
}
