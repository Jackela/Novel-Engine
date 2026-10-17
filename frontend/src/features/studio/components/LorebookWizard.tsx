import { useState } from "react";

import { translateActive } from "@/app/i18n/translate";
import type { DocumentSummary, StudioDocument } from "@/app/types/studio";

import { useLorebookWizard } from "../hooks/useLorebookWizard";
import { LorebookWizardCandidates } from "./LorebookWizardCandidates";
import { LorebookWizardResults } from "./LorebookWizardResults";
import { LorebookWizardSegments } from "./LorebookWizardSegments";

interface LorebookWizardProps {
  readonly projectId: string;
  readonly provider: string;
  readonly documents: DocumentSummary[];
  readonly onDocumentCreated?: (document: StudioDocument) => void;
}

/**
 * The lorebook initialization wizard flow (#614): input segments (paste or
 * picked chapter documents) each run as their own extraction Job, completed
 * segments fold into one merged candidate list, and confirmation reports
 * each candidate's two-step outcome. The session lives in this component's
 * hook; unmounting the project abandons it. After a confirmation, Start
 * over revisits the extracted segments without offering already-created
 * entries again. Failed alias writes remain independently retryable.
 */
export function LorebookWizard({
  projectId,
  provider,
  documents,
  onDocumentCreated,
}: LorebookWizardProps) {
  const wizard = useLorebookWizard(projectId, provider, onDocumentCreated);
  const [continuing, setContinuing] = useState(false);
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
      {hasResults && !wizard.isConfirming ? (
        <LorebookWizardResults
          results={wizard.results}
          onRetryAliases={wizard.retryAliases}
          onStartOver={() => {
            wizard.clearResults();
            setContinuing(true);
          }}
        />
      ) : null}
      {!hasResults || continuing || wizard.isConfirming ? (
        <LorebookWizardCandidates
          candidates={wizard.candidates}
          deselected={wizard.deselected}
          selectedCount={wizard.selectedCandidates.length}
          aliasDrafts={wizard.aliasDrafts}
          isConfirming={wizard.isConfirming}
          aliasesFor={wizard.aliasesFor}
          onToggle={wizard.toggleCandidate}
          onAliasDraft={wizard.setAliasDraft}
          onConfirm={() => {
            setContinuing(false);
            return wizard.confirmSelected();
          }}
          onAbandon={() => {
            wizard.reset();
            setContinuing(false);
          }}
        />
      ) : null}
    </div>
  );
}
