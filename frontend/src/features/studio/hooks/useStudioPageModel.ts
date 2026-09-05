import { useState } from "react";
import type { NavigateFunction } from "react-router-dom";

import type { StudioRouteState } from "../studioRouteState";
import { buildProposalAuditView } from "./proposalAuditView";
import { buildLoreStatusModel, buildStudioNavigatorProps } from "./studioPageModelView";
import { useActiveDocument } from "./useActiveDocument";
import { useDocumentDraft } from "./useDocumentDraft";
import { useExportDownload } from "./useExportDownload";
import { useLazyInspectorHistories } from "./useLazyInspectorHistories";
import { usePageCurrentDocument } from "./usePageCurrentDocument";
import { useScopedRevisionRestore } from "./useScopedRevisionRestore";
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
import { useStudioSearch } from "./useStudioSearch";

type Nav = NavigateFunction;

export function useStudioPageModel(projectId: string, route: StudioRouteState, navigate: Nav) {
  const { inspector: routeInspector, section } = route;
  const [activeId, setActiveId] = useState<string | null>(null);
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
  const inspectorHistories = useLazyInspectorHistories({
    enabled: project !== null,
    inspector: routeInspector,
    projectId,
    recheckProject,
    onSessionLost: navigation.onProjectResourceSessionLost,
  });
  const activeSummary = useActiveDocument(project, section, activeId);
  const currentDocument = usePageCurrentDocument(
    projectId,
    activeSummary,
    lifecycle,
    { captureProjectShellRead, publishProjectShellRead },
    navigate,
  );
  const activeDocument = currentDocument.document;
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
    activeSummary?.id ?? null,
  );
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
  const { restoringRevisionId, restoreRevision: onRestoreRevision } = useScopedRevisionRestore(
    `${projectId}\u0000${activeDocument?.id ?? ""}`,
    restoreRevision,
  );
  const { search, setSearch, isSearching, searchResults, runSearch } = useStudioSearch(
    projectId,
    projectErrors.publishers.search,
  );
  const providers = useStudioProviders();
  const { exportProject, retryExport, exportingFormat, retryingFormat, failedFormat, exportError } =
    useExportDownload(project, projectId, inspectorHistories.export.setData);
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
    setReviews: inspectorHistories.review.setData,
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
        onDraftChange: setDraft,
        onTitleChange: setTitleDraft,
        onLoadLatest: loadLatest,
        onRetryOverwrite: retryOverwrite,
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
        model: {
          copilot: {
            instruction: copilot.instruction,
            proposal: copilot.proposal,
            streamingText: copilot.streamingText,
            onRunProposal: copilot.runProposal,
            onAcceptProposal: copilot.acceptProposal,
            onStopProposal: () => copilot.stopProposal(),
            ...buildProposalAuditView(
              copilot.proposalOutcomeUnknown,
              copilot.proposalAuditStatus,
              copilot.retryProposalAudit,
            ),
            unknownAttemptOperation: copilot.unknownAttemptOperation,
            setInstruction: copilot.setInstruction,
            setProposal: copilot.setProposal,
          },
          export: {
            exports: inspectorHistories.export.data,
            historyInitialized: inspectorHistories.export.initialized,
            isLoadingHistory: inspectorHistories.export.isLoading,
            historyError: inspectorHistories.export.error,
            onRetryHistory: inspectorHistories.export.retry,
            exportingFormat,
            retryingFormat,
            failedFormat,
            errorForExport: exportError,
            onExport: exportProject,
            onRetryExport: retryExport,
          },
          review: {
            latestReview: inspectorHistories.review.data[0] ?? null,
            historyInitialized: inspectorHistories.review.initialized,
            isLoadingHistory: inspectorHistories.review.isLoading,
            historyError: inspectorHistories.review.error,
            actionError: projectErrors.errors.review,
            onRetryHistory: inspectorHistories.review.retry,
            onRunReview: runReview,
          },
          history: {
            revisions,
            loadedRevisionId: loadedRevision.current,
            historyInitialized,
            hasOlderRevisions,
            isLoadingOlder,
            isLoadingHistory,
            onLoadOlderRevisions: loadOlderRevisions,
            onRestoreRevision,
          },
          jobs: {
            jobs,
            hasOlderJobs,
            onLoadJobs: () => loadJobs("refresh"),
            onLoadOlderJobs: loadOlderJobs,
            onRetryJob: retryJob,
          },
          usage: { projectId },
          settings: {
            settingsForm,
            providers,
            error: projectErrors.errors.settings,
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
