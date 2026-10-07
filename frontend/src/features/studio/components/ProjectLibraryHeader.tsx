import { BookOpen, Loader2, LogOut } from "lucide-react";

import { useTranslation } from "@/app/i18n/useTranslation";
import { LanguageSwitch } from "@/app/LanguageSwitch";
import { productIdentity } from "@/app/productIdentity";
import { ThemeSwitch } from "@/app/ThemeSwitch";

import type { LibraryOperation } from "../hooks/useProjectLibraryActions";

interface ProjectLibraryHeaderProps {
  readonly isLoading: boolean;
  readonly operation: LibraryOperation | null;
  readonly onSignOut: (target: HTMLButtonElement) => void;
}

/**
 * The library header: product identity, language and theme switches,
 * and the single sign-out command. Sign-out reports busy while the
 * logout operation holds the page's command slot, and the command
 * locks while any operation runs.
 */
export function ProjectLibraryHeader({
  isLoading,
  operation,
  onSignOut,
}: ProjectLibraryHeaderProps) {
  const { t } = useTranslation();
  return (
    <header className="library__header">
      <div className="ui-brand">
        <BookOpen aria-hidden="true" /> {productIdentity.name}
      </div>
      <div className="library__header-actions">
        <LanguageSwitch />
        <ThemeSwitch />
        <button
          aria-busy={operation === "logout" || undefined}
          aria-label={t("library.action.signOut")}
          className="ui-command--icon"
          disabled={operation !== null || isLoading}
          onClick={(event) => onSignOut(event.currentTarget)}
          title={t("library.action.signOut")}
          type="button"
        >
          {operation === "logout" ? (
            <Loader2 aria-hidden="true" className="ui-spin" />
          ) : (
            <LogOut aria-hidden="true" />
          )}
        </button>
      </div>
    </header>
  );
}
