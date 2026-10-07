import { useTranslation } from "@/app/i18n/useTranslation";

import { ProjectCatalogList } from "./components/ProjectCatalogList";
import { ProjectLibraryCreateForm } from "./components/ProjectLibraryCreateForm";
import { ProjectLibraryHeader } from "./components/ProjectLibraryHeader";
import { ProjectLibraryLoadState } from "./components/ProjectLibraryLoadState";
import { useProjectLibraryActions } from "./hooks/useProjectLibraryActions";

/**
 * The project library entry page: the project catalog with its
 * older-page continuation, the create-project form, and the
 * page-level commands sharing one single-flight command slot —
 * create, sign-out, retry, delete, and load older.
 */
export function ProjectLibraryPage() {
  const { t } = useTranslation();
  const {
    actionError,
    activateLoadOlder,
    createButtonRef,
    deletion,
    description,
    error,
    hasLoaded,
    headingRef,
    isLoading,
    isLoadingOlder,
    nextCursor,
    olderError,
    openProject,
    operation,
    projects,
    requestDelete,
    requestRetry,
    requestSignOut,
    setDescription,
    setTitle,
    submitProject,
    title,
  } = useProjectLibraryActions();

  return (
    <main className="library">
      <ProjectLibraryHeader
        isLoading={isLoading}
        onSignOut={requestSignOut}
        operation={operation}
      />

      <section className="library__content">
        <div className="library__heading">
          <div>
            <h1 ref={headingRef} tabIndex={-1}>
              {t("library.heading.projects")}
            </h1>
            <p>{t("library.intro")}</p>
          </div>
        </div>
        {actionError ? (
          <p aria-live="assertive" className="library__action-error ui-form-error" role="alert">
            {actionError}
          </p>
        ) : null}
        {deletion.deletionNotice !== null ? (
          <p aria-live="polite" className="library__deletion-notice" role="status">
            {deletion.deletionNotice}
          </p>
        ) : null}
        {!hasLoaded ? (
          <ProjectLibraryLoadState
            commandsLocked={operation !== null}
            error={error}
            headingRef={headingRef}
            isLoading={isLoading}
            onRetry={requestRetry}
          />
        ) : (
          <div className="library__grid">
            <ProjectLibraryCreateForm
              createButtonRef={createButtonRef}
              description={description}
              onDescriptionChange={setDescription}
              onSubmit={submitProject}
              onTitleChange={setTitle}
              operation={operation}
              title={title}
            />
            <ProjectCatalogList
              confirmingDeleteId={deletion.confirmingProjectId}
              deleteErrorFor={deletion.deleteErrorFor}
              deletingProjectId={deletion.deletingProjectId}
              disabled={operation !== null || isLoadingOlder}
              hasOlderProjects={nextCursor !== null}
              isLoadingOlder={isLoadingOlder}
              olderError={olderError}
              onActivateOlder={activateLoadOlder}
              onConfirmingDeleteChange={deletion.setConfirmingProjectId}
              onDeleteProject={requestDelete}
              onOpenProject={openProject}
              projects={projects}
            />
          </div>
        )}
      </section>
    </main>
  );
}
