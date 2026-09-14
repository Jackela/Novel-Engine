import { BookOpen, Loader2 } from "lucide-react";

import { useTranslation } from "@/app/i18n/useTranslation";
import type { ProjectCatalogItem } from "@/app/types/studio";

interface ProjectCatalogListProps {
  readonly projects: readonly ProjectCatalogItem[];
  readonly hasOlderProjects: boolean;
  readonly isLoadingOlder: boolean;
  readonly olderError: string | null;
  readonly disabled: boolean;
  readonly onOpenProject: (projectId: string) => void;
  readonly onActivateOlder: (target: HTMLButtonElement) => void;
}

/** The bounded catalog rows plus the explicit older-page continuation. */
export function ProjectCatalogList({
  projects,
  hasOlderProjects,
  isLoadingOlder,
  olderError,
  disabled,
  onOpenProject,
  onActivateOlder,
}: ProjectCatalogListProps) {
  const { t } = useTranslation();
  // Mirrors the export/review/history terminal copy: a populated catalog with
  // no continuation announces its end instead of going silent.
  const isCatalogExhausted = projects.length > 0 && !hasOlderProjects && !olderError;
  return (
    <>
      {projects.map((project) => (
        <button
          className="library__project-row"
          disabled={disabled}
          key={project.id}
          onClick={() => onOpenProject(project.id)}
          type="button"
        >
          <BookOpen aria-hidden="true" />
          <span>
            <strong>{project.title}</strong>
            <small>{project.description || t("library.catalog.noPremise")}</small>
          </span>
          <time>{new Date(project.updated_at).toLocaleDateString()}</time>
        </button>
      ))}
      {hasOlderProjects || olderError || isCatalogExhausted ? (
        <div className="library__catalog-older">
          {olderError ? (
            <p aria-live="assertive" className="ui-form-error" role="alert">
              {olderError}
            </p>
          ) : null}
          {hasOlderProjects ? (
            <button
              aria-busy={isLoadingOlder || undefined}
              className="ui-command"
              disabled={disabled || isLoadingOlder}
              onClick={(event) => onActivateOlder(event.currentTarget)}
              type="button"
            >
              {isLoadingOlder ? <Loader2 aria-hidden="true" className="ui-spin" /> : null}
              {isLoadingOlder ? t("library.action.loadingOlder") : t("library.action.loadOlder")}
            </button>
          ) : null}
          {isCatalogExhausted ? (
            <p className="library__catalog-end" role="status">
              {t("library.catalog.end")}
            </p>
          ) : null}
        </div>
      ) : null}
    </>
  );
}
