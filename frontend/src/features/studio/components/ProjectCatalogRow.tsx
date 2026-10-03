import { BookOpen, Loader2, Trash2 } from "lucide-react";
import { type KeyboardEvent, useEffect, useRef } from "react";

import { formatDate } from "@/app/i18n/format";
import { useTranslation } from "@/app/i18n/useTranslation";
import type { ProjectCatalogItem } from "@/app/types/studio";

interface ProjectCatalogRowProps {
  readonly project: ProjectCatalogItem;
  /** Another library command (create/logout/reload) owns the page. */
  readonly disabled: boolean;
  readonly isConfirmingDelete: boolean;
  readonly isDeleting: boolean;
  readonly deleteError: string | null;
  readonly onOpenProject: (projectId: string) => void;
  readonly onConfirmingDeleteChange: (projectId: string | null) => void;
  readonly onDeleteProject: (target: HTMLButtonElement, projectId: string, title: string) => void;
}

/**
 * One catalog row: the open command, the irreversible project deletion
 * behind an inline confirmation, and the row-scoped delete failure. The
 * confirmation states the removed surface (documents, revisions, exports,
 * snapshots; backups untouched) because the DELETE drops all of it. Escape
 * cancels; focus moves deliberately between trigger and confirmation and
 * returns to the trigger after cancelling.
 */
export function ProjectCatalogRow({
  project,
  disabled,
  isConfirmingDelete,
  isDeleting,
  deleteError,
  onOpenProject,
  onConfirmingDeleteChange,
  onDeleteProject,
}: ProjectCatalogRowProps) {
  const { t } = useTranslation();
  const deleteButtonRef = useRef<HTMLButtonElement | null>(null);
  const confirmButtonRef = useRef<HTMLButtonElement | null>(null);

  // Deliberate focus movement: opening the confirmation hands focus to its
  // confirm control so keyboard authors review the warning before firing.
  useEffect(() => {
    if (isConfirmingDelete) confirmButtonRef.current?.focus();
  }, [isConfirmingDelete]);

  const cancelDelete = () => {
    onConfirmingDeleteChange(null);
    deleteButtonRef.current?.focus();
  };
  const onConfirmKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") {
      event.stopPropagation();
      cancelDelete();
    }
  };

  return (
    <div className="library__project-row-wrap">
      <button
        className="library__project-row"
        disabled={disabled}
        onClick={() => onOpenProject(project.id)}
        type="button"
      >
        <BookOpen aria-hidden="true" />
        <span>
          <strong>{project.title}</strong>
          <small>{project.description || t("library.catalog.noPremise")}</small>
        </span>
        <time>{formatDate(project.updated_at)}</time>
      </button>
      <span className="library__project-actions">
        <button
          aria-busy={isDeleting || undefined}
          aria-label={
            isDeleting
              ? t("library.row.deleting", { title: project.title })
              : t("library.row.delete", { title: project.title })
          }
          disabled={disabled || isDeleting}
          onClick={() => onConfirmingDeleteChange(project.id)}
          ref={deleteButtonRef}
          title={isDeleting ? t("library.row.deletingTitle") : t("library.row.deleteTitle")}
          type="button"
        >
          {isDeleting ? (
            <Loader2 aria-hidden="true" className="ui-spin" />
          ) : (
            <Trash2 aria-hidden="true" />
          )}
        </button>
      </span>
      {isConfirmingDelete ? (
        // biome-ignore lint/a11y/useSemanticElements: this confirmation strip is not a form control group; <fieldset> would misrepresent semantics and drag in default fieldset styling.
        <div
          aria-label={t("library.row.confirmHeading", { title: project.title })}
          className="library__project-confirm"
          onKeyDown={onConfirmKeyDown}
          role="group"
        >
          <p>{t("library.row.confirmBody", { title: project.title })}</p>
          <span className="library__project-confirm-actions">
            <button
              aria-busy={isDeleting || undefined}
              aria-label={
                isDeleting
                  ? t("library.row.deleting", { title: project.title })
                  : t("library.row.confirmDelete", { title: project.title })
              }
              disabled={disabled || isDeleting}
              onClick={(event) => onDeleteProject(event.currentTarget, project.id, project.title)}
              ref={confirmButtonRef}
              type="button"
            >
              {isDeleting ? t("library.row.confirmingAction") : t("library.row.confirmAction")}
            </button>
            <button
              aria-label={t("library.row.cancelDelete", { title: project.title })}
              disabled={disabled || isDeleting}
              onClick={cancelDelete}
              type="button"
            >
              {t("library.row.cancel")}
            </button>
          </span>
          {deleteError !== null ? (
            <p aria-live="assertive" className="library__project-error" role="alert">
              {deleteError}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
