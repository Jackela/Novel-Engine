import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { BookOpen, Clock3, LogOut, Plus } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import { api } from '@/app/api';
import type { Project, Session } from '@/app/types/studio';

export function ProjectLibraryPage() {
  const navigate = useNavigate();
  const [session, setSession] = useState<Session | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [nextSession, response] = await Promise.all([api.session(), api.projects()]);
      setSession(nextSession);
      setProjects(response.projects);
    } catch {
      navigate('/', { replace: true });
    }
  }, [navigate]);

  useEffect(() => {
    void load();
  }, [load]);

  const createProject = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      const project = await api.createProject(title, description);
      navigate(`/projects/${project.id}/manuscript`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to create project.');
    }
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to sign out.');
      return;
    }
    navigate('/');
  };

  return (
    <main className="library">
      <header className="library__header">
        <div className="brand">
          <BookOpen aria-hidden="true" /> Novel Studio
        </div>
        <div className="library__header-actions">
          {session?.kind === 'guest' ? (
            <span className="session-expiry">
              <Clock3 aria-hidden="true" />
              Guest expires{' '}
              {session.expires_at ? new Date(session.expires_at).toLocaleString() : ''}
            </span>
          ) : null}
          <button
            className="icon-command"
            onClick={() => void logout()}
            title="Sign out"
            type="button"
          >
            <LogOut aria-hidden="true" />
          </button>
        </div>
      </header>

      <section className="library__content">
        <div className="library__heading">
          <div>
            <h1>Projects</h1>
            <p>Open a manuscript or start a new novel.</p>
          </div>
        </div>
        <div className="library__grid">
          <form className="project-create" onSubmit={createProject}>
            <div className="project-create__icon">
              <Plus />
            </div>
            <h2>New project</h2>
            <label>
              <span>Title</span>
              <input value={title} onChange={(event) => setTitle(event.target.value)} required />
            </label>
            <label>
              <span>Premise</span>
              <textarea
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                rows={4}
              />
            </label>
            {error ? <p className="form-error">{error}</p> : null}
            <button className="command command--primary" type="submit">
              Create project
            </button>
          </form>
          {projects.map((project) => (
            <button
              className="project-row"
              key={project.id}
              onClick={() => navigate(`/projects/${project.id}/manuscript`)}
              type="button"
            >
              <BookOpen aria-hidden="true" />
              <span>
                <strong>{project.title}</strong>
                <small>{project.description || 'No premise yet'}</small>
              </span>
              <time>{new Date(project.updated_at).toLocaleDateString()}</time>
            </button>
          ))}
        </div>
      </section>
    </main>
  );
}
