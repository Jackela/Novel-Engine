import {
  BookOpen,
  Bot,
  ArrowDown,
  ArrowUp,
  Check,
  ChevronLeft,
  Clock3,
  Download,
  FileText,
  Globe2,
  History,
  Loader2,
  Plus,
  RotateCcw,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  Users,
  X,
} from 'lucide-react';
import {
  useCallback,
  useEffect,
  lazy,
  useMemo,
  useRef,
  useState,
  Suspense,
  type FormEvent,
} from 'react';
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
  StudioDocument,
  StudioExport,
  StudioJob,
} from '@/app/types/studio';

const MarkdownEditor = lazy(async () => {
  const module = await import('./MarkdownEditor');
  return { default: module.MarkdownEditor };
});

const GROUPS: Array<{
  kind: DocumentKind;
  label: string;
  icon: typeof FileText;
}> = [
  { kind: 'chapter', label: 'Manuscript', icon: BookOpen },
  { kind: 'outline', label: 'Outline', icon: FileText },
  { kind: 'character', label: 'Characters', icon: Users },
  { kind: 'world', label: 'World', icon: Globe2 },
  { kind: 'note', label: 'Notes', icon: FileText },
];

type InspectorTab = 'copilot' | 'review' | 'history' | 'settings';

const SECTIONS = [
  ['manuscript', 'Manuscript'],
  ['outline', 'Outline'],
  ['characters', 'Characters'],
  ['world', 'World'],
  ['review', 'Review'],
  ['history', 'History'],
  ['export', 'Export'],
  ['settings', 'Settings'],
] as const;

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
  const [search, setSearch] = useState('');
  const [searchResults, setSearchResults] = useState<
    Array<{ document_id: string; title: string; excerpt: string }>
  >([]);
  const loadedRevision = useRef<string | null>(null);
  const saveTimer = useRef<number | null>(null);

  const activeDocument = useMemo(
    () => project?.documents?.find((document) => document.id === activeId) ?? null,
    [activeId, project],
  );

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
    if (!activeDocument) return;
    loadedRevision.current = activeDocument.current_revision_id;
    setDraft(activeDocument.content_markdown);
    setSaveState('idle');
    setProposal(null);
    void api.revisions(projectId, activeDocument.id).then((response) => {
      setRevisions(response.revisions);
    });
  }, [activeDocument?.id]);

  useEffect(() => {
    if (!activeDocument) return;
    if (draft === activeDocument.content_markdown) {
      setSaveState('idle');
      return;
    }
    setSaveState('saving');
    if (saveTimer.current) window.clearTimeout(saveTimer.current);
    saveTimer.current = window.setTimeout(async () => {
      try {
        const saved = await api.saveDocument(projectId, activeDocument.id, {
          content_markdown: draft,
          base_revision_id: loadedRevision.current ?? activeDocument.current_revision_id,
        });
        loadedRevision.current = saved.current_revision_id;
        setProject((current) => current ? {
          ...current,
          documents: current.documents?.map((document) =>
            document.id === saved.id ? saved : document
          ),
        } : current);
        setSaveState('saved');
        void api.revisions(projectId, activeDocument.id).then((response) => {
          setRevisions(response.revisions);
        });
      } catch (reason) {
        setSaveState(reason instanceof HttpError && reason.status === 409 ? 'conflict' : 'error');
        setError(reason instanceof Error ? reason.message : 'Unable to save.');
      }
    }, 1500);
    return () => {
      if (saveTimer.current) window.clearTimeout(saveTimer.current);
    };
  }, [activeDocument, draft, projectId]);

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
      setProject((current) => current ? {
        ...current,
        documents: [...(current.documents ?? []), document],
      } : current);
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
      const response = await api.reorderDocuments(project.id, ordered.map((item) => item.id));
      setProject((current) => current ? { ...current, documents: response.documents } : current);
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
    const response = await api.search(projectId, search);
    setSearchResults(response.results);
  };

  const runProposal = async (operation: 'continue' | 'rewrite') => {
    if (!activeDocument) return;
    setError(null);
    try {
      const nextProposal = await api.proposal(
        projectId,
        activeDocument.id,
        operation,
        instruction,
        'mock',
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
      }
      setProposal(null);
      setSaveState('saved');
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
    try {
      const item = await api.createExport(projectId, format);
      setExports((current) => [item, ...current]);
      window.location.assign(item.download_url);
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
      setProject((current) => current ? {
        ...current,
        documents: current.documents?.map((document) =>
          document.id === restored.id ? restored : document
        ),
      } : current);
      const response = await api.revisions(projectId, activeDocument.id);
      setRevisions(response.revisions);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to restore revision.');
    }
  };

  const latestReview = reviews[0] ?? null;

  if (!project) {
    return <main className="studio-loading"><Loader2 className="spin" /> Loading Studio</main>;
  }

  return (
    <main className="studio">
      <header className="studio-topbar">
        <button className="icon-command" onClick={() => navigate('/projects')} title="Projects">
          <ChevronLeft />
        </button>
        <div className="brand"><BookOpen /> Novel Studio</div>
        <div className="studio-project-title">{project.title}</div>
        <div className="studio-topbar__spacer" />
        {session?.kind === 'guest' ? (
          <span className="session-expiry">
            <Clock3 />
            {session.expires_at ? new Date(session.expires_at).toLocaleTimeString() : 'Guest'}
          </span>
        ) : null}
        <button className="command" onClick={() => void runReview()} type="button">
          <ShieldCheck /> Review
        </button>
        <details className="export-menu">
          <summary aria-haspopup="menu" className="command command--primary" role="button">
            <Download /> Export
          </summary>
          <div className="export-menu__items">
            {(['markdown', 'docx', 'epub'] as ExportFormat[]).map((format) => (
              <button key={format} onClick={() => void exportProject(format)} type="button">
                {format.toUpperCase()}
              </button>
            ))}
          </div>
        </details>
        <button
          className="icon-command"
          onClick={() => navigate(`/projects/${project.id}/settings`)}
          title="Project settings"
          type="button"
        ><Settings2 /></button>
      </header>

      <aside className="studio-nav">
        <nav className="section-nav" aria-label="Project sections">
          {SECTIONS.map(([path, label]) => (
            <button
              className={section === path ? 'active' : ''}
              key={path}
              onClick={() => navigate(`/projects/${project.id}/${path}`)}
              type="button"
            >
              {label}
            </button>
          ))}
        </nav>
        <form className="studio-search" onSubmit={runSearch}>
          <Search />
          <input
            aria-label="Search project"
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search documents"
            value={search}
          />
        </form>
        {searchResults.length ? (
          <div className="search-results">
            {searchResults.map((result) => (
              <button key={result.document_id} onClick={() => setActiveId(result.document_id)} type="button">
                <strong>{result.title}</strong>
                <span>{result.excerpt}</span>
              </button>
            ))}
          </div>
        ) : null}
        <div className="document-tree">
          {GROUPS.map(({ kind, label, icon: Icon }) => {
            const documents = project.documents?.filter((document) => document.kind === kind) ?? [];
            return (
              <section className="document-group" key={kind}>
                <header>
                  <span><Icon /> {label}</span>
                  <button onClick={() => void createDocument(kind)} title={`Add ${label}`} type="button">
                    <Plus />
                  </button>
                </header>
                {documents.map((document, index) => (
                  <div className="document-row-wrap" key={document.id}>
                    <button
                      className={document.id === activeId ? 'document-row document-row--active' : 'document-row'}
                      onClick={() => setActiveId(document.id)}
                      type="button"
                    >
                      <FileText />
                      <span>{document.title}</span>
                    </button>
                    <span className="document-order">
                      <button
                        disabled={index === 0}
                        onClick={() => void moveDocument(document.id, -1)}
                        title="Move up"
                        type="button"
                      ><ArrowUp /></button>
                      <button
                        disabled={index === documents.length - 1}
                        onClick={() => void moveDocument(document.id, 1)}
                        title="Move down"
                        type="button"
                      ><ArrowDown /></button>
                    </span>
                  </div>
                ))}
              </section>
            );
          })}
        </div>
      </aside>

      <section className="studio-editor">
        {activeDocument ? (
          <>
            <header className="editor-header">
              <div>
                <input
                  aria-label="Document title"
                  className="editor-title"
                  value={activeDocument.title}
                  readOnly
                />
                <span className={`save-state save-state--${saveState}`}>
                  {saveState === 'saving' ? <Loader2 className="spin" /> : <Check />}
                  {saveState === 'idle' ? 'saved' : saveState}
                </span>
              </div>
              <span>{activeDocument.word_count} words</span>
            </header>
            <div className="editor-toolbar"><span>Markdown</span></div>
            <Suspense fallback={<div className="editor-loading">Loading editor...</div>}>
              <MarkdownEditor value={draft} onChange={setDraft} />
            </Suspense>
          </>
        ) : (
          <div className="empty-editor">Create a document to begin writing.</div>
        )}
      </section>

      <aside className="studio-inspector">
        <nav className="inspector-tabs">
          <button
            className={inspector === 'copilot' ? 'active' : ''}
            onClick={() => setInspector('copilot')}
            type="button"
          >
            <Bot /> Copilot
          </button>
          <button
            className={inspector === 'review' ? 'active' : ''}
            onClick={() => setInspector('review')}
            type="button"
          >
            <ShieldCheck /> Review
          </button>
          <button
            className={inspector === 'history' ? 'active' : ''}
            onClick={() => setInspector('history')}
            type="button"
          >
            <History /> History
          </button>
        </nav>

        {error ? <div className="inspector-error">{error}</div> : null}

        {inspector === 'copilot' ? (
          <div className="inspector-content">
            <h2>AI proposal</h2>
            <p>Copilot never changes the manuscript until you accept a proposal.</p>
            <textarea
              onChange={(event) => setInstruction(event.target.value)}
              placeholder="Describe the change or direction..."
              rows={5}
              value={instruction}
            />
            <div className="inspector-actions">
              <button className="command" onClick={() => void runProposal('rewrite')} type="button">
                <Sparkles /> Rewrite
              </button>
              <button className="command" onClick={() => void runProposal('continue')} type="button">
                Continue
              </button>
            </div>
            {proposal?.result.proposal_markdown ? (
              <section className="proposal">
                <header><strong>Proposed Markdown</strong><span>Preview only</span></header>
                <pre>{proposal.result.proposal_markdown}</pre>
                <div className="inspector-actions">
                  <button className="command command--primary" onClick={() => void acceptProposal()} type="button">
                    <Check /> Accept
                  </button>
                  <button className="command" onClick={() => setProposal(null)} type="button">
                    <X /> Reject
                  </button>
                </div>
              </section>
            ) : null}
          </div>
        ) : null}

        {inspector === 'review' ? (
          <div className="inspector-content">
            <header className="inspector-heading">
              <div><h2>Review findings</h2><p>Snapshot-bound and non-mutating.</p></div>
              <button className="icon-command" onClick={() => void runReview()} title="Run review" type="button">
                <RotateCcw />
              </button>
            </header>
            {latestReview?.issues.length ? latestReview.issues.map((issue) => (
              <article className={`review-issue review-issue--${issue.severity}`} key={issue.id}>
                <header><strong>{issue.code.replace(/_/g, ' ')}</strong><span>{issue.severity}</span></header>
                <p>{issue.message}</p>
                <small>{issue.suggestion}</small>
              </article>
            )) : <p className="empty-panel">No review findings. Run a review when ready.</p>}
          </div>
        ) : null}

        {inspector === 'history' ? (
          <div className="inspector-content">
            <h2>Revision history</h2>
            <p>Restoring creates a new revision and preserves the chain.</p>
            <div className="revision-list">
              {revisions.map((revision) => (
                <article key={revision.id}>
                  <div>
                    <strong>{revision.source}</strong>
                    <time>{new Date(revision.created_at).toLocaleString()}</time>
                    <small>{revision.word_count} words · {revision.id.slice(0, 8)}</small>
                  </div>
                  {revision.id !== loadedRevision.current ? (
                    <button
                      className="icon-command"
                      onClick={() => void restoreRevision(revision.id)}
                      title="Restore revision"
                      type="button"
                    >
                      <RotateCcw />
                    </button>
                  ) : <span className="current-revision">Current</span>}
                </article>
              ))}
            </div>
            {exports.length ? (
              <>
                <h2>Recent exports</h2>
                {exports.slice(0, 4).map((item) => (
                  <a className="export-row" href={item.download_url} key={item.id}>
                    <Download />
                    <span>{item.format.toUpperCase()} · {Math.ceil(item.size_bytes / 1024)} KB</span>
                  </a>
                ))}
              </>
            ) : null}
          </div>
        ) : null}

        {inspector === 'settings' ? (
          <div className="inspector-content">
            <h2>Project settings</h2>
            <dl className="settings-list">
              <div><dt>Title</dt><dd>{project.title}</dd></div>
              <div><dt>Provider</dt><dd>{String(project.settings.provider ?? 'mock')}</dd></div>
              <div><dt>Storage</dt><dd>SQLite</dd></div>
              <div><dt>Document syntax</dt><dd>Markdown</dd></div>
            </dl>
          </div>
        ) : null}
      </aside>

      <footer className="studio-statusbar">
        <span><Check /> {saveState === 'saving' ? 'Saving' : saveState === 'conflict' ? 'Conflict' : 'Saved'}</span>
        <span>Revision {loadedRevision.current?.slice(0, 8) ?? 'none'}</span>
        <span className="studio-statusbar__spacer" />
        <span>{activeDocument?.word_count ?? 0} words</span>
        <span>Novel Studio {__APP_VERSION__}</span>
      </footer>
    </main>
  );
}
