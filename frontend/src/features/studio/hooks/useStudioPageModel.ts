import type { ComponentProps } from "react";
import { useCallback, useState } from "react";
import type { NavigateFunction } from "react-router-dom";

import type { StudioPageView } from "../StudioPageView";
import { type StudioRouteState, studioInspectorPath } from "../studioRouteState";
import { buildLoreStatusModel, buildStudioNavigatorProps } from "./studioPageModelView";
import { useActiveDocument } from "./useActiveDocument";
import { useDocumentDraft } from "./useDocumentDraft";
import { useExportDownload } from "./useExportDownload";
import { combineErrorMessages, useOwnerKeyedErrors } from "./useOwnerKeyedErrors";
import { useScopedRevisionRestore } from "./useScopedRevisionRestore";
import { useStudioActions } from "./useStudioActions";
import { useStudioInspectorState } from "./useStudioInspectorState";
import { useStudioJobs } from "./useStudioJobs";
import { useStudioProject } from "./useStudioProject";
import { useStudioProposal } from "./useStudioProposal";
import { useStudioProviders } from "./useStudioProviders";
import { useStudioSearch } from "./useStudioSearch";
import { useWholeBookLoop } from "./useWholeBookLoop";
import { wholeBookPlan } from "./wholeBookPlan";

type StudioViewProps = ComponentProps<typeof StudioPageView>;

const DOCUMENT_ERROR_SOURCES = ["draft", "proposal", "revision", "restore"] as const;
const PROJECT_ERROR_SOURCES = [
  "jobs",
  "search",
  "review",
  "settings",
  "retryJob",
  "createDocument",
  "moveDocument",
] as const;

