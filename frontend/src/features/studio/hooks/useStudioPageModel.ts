import type { NavigateFunction } from "react-router-dom";

import type { StudioRouteState } from "../studioRouteState";
import { buildNavigatorCommands } from "./navigatorCommands";
import { buildProposalUndo } from "./proposalUndo";
import { buildStudioInspectorModel, buildStudioNavigatorProps } from "./studioPageModelView";
import { useStudioSearchModel } from "./studioSearchModel";
import { useDiagnosticsDownload } from "./useDiagnosticsDownload";
import { useExportDownload } from "./useExportDownload";
import { useLazyInspectorHistories } from "./useLazyInspectorHistories";
import { usePageActiveDocument } from "./usePageActiveDocument";
import { usePageDocumentDraft } from "./usePageDocumentDraft";
import { reviewInspectorModel } from "./useReviewHistory";
import { revisionPreviewScope } from "./useRevisionPreview";
import { useStudioActions } from "./useStudioActions";
import { useStudioErrorChannels } from "./useStudioErrorChannels";
import { useStudioGeneration } from "./useStudioGeneration";
import { useStudioInspectorState } from "./useStudioInspectorState";
import {
  buildInspectorPending,
  buildWholeBookNavigatorModel,
  useStudioPageNavigation,
} from "./useStudioPageNavigation";
import { useStudioProject } from "./useStudioProject";
import { useStudioProviders } from "./useStudioProviders";

type Nav = NavigateFunction;

/**
 * Compose the whole studio page behind one route-scoped model: the project
 * shell, the active document with its draft, and every inspector family,
 * each owning its own requests and error channels.
 */
