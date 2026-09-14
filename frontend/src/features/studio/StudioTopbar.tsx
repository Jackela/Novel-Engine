import { BookOpen, ChevronLeft } from "lucide-react";
import type { Ref } from "react";
import { useTranslation } from "@/app/i18n/useTranslation";
import { LanguageSwitch } from "@/app/LanguageSwitch";
import { productIdentity } from "@/app/productIdentity";
import { ThemeSwitch } from "@/app/ThemeSwitch";
import type { Project } from "@/app/types/studio";

interface StudioTopbarProps {
  project: Project;
  onBack: () => void;
  headingRef?: Ref<HTMLHeadingElement>;
}

export function StudioTopbar({ project, onBack, headingRef }: StudioTopbarProps) {
  const { t } = useTranslation();
  return (
    <header className="studio-topbar">
      <button
        aria-label={t("shell.action.backToProjects")}
        className="ui-command--icon"
        onClick={onBack}
        type="button"
      >
        <ChevronLeft />
      </button>
      <div className="ui-brand">
        <BookOpen /> {productIdentity.name}
      </div>
      <h1
        className="studio-topbar__project-title"
        id="studio-project-title"
        ref={headingRef}
        tabIndex={-1}
      >
        {project.title}
      </h1>
      <div className="studio-topbar__spacer" />
      <LanguageSwitch />
      <ThemeSwitch />
    </header>
  );
}