export function useStudioPageModel(
  projectId: string,
  route: StudioRouteState,
  navigate: NavigateFunction,
): {
  project: StudioViewProps["project"] | null;
  viewProps: StudioViewProps | null;
  loadError: string | null;
  isLoading: boolean;
  retryLoad: () => Promise<void>;
} {
  const { inspector: routeInspector, section } = route;
  const [activeId, setActiveId] = useState<string | null>(null);
  const {
    project,
    setProject,
    reviews,
    setReviews,
    exports,
    setExports,
    error,
    setError,
    loadError,
    isLoading,
    retryLoad,
  } = useStudioProject(projectId);
  const activeDocument = useActiveDocument(project, section, activeId);
  const projectErrors = useOwnerKeyedErrors(projectId, PROJECT_ERROR_SOURCES);
  const documentErrors = useOwnerKeyedErrors(
    `${projectId}\u0000${activeDocument?.id ?? ""}`,
    DOCUMENT_ERROR_SOURCES,
  );
  const visibleError = combineErrorMessages(documentErrors.error, projectErrors.error, error);
  const visibleActiveId = activeDocument?.id ?? activeId;
  const {
    draft,
    setDraft,
    titleDraft,
    setTitleDraft,
    saveState,
    loadedRevision,
    revisions,
    captureAcceptance,
    restoreRevision,
    isConflictActionPending,
    loadLatest,
    retryOverwrite,
  } = useDocumentDraft(
    activeDocument,
    projectId,
    setProject,
    documentErrors.publishers.draft,
    documentErrors.publishers.revision,
    documentErrors.publishers.restore,
  );
  const {
    jobs,
    loadJobs,
    isLoading: isLoadingJobs,
    loadingInitiator: jobsLoadingInitiator,
  } = useStudioJobs(projectId, projectErrors.publishers.jobs);
  const onSelectInspector = useCallback(
    (nextInspector: Parameters<typeof studioInspectorPath>[2]) => {
      if (nextInspector === routeInspector) return;
      navigate(studioInspectorPath(projectId, section, nextInspector));
    },
    [navigate, projectId, routeInspector, section],
  );
  const { inspector, setInspector, settingsForm, setSettingsForm } = useStudioInspectorState({
    inspector: routeInspector,
    project,
    loadJobs,
    onSelectInspector,
  });
  const { restoringRevisionId, restoreRevision: onRestoreRevision } = useScopedRevisionRestore(
    `${projectId}\u0000${activeDocument?.id ?? ""}`,
    restoreRevision,
  );
  const {
    proposal,
    setProposal,
    instruction,
    setInstruction,
    runProposal,
    stopProposal,
    streamingText,
    acceptProposal,
    isRunningProposal,
    isAcceptingProposal,
  } = useStudioProposal(
    projectId,
    activeDocument,
    project,
    setProject,
    documentErrors.publishers.proposal,
    loadJobs,
    captureAcceptance,
  );
  const { search, setSearch, isSearching, searchResults, runSearch } = useStudioSearch(
    projectId,
    projectErrors.publishers.search,
  );
  // #318 whole-book loop: reuses the copilot accept refresh path so the
  // editor cache resets whenever the loop accepts the active document.
  const wholeBookLoop = useWholeBookLoop({
    projectId,
    provider: String(project?.settings.provider ?? "mock"),
    setProject,
    loadJobs,
    captureAcceptedDocument: captureAcceptance,
  });
  const providers = useStudioProviders();
  const { exportProject, retryExport, exportingFormat, retryingFormat, failedFormat, exportError } =
    useExportDownload(project, projectId, setExports);
  const {
    createDocument,
    moveDocument,
    runReview,
    updateProjectSettings,
    retryJob,
    changeLoreStatus,
    loreStatusFor,
    isRunningReview,
    isUpdatingSettings,
    isRetryingJob,
    retryingJobId,
    isCreatingDocument,
    isMovingDocument,
    creatingDocumentKind,
    movingDocument,
  } = useStudioActions({
    project,
    projectId,
    setProject,
    setReviews,
    setError,
    errorPublishers: projectErrors.publishers,
    setActiveId,
    settingsForm,
    loadJobs,
  });

  if (!project) return { project, viewProps: null, loadError, isLoading, retryLoad };

  const latestReview = reviews[0] ?? null;
  const inspectorPending = {
    proposal: {
      running: isRunningProposal,
      accepting: isAcceptingProposal,
    },
    review: isRunningReview,
    jobs: {
      loading: isLoadingJobs,
      loadingInitiator: jobsLoadingInitiator,
      retrying: isRetryingJob,
      retryingJobId,
    },
    settings: isUpdatingSettings,
    history: { restoringRevisionId },
  };

  return {
    project,
    loadError,
    isLoading,
    retryLoad,
    viewProps: {
      project,
      onBack: () => navigate("/projects"),
      navigator: buildStudioNavigatorProps(
        {
          project,
          section,
          activeId: visibleActiveId,
          search,
          isSearching,
          searchResults,
          onSearchChange: setSearch,
          onSearchSubmit: runSearch,
          onSelectDocument: setActiveId,
          createDocument,
          moveDocument,
          isCreatingDocument,
          isMovingDocument,
          creatingDocumentKind,
          movingDocument,
          wholeBook: {
            phase: wholeBookLoop.phase,
            remaining: wholeBookPlan(project).length,
            onStart: () => wholeBookLoop.start(wholeBookPlan(project)),
            onStop: () => wholeBookLoop.stop(),
          },
        },
        navigate,
      ),
      editor: {
        activeDocument,
        draft,
        titleDraft,
        saveState,
        error: documentErrors.error,
        isConflictActionPending,
        onDraftChange: setDraft,
        onTitleChange: setTitleDraft,
        onLoadLatest: loadLatest,
        onRetryOverwrite: retryOverwrite,
      },
      inspector: {
        error: visibleError,
        inspector,
        setInspector,
        pending: inspectorPending,
        // #412: per-tab groups assembled once here instead of a forwarded
        // props corridor through StudioPageView -> Inspector -> Panels.
        model: {
          copilot: {
            instruction,
            proposal,
            streamingText,
            onRunProposal: runProposal,
            onAcceptProposal: acceptProposal,
            onStopProposal: () => stopProposal(),
            setInstruction,
            setProposal,
          },
          export: {
            exports,
            exportingFormat,
            retryingFormat,
            failedFormat,
            errorForExport: exportError,
            onExport: exportProject,
            onRetryExport: retryExport,
          },
          review: {
            latestReview,
            onRunReview: runReview,
          },
          history: {
            revisions,
            loadedRevisionId: loadedRevision.current,
            onRestoreRevision,
          },
          jobs: {
            jobs,
            onLoadJobs: () => loadJobs("refresh"),
            onRetryJob: retryJob,
          },
          usage: { projectId },
          settings: {
            settingsForm,
            providers,
            onUpdateSettings: updateProjectSettings,
            setSettingsForm,
          },
          loreStatus: buildLoreStatusModel(
            activeDocument,
            changeLoreStatus,
            activeDocument
              ? loreStatusFor(activeDocument.id)
              : { isSaving: false, error: null, attemptedStatus: null },
          ),
        },
      },
      statusbar: {
        activeDocument,
        loadedRevisionId: loadedRevision.current,
        saveState,
      },
    },
  };
}
