import { Loader2 } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { api, HttpError } from '@/app/api';
import type {
  DocumentKind,
  ExportFormat,
  Project,
  Review,
  Revision,
  SaveState,
  Session,
  StudioExport,
  StudioJob,
} from '@/app/types/studio';

import { StudioEditorPane } from './StudioEditorPane';
import { StudioInspector, type SettingsFormState } from './StudioInspector';
import { StudioNavigator } from './StudioNavigator';
import { StudioStatusbar } from './StudioStatusbar';
import { StudioTopbar } from './StudioTopbar';
import { GROUPS, type InspectorTab } from './studioConstants';

export function StudioPage() {
  const { projectId = '', section = 'manuscript' } = useParams();
  const navigate = useNavigate();
  const [session, setSession] = useState<Session | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const [saveState, setSaveState] = useState<SaveState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [inspector, setInspector] = useState<InspectorTab>('copilot');
  const [revisions, setRevisions] = useState<Revision[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [exports, setExports] = useState<StudioExport[]>([]);
  const [proposal, setProposal] = useState<StudioJob | null>(null);
  const [instruction, setInstruction] = useState('');
  const [titleDraft, setTitleDraft] = useState('');
  const [settingsForm, setSettingsForm] = useState<SettingsFormState>({
    title: '',
    description: '',
    provider: 'mock',
  });
  const [jobs, setJobs] = useState<StudioJob[]>([]);
  const [search, setSearch] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<
    Array<{ document_id: string; title: string; excerpt: string }>
  >([]);
  const loadedRevision = useRef<string | null>(null);
  const saveTimer = useRef<number | null>(null);
  const draftRef = useRef({ draft, titleDraft, activeDocument: null as typeof activeDocument });

  const activeDocument = useMemo(() => {
    const document = project?.documents?.find((item) => item.id === activeId) ?? null;
    if (!document) return null;
    if (section === 'outline' && document.kind !== 'outline') return null;
    if (section === 'characters' && document.kind !== 'character') return null;
    if (section === 'world' && document.kind !== 'world') return null;
    return document;
  }, [activeId, project, section]);

  useEffect(() => {
    draftRef.current = { draft, titleDraft, activeDocument };
  }, [draft, titleDraft, activeDocument]);

  const loadProject = useCallback(async () => {
    try {
      const [nextSession, nextProject, reviewResponse, exportResponse] = await Promise.all([
        api.session(),
        api.project(projectId),
        api.reviews(projectId),
        api.exports(projectId),
      ]);
      setSession(nextSession);
      setProject(nextProject);
      setReviews(reviewResponse.reviews);
      setExports(exportResponse.exports);
      setActiveId((current) => current ?? nextProject.documents?.[0]?.id ?? null);
    } catch {
      navigate('/', { replace: true });
    }
  }, [navigate, projectId]);

  useEffect(() => {
    void loadProject();
  }, [loadProject]);

  useEffect(() => {
    if (section === 'review') setInspector('review');
    if (section === 'history' || section === 'export') setInspector('history');
    if (section === 'settings') setInspector('settings');
  }, [section]);

  useEffect(() => {
    if (!search.trim()) {
      setSearchResults([]);
    }
  }, [search]);

  useEffect(() => {
    if (!project) return;
    const kind: DocumentKind | null =
      section === 'outline' || section === 'characters' || section === 'world'
        ? section === 'characters'
          ? 'character'
          : section
        : null;
    if (!kind) return;
    const currentDocument = project.documents?.find((document) => document.id === activeId);
    if (currentDocument?.kind === kind) return;
    const first = project.documents?.find((document) => document.kind === kind);
    setActiveId(first?.id ?? null);
  }, [project, section, activeId]);

  useEffect(() => {
    // Only react to the active document identity changing, not to every field
    // update, to avoid resetting the editor while the user is typing.
    if (!activeDocument) return;
    loadedRevision.current = activeDocument.current_revision_id;
    setDraft(activeDocument.content_markdown);
    setTitleDraft(activeDocument.title);
    setSaveState('idle');
    setProposal(null);
    void api
      .revisions(projectId, activeDocument.id)
      .then((response) => {
        setRevisions(response.revisions);
      })
      .catch(setError);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeDocument?.id]);

  useEffect(() => {
    if (!activeDocument) return;
    const unchanged =
      draft === activeDocument.content_markdown && titleDraft === activeDocument.title;
    if (unchanged) {
      setSaveState('idle');
      return;
    }
    setSaveState('saving');
    if (saveTimer.current) window.clearTimeout(saveTimer.current);
    saveTimer.current = window.setTimeout(async () => {
      const {
        draft: currentDraft,
        titleDraft: currentTitle,
        activeDocument: currentDocument,
      } = draftRef.current;
      if (!currentDocument) return;
      try {
        const saved = await api.saveDocument(projectId, currentDocument.id, {
          content_markdown: currentDraft,
          base_revision_id: loadedRevision.current ?? currentDocument.current_revision_id,
          title: currentTitle,
        });
        loadedRevision.current = saved.current_revision_id;
        setProject((current) =>
          current
            ? {
                ...current,
                documents: current.documents?.map((document) =>
                  document.id === saved.id ? saved : document,
                ),
              }
            : current,
        );
        setTitleDraft(saved.title);
        setSaveState('saved');
        void api
          .revisions(projectId, currentDocument.id)
          .then((response) => {
            setRevisions(response.revisions);
          })
          .catch(setError);
      } catch (reason) {
        setSaveState(reason instanceof HttpError && reason.status === 409 ? 'conflict' : 'error');
        setError(reason instanceof Error ? reason.message : 'Unable to save.');
      }
    }, 1500);
    return () => {
      if (saveTimer.current) window.clearTimeout(saveTimer.current);
    };
  }, [draft, titleDraft, activeDocument, projectId]);

  const createDocument = async (kind: DocumentKind) => {
    if (!project) return;
    const count = project.documents?.filter((document) => document.kind === kind).length ?? 0;
    const label = GROUPS.find((group) => group.kind === kind)?.label ?? 'Document';
    try {
      const document = await api.createDocument(project.id, {
        kind,
        title: kind === 'chapter' ? `Chapter ${count + 1}` : `${label} ${count + 1}`,
        content_markdown: kind === 'chapter' ? `# Chapter ${count + 1}\n\n` : '',
      });
      setProject((current) =>
        current
          ? {
              ...current,
              documents: [...(current.documents ?? []), document],
            }
          : current,
      );
      setActiveId(document.id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to create document.');
    }
  };

  const moveDocument = async (documentId: string, direction: -1 | 1) => {
    if (!project?.documents) return;
    const ordered = [...project.documents].sort((a, b) => a.position - b.position);
    const index = ordered.findIndex((document) => document.id === documentId);
    const target = index + direction;
    if (index < 0 || target < 0 || target >= ordered.length) return;
    const currentItem = ordered[index];
    const targetItem = ordered[target];
    if (!currentItem || !targetItem) return;
    ordered[index] = targetItem;
    ordered[target] = currentItem;
    try {
      const response = await api.reorderDocuments(
        project.id,
        ordered.map((item) => item.id),
      );
      setProject((current) => (current ? { ...current, documents: response.documents } : current));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to reorder documents.');
    }
  };

  const runSearch = async (event: FormEvent) => {
    event.preventDefault();
    if (!search.trim()) {
      setSearchResults([]);
      return;
    }
    setIsSearching(true);
    try {
      const response = await api.search(projectId, search);
      setSearchResults(response.results);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Search failed.');
    } finally {
      setIsSearching(false);
    }
  };

  const runProposal = async (operation: 'continue' | 'rewrite') => {
    if (!activeDocument || !project) return;
    setError(null);
    try {
      const nextProposal = await api.proposal(
        projectId,
        activeDocument.id,
        operation,
        instruction,
        String(project.settings.provider ?? 'mock'),
      );
      setProposal(nextProposal);
      setInspector('copilot');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to create proposal.');
    }
  };

  const acceptProposal = async () => {
    if (!proposal || !activeDocument) return;
    try {
      await api.acceptProposal(projectId, proposal.id);
      const refreshed = await api.project(projectId);
      setProject(refreshed);
      const refreshedDocument = refreshed.documents?.find((item) => item.id === activeDocument.id);
      if (refreshedDocument) {
        loadedRevision.current = refreshedDocument.current_revision_id;
        setDraft(refreshedDocument.content_markdown);
        setTitleDraft(refreshedDocument.title);
      }
      const response = await api.revisions(projectId, activeDocument.id);
      setRevisions(response.revisions);
      setProposal(null);
      setSaveState('saved');
      void loadJobs();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to accept proposal.');
    }
  };

  const runReview = async () => {
    try {
      const review = await api.createReview(projectId);
      setReviews((current) => [review, ...current]);
      setInspector('review');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to run review.');
    }
  };

  const exportProject = async (format: ExportFormat) => {
    if (!project) return;
    try {
      const item = await api.createExport(projectId, format);
      setExports((current) => [item, ...current]);
      const response = await fetch(item.download_url, { credentials: 'include' });
      if (!response.ok) {
        throw new Error(`Export download failed: ${response.status} ${response.statusText}`);
      }
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      const extension = format === 'markdown' ? 'md' : format;
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = `${project.title}.${extension}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(blobUrl), 100);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to export project.');
    }
  };

  const restoreRevision = async (revisionId: string) => {
    if (!activeDocument) return;
    try {
      const restored = await api.restoreRevision(
        projectId,
        activeDocument.id,
        revisionId,
        loadedRevision.current ?? activeDocument.current_revision_id,
      );
      loadedRevision.current = restored.current_revision_id;
      setDraft(restored.content_markdown);
      setTitleDraft(restored.title);
      setProject((current) =>
        current
          ? {
              ...current,
              documents: current.documents?.map((document) =>
                document.id === restored.id ? restored : document,
              ),
            }
          : current,
      );
      const response = await api.revisions(projectId, activeDocument.id);
      setRevisions(response.revisions);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to restore revision.');
    }
  };

  const loadJobs = useCallback(async () => {
    try {
      const response = await api.jobs(projectId);
      setJobs(response.jobs);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to load jobs.');
    }
  }, [projectId]);

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

  const updateProjectSettings = async (event: FormEvent) => {
    event.preventDefault();
    if (!project) return;
    try {
      const updated = await api.updateProject(project.id, {
        title: settingsForm.title,
        description: settingsForm.description,
        settings: { ...project.settings, provider: settingsForm.provider },
      });
      setProject(updated);
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to update project.');
    }
  };

  const retryJob = async (jobId: string) => {
    try {
      await api.retryJob(projectId, jobId);
      void loadJobs();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to retry job.');
    }
  };

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
