import { useCallback, useState } from 'react';
import type { ComponentProps } from 'react';
import type { NavigateFunction } from 'react-router-dom';

import type { StudioDocument } from '@/app/types/studio';

import { StudioPageView } from '../StudioPageView';
import { buildStudioNavigatorProps } from './studioPageModelView';
import { useActiveDocument } from './useActiveDocument';
import { useDocumentDraft } from './useDocumentDraft';
import { useExportDownload } from './useExportDownload';
import { useStudioActions } from './useStudioActions';
import { useStudioInspectorState } from './useStudioInspectorState';
import { useStudioJobs } from './useStudioJobs';
import { useStudioProject } from './useStudioProject';
import { useStudioProposal } from './useStudioProposal';
import { useStudioProviders } from './useStudioProviders';
import { useStudioSearch } from './useStudioSearch';
import { wholeBookPlan } from './wholeBookPlan';
import { useWholeBookLoop } from './useWholeBookLoop';

type StudioViewProps = ComponentProps<typeof StudioPageView>;

export function useStudioPageModel(
  projectId: string,
  section: string,
  navigate: NavigateFunction,
): {
  project: StudioViewProps['project'] | null;
  viewProps: StudioViewProps | null;
  loadError: string | null;
} {
  const [activeId, setActiveId] = useState<string | null>(null);
  const [restoringRevisionId, setRestoringRevisionId] = useState<string | null>(null);
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
  } = useStudioProject(projectId);
  const activeDocument = useActiveDocument(project, section, activeId);
  const visibleActiveId = activeDocument?.id ?? activeId;
  const {
    draft,
    setDraft,
    titleDraft,
    setTitleDraft,
    saveState,
    loadedRevision,
    revisions,
    resetFor,
    restoreRevision,
    isConflictActionPending,
    loadLatest,
    retryOverwrite,
  } = useDocumentDraft(activeDocument, projectId, setProject, setError);
  const { jobs, loadJobs, isLoading: isLoadingJobs } = useStudioJobs(projectId, setError);
  const { inspector, setInspector, settingsForm, setSettingsForm } = useStudioInspectorState({
    section,
    project,
    loadJobs,
  });
  const onProposalAccepted = useCallback(
    (document: StudioDocument) => resetFor(document, 'saved'),
    [resetFor],
  );
  const onRestoreRevision = useCallback(
    async (revisionId: string) => {
      setRestoringRevisionId(revisionId);
      try {
        await restoreRevision(revisionId);
      } finally {
        setRestoringRevisionId(null);
      }
    },
    [restoreRevision],
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
    setInspector,
    setError,
    loadJobs,
    onProposalAccepted,
  );
  const { search, setSearch, isSearching, searchResults, runSearch } = useStudioSearch(
    projectId,
    setError,
  );
  // #318 whole-book loop: reuses the copilot accept refresh path so the
  // editor cache resets whenever the loop accepts the active document.
  const wholeBookLoop = useWholeBookLoop({
    projectId,
    provider: String(project?.settings.provider ?? 'mock'),
    setProject,
    loadJobs,
    onAccepted: onProposalAccepted,
  });
  const providers = useStudioProviders();
  const { exportProject, exportingFormat, failedFormat } = useExportDownload(
    project,
    projectId,
    setExports,
    setError,
  );
  const {
    createDocument,
    moveDocument,
    runReview,
    updateProjectSettings,
    retryJob,
    isRunningReview,
    isUpdatingSettings,
    isRetryingJob,
    retryingJobId,
    isCreatingDocument,
    isMovingDocument,
  } = useStudioActions({
    project,
    projectId,
    setProject,
    setReviews,
    setError,
    setActiveId,
    setInspector,
    settingsForm,
    loadJobs,
  });

  if (!project) return { project, viewProps: null, loadError };

  const latestReview = reviews[0] ?? null;
  const inspectorPending = {
    proposal: {
      running: isRunningProposal,
      accepting: isAcceptingProposal,
    },
    review: isRunningReview,
    jobs: {
      loading: isLoadingJobs,
      retrying: isRetryingJob,
      retryingJobId,
    },
    settings: isUpdatingSettings,
    history: { restoringRevisionId },
  };

  return {
    project,
    loadError,
    viewProps: {
      project,
      onBack: () => navigate('/projects'),
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
          wholeBook: {
            phase: wholeBookLoop.phase,
            remaining: wholeBookPlan(project).length,
            onStart: () => void wholeBookLoop.start(wholeBookPlan(project)),
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
        error,
        isConflictActionPending,
        onDraftChange: setDraft,
        onTitleChange: setTitleDraft,
        onLoadLatest: loadLatest,
        onRetryOverwrite: retryOverwrite,
      },
      inspector: {
        error,
        exports,
        inspector,
        instruction,
        jobs,
        projectId,
        latestReview,
        loadedRevisionId: loadedRevision.current,
        proposal,
        providers,
        revisions,
        settingsForm,
        onAcceptProposal: () => void acceptProposal(),
        onExport: (format) => void exportProject(format),
        exportingFormat,
        failedFormat,
        onRetryExport: (format) => void exportProject(format),
        pending: inspectorPending,
        errorForExport: section === 'export' ? error : null,
        onLoadJobs: () => void loadJobs(),
        onRestoreRevision: (revisionId) => void onRestoreRevision(revisionId),
        onRetryJob: (jobId) => void retryJob(jobId),
        onRunProposal: (operation) => void runProposal(operation),
        onStopProposal: () => stopProposal(),
        streamingText,
        onRunReview: () => void runReview(),
        onUpdateSettings: updateProjectSettings,
        setInspector,
        setInstruction,
        setProposal,
        setSettingsForm,
      },
      statusbar: {
        activeDocument,
        loadedRevisionId: loadedRevision.current,
        saveState,
      },
    },
  };
}
