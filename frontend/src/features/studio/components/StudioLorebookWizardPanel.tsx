import { useTranslation } from "@/app/i18n/useTranslation";
import type { DocumentSummary } from "@/app/types/studio";
import { isLoreEntryKind } from "../studioConstants";
import { LorebookWizard } from "./LorebookWizard";

interface StudioLorebookWizardPanelProps {
  readonly projectId: string;
  /** The project's configured provider; `mock` is the built-in trial provider. */
  readonly provider: string;
  /** The project shell's document summaries drive the picker and empty state. */
  readonly documents: DocumentSummary[];
}

/**
 * The Inspector's `lore` tab panel (#614): hosts the lorebook initialization
 * wizard. A project with no character/world documents surfaces the wizard as
 * the onboarding moment (the empty-lorebook guidance); a populated lorebook
 * keeps a persistent entry for re-extraction. Trial-provider projects carry
 * the same trial-mode wording family as the first-run explainer (#615).
 */
export function StudioLorebookWizardPanel({
  projectId,
  provider,
  documents,
}: StudioLorebookWizardPanelProps) {
  const { t } = useTranslation();
  const isTrialProvider = provider === "mock";
  const hasLoreEntries = documents.some((document) => isLoreEntryKind(document.kind));

  return (
    <div className="studio-inspector__panel">
      <header className="studio-inspector__heading">
        <div>
          <h2>{t("lore.heading")}</h2>
          <p>{hasLoreEntries ? t("lore.populated.hint") : t("lore.empty.guidance")}</p>
        </div>
      </header>
      {isTrialProvider ? <p className="lore-wizard__trial-note">{t("lore.trialNote")}</p> : null}
      <LorebookWizard documents={documents} projectId={projectId} provider={provider} />
    </div>
  );
}
