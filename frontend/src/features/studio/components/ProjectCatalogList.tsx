import { Loader2 } from "lucide-react";

import { useTranslation } from "@/app/i18n/useTranslation";
import type { ProjectCatalogItem } from "@/app/types/studio";

import { ProjectCatalogRow } from "./ProjectCatalogRow";

interface ProjectCatalogListProps {
  readonly projects: readonly ProjectCatalogItem[];
  readonly hasOlderProjects: boolean;
  readonly isLoadingOlder: boolean;
  readonly olderError: string | null;
  readonly disabled: boolean;
  readonly confirmingDeleteId: string | null;
  readonly deletingProjectId: string | null;
  readonly deleteErrorFor: (projectId: string) => string | null;
  readonly onOpenProject: (projectId: string) => void;
  readonly onActivateOlder: (target: HTMLButtonElement) => void;
  readonly onConfirmingDeleteChange: (projectId: string | null) => void;
  readonly onDeleteProject: (target: HTMLButtonElement, projectId: string, title: string) => void;
}

/** The bounded catalog rows plus the explicit older-page continuation. */
export function ProjectCatalogList({
  projects,
  hasOlderProjects,
  isLoadingOlder,
  olderError,
  disabled,
  confirmingDeleteId,
  deletingProjectId,
  deleteErrorFor,
  onOpenProject,
  onActivateOlder,
  onConfirmingDeleteChange,
  onDeleteProject,
}: ProjectCatalogListProps) {
  const { t } = useTranslation();
  // Mirrors the export/review/history terminal copy: a populated catalog with
  // no continuation announces its end instead of going silent.
  const isCatalogExhausted = projects.length > 0 && !hasOlderProjects && !olderError;
  return (
    <>
      {projects.map((project) => (
        <ProjectCatalogRow
          deleteError={deleteErrorFor(project.id)}
          disabled={disabled}
          isConfirmingDelete={confirmingDeleteId === project.id}
          isDeleting={deletingProjectId === project.id}
          key={project.id}
          onConfirmingDeleteChange={onConfirmingDeleteChange}
          onDeleteProject={onDeleteProject}
          onOpenProject={onOpenProject}
          project={project}
        />
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
