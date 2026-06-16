import { Loader2 } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import type { StudioDocument } from '@/app/types/studio';

import { StudioEditorPane } from './StudioEditorPane';
import { StudioInspector, type SettingsFormState } from './StudioInspector';
import { StudioNavigator } from './StudioNavigator';
import { StudioStatusbar } from './StudioStatusbar';
import { StudioTopbar } from './StudioTopbar';
import { type InspectorTab } from './studioConstants';
import { useActiveDocument } from './hooks/useActiveDocument';
import { useDocumentDraft } from './hooks/useDocumentDraft';
import { useExportDownload } from './hooks/useExportDownload';
import { useStudioActions } from './hooks/useStudioActions';
import { useStudioJobs } from './hooks/useStudioJobs';
import { useStudioProject } from './hooks/useStudioProject';
import { useStudioProposal } from './hooks/useStudioProposal';
import { useStudioSearch } from './hooks/useStudioSearch';

export function StudioPage() {
  const { projectId = '', section = 'manuscript' } = useParams();
  const navigate = useNavigate();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [inspector, setInspector] = useState<InspectorTab>('copilot');
  const [settingsForm, setSettingsForm] = useState<SettingsFormState>({
    title: '',
    description: '',
    provider: 'mock',
  });

  const {
    project,
    setProject,
    session,
    reviews,
    setReviews,
    exports,
    setExports,
    error,
    setError,
  } = useStudioProject(projectId);

  useEffect(() => {
    setActiveId((current) => current ?? project?.documents?.[0]?.id ?? null);
  }, [project]);

  const activeDocument = useActiveDocument(project, section, activeId, setActiveId);

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
  } = useDocumentDraft(activeDocument, projectId, setProject, setError);

  const { jobs, loadJobs } = useStudioJobs(projectId, setError);

  const onProposalAccepted = useCallback(
    (document: StudioDocument) => resetFor(document, 'saved'),
    [resetFor],
  );

  const { proposal, setProposal, instruction, setInstruction, runProposal, acceptProposal } =
    useStudioProposal(
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

  const { exportProject } = useExportDownload(project, projectId, setExports, setError);

  const { createDocument, moveDocument, runReview, updateProjectSettings, retryJob } =
    useStudioActions({
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

  useEffect(() => {
    if (section === 'review') setInspector('review');
    if (section === 'history' || section === 'export') setInspector('history');
    if (section === 'settings') setInspector('settings');
  }, [section]);

  useEffect(() => {
    if (inspector === 'jobs') {
      void loadJobs();
    }
  }, [inspector, loadJobs]);

  useEffect(() => {
    if (inspector === 'settings' && project) {
      setSettingsForm({
        title: project.title,
        description: project.description,
        provider: String(project.settings.provider ?? 'mock'),
      });
    }
  }, [inspector, project]);

  const latestReview = reviews[0] ?? null;

  if (!project) {
    return (
      <main className="studio-loading">
        <Loader2 className="spin" /> Loading Studio
      </main>
    );
  }

  return (
    <main className="studio">
      <StudioTopbar
        project={project}
        session={session}
        onBack={() => navigate('/projects')}
        onReview={() => void runReview()}
        onExport={(format) => void exportProject(format)}
        onSettings={() => navigate(`/projects/${project.id}/settings`)}
      />

      <StudioNavigator
        project={project}
        section={section}
        activeId={activeId}
        search={search}
        isSearching={isSearching}
        searchResults={searchResults}
        onSearchChange={setSearch}
        onSearchSubmit={runSearch}
        onNavigateSection={(nextSection) => navigate(`/projects/${project.id}/${nextSection}`)}
        onSelectDocument={setActiveId}
        onCreateDocument={(kind) => void createDocument(kind)}
        onMoveDocument={(documentId, direction) => void moveDocument(documentId, direction)}
      />

      <StudioEditorPane
        activeDocument={activeDocument}
        draft={draft}
        titleDraft={titleDraft}
        saveState={saveState}
        onDraftChange={setDraft}
        onTitleChange={setTitleDraft}
      />

      <StudioInspector
        error={error}
        exports={exports}
        inspector={inspector}
        instruction={instruction}
        jobs={jobs}
        latestReview={latestReview}
        loadedRevisionId={loadedRevision.current}
        proposal={proposal}
        revisions={revisions}
        settingsForm={settingsForm}
        onAcceptProposal={() => void acceptProposal()}
        onLoadJobs={() => void loadJobs()}
        onRestoreRevision={(revisionId) => void restoreRevision(revisionId)}
        onRetryJob={(jobId) => void retryJob(jobId)}
        onRunProposal={(operation) => void runProposal(operation)}
        onRunReview={() => void runReview()}
        onUpdateSettings={updateProjectSettings}
        setInspector={setInspector}
        setInstruction={setInstruction}
        setProposal={setProposal}
        setSettingsForm={setSettingsForm}
      />

      <StudioStatusbar
        activeDocument={activeDocument}
        loadedRevisionId={loadedRevision.current}
        saveState={saveState}
      />
    </main>
  );
}
