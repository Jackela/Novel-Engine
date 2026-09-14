import { AlertCircle, Check, Loader2 } from "lucide-react";

import { useTranslation } from "@/app/i18n/useTranslation";
import { productLabel } from "@/app/productIdentity";
import type { SaveState, StudioDocument } from "@/app/types/studio";

interface StudioStatusbarProps {
  activeDocument: StudioDocument | null;
  loadedRevisionId: string | null;
  saveState: SaveState;
}

export function StudioStatusbar({
  activeDocument,
  loadedRevisionId,
  saveState,
}: StudioStatusbarProps) {
  const { t } = useTranslation();
  const wordCount = activeDocument?.word_count ?? 0;
  return (
    <footer className="studio-statusbar">
      <span>
        {saveState === "error" ? (
          <AlertCircle />
        ) : saveState === "saving" ? (
          <Loader2 className="ui-spin" />
        ) : (
          <Check />
        )}{" "}
        {saveState === "saving"
          ? t("statusbar.saving")
          : saveState === "conflict"
            ? t("statusbar.conflict")
            : saveState === "error"
              ? t("statusbar.error")
              : t("statusbar.saved")}
      </span>
      <span>{t("statusbar.revision", { id: loadedRevisionId?.slice(0, 8) ?? "none" })}</span>
      <span className="studio-statusbar__spacer" />
      <span>
        {t("statusbar.words", {
          count: wordCount,
          unit: wordCount === 1 ? t("noun.word") : t("noun.words"),
        })}
      </span>
      <span>{productLabel}</span>
    </footer>
  );
}