export function useStudioPageModel(projectId: string, route: StudioRouteState, navigate: Nav) {
  const { inspector: routeInspector, section } = route;
  const {
    project,
    setProject,
    error,
    setError,
    loadError,
    isLoading,
    retryLoad,
    lifecycle,
    captureProjectShellRead,
    publishProjectShellRead,
    recheckProject,
  } = useStudioProject(projectId);
  const navigation = useStudioPageNavigation({ navigate, projectId, section, routeInspector });
  // #478: every URL-selected inspector history family and its activation gate
  // lives behind this shell; Export no longer bypasses it at the page model.
  const inspectorHistories = useLazyInspectorHistories({
    enabled: project !== null,
    inspector: routeInspector,
    projectId,
    recheckProject,
    onSessionLost: navigation.onProjectResourceSessionLost,
  });
  const { activeId, setActiveId, activeSummary, currentDocument, activeDocument } =
    usePageActiveDocument({
      projectId,
      project,
      section,
      lifecycle,
      shellReadAuthority: { captureProjectShellRead, publishProjectShellRead },
      navigate,
    });
  const { projectErrors, documentErrors, visibleError, visibleErrorWithoutSettings } =
    useStudioErrorChannels(projectId, activeSummary?.id ?? null, error);
  const {
    draft,
    setDraft,
    titleDraft,
    setTitleDraft,
    saveState,
    loadedRevision,
    revisions,
    historyInitialized,
    hasOlderRevisions,
    isLoadingOlder,
    isLoadingHistory,
    loadOlderRevisions,
    captureAcceptance,
    restoringRevisionId,
    onRestoreRevision,
    isConflictActionPending,
    loadLatest,
    retryOverwrite,
    retrySave,
    saveNow,
  } = usePageDocumentDraft({
    projectId,
    activeDocument,
    selectedDocumentId: activeSummary?.id ?? null,
    setProject,
    draftError: documentErrors.publishers.draft,
    revisionError: documentErrors.publishers.revision,
    restoreError: documentErrors.publishers.restore,
  });
  const generation = useStudioGeneration({
    projectId,
    activeDocument,
    project,
    setProject,
    setProposalError: documentErrors.publishers.proposal,
    setJobsError: projectErrors.publishers.jobs,
    captureAcceptance,
  });
  const {
    jobs,
    loadJobs,
    loadOlderJobs,
    hasOlderJobs,
    isLoading: isLoadingJobs,
    loadingInitiator: jobsLoadingInitiator,
    proposalAudit,
    proposalAuditGated,
    copilot,
    wholeBookLoop,
  } = generation;
  const { inspector, setInspector, settingsForm, setSettingsForm } = useStudioInspectorState({
    inspector: routeInspector,
    project,
    loadJobs,
    onSelectInspector: navigation.onSelectInspector,
  });
  const { reveal, model: searchModel } = useStudioSearchModel(
    projectId,
    projectErrors.publishers.search,
    setActiveId,
  );
  const providers = useStudioProviders();
  const exportHistory = inspectorHistories.exportHistory;
  const exportDownload = useExportDownload(
    project,
    projectId,
    exportHistory.applyRefreshedFirstPage,
  );
  const diagnosticsDownload = useDiagnosticsDownload(projectId);
  const studioActions = useStudioActions({
    project,
    projectId,
    setProject,
    setReviewPage: inspectorHistories.review.setFirstPage,
    setError,
    errorPublishers: projectErrors.publishers,
    setActiveId,
    settingsForm,
    setSettingsForm,
    onSettingsSessionLost: navigation.onProjectResourceSessionLost,
    onSettingsProjectMissing: navigation.onSettingsProjectMissing,
    loadJobs,
    isProposalActionGated: proposalAudit.isGated,
  });
  const {
    createDocument,
    moveDocument,
    runReview,
    updateProjectSettings,
    retryJob,
    changeLoreStatus,
    loreStatusFor,
    linkBeat,
    beatFor,
    isRunningReview,
    isUpdatingSettings,
    isRetryingJob,
    retryingJobId,
    isCreatingDocument,
    isMovingDocument,
    creatingDocumentKind,
    movingDocument,
  } = studioActions;

  if (!project) return { project, viewProps: null, loadError, isLoading, retryLoad };

  const inspectorPending = buildInspectorPending({
    copilot,
    isRunningReview,
    jobs: {
      isLoading: isLoadingJobs,
      loadingInitiator: jobsLoadingInitiator,
      isRetrying: isRetryingJob,
      retryGated: proposalAuditGated,
      retryingJobId,
    },
    isUpdatingSettings,
    restoringRevisionId,
  });

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
          activeId: activeSummary?.id ?? activeId,
          ...searchModel,
          onSelectDocument: setActiveId,
          createDocument,
          moveDocument,
          isCreatingDocument,
          isMovingDocument,
          creatingDocumentKind,
          movingDocument,
          // #481/DR-017: the Navigator's row and volume commands with their
          // exact pending identities and inline error surfaces.
          ...buildNavigatorCommands(studioActions),
          wholeBook: buildWholeBookNavigatorModel(project, wholeBookLoop),
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
        // DR-029: the locate intent reaches the editor only once its target
        // document is the active one; other documents never consume it.
        reveal: reveal !== null && reveal.documentId === activeSummary?.id ? reveal : null,
        onDraftChange: setDraft,
        onTitleChange: setTitleDraft,
        onLoadLatest: loadLatest,
        onRetryOverwrite: retryOverwrite,
        onRetrySave: retrySave,
        onSaveNow: saveNow,
        isLoadingDocument: currentDocument.isLoading,
        documentLoadError: currentDocument.error,
        onRetryDocument: currentDocument.retry,
      },
      inspector: {
        error: inspector === "settings" ? visibleErrorWithoutSettings : visibleError,
        inspector,
        setInspector,
        pending: inspectorPending,
        // #412: per-tab groups assembled once here instead of a forwarded
        // props corridor through StudioPageView -> Inspector -> Panels.
        model: buildStudioInspectorModel({
          projectId,
          lore: {
            provider: String(project.settings.provider ?? "mock"),
            documents: project.documents,
          },
          copilot,
          proposalUndo: buildProposalUndo(copilot, onRestoreRevision),
          jobs: {
            projectId,
            jobs,
            hasOlderJobs,
            onLoadJobs: () => loadJobs("refresh"),
            onLoadOlderJobs: loadOlderJobs,
            onRetryJob: retryJob,
          },
          export: { ...exportDownload, history: exportHistory },
          review: reviewInspectorModel(
            inspectorHistories.review,
            projectErrors.errors.review,
            runReview,
          ),
          history: {
            revisions,
            loadedRevisionId: loadedRevision.current,
            historyInitialized,
            hasOlderRevisions,
            isLoadingOlder,
            isLoadingHistory,
            onLoadOlderRevisions: loadOlderRevisions,
            onRestoreRevision,
            preview: revisionPreviewScope(projectId, activeDocument),
          },
          settings: {
            settingsForm,
            providers,
            error: projectErrors.errors.settings,
            onUpdateSettings: updateProjectSettings,
            setSettingsForm,
            diagnostics: {
              onExport: diagnosticsDownload.exportDiagnostics,
              isExporting: diagnosticsDownload.isExportingDiagnostics,
              error: diagnosticsDownload.diagnosticsError,
            },
          },
          narrowCommands: {
            activeSummary,
            activeDocument,
            changeLoreStatus,
            loreStatusFor,
            linkBeat,
            beatFor,
          },
        }),
      },
      statusbar: {
        activeDocument,
        loadedRevisionId: loadedRevision.current,
        saveState,
      },
    },
  };
}
