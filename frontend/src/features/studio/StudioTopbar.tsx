import { BookOpen, ChevronLeft, Clock3 } from 'lucide-react';

import type { Project, Session } from '@/app/types/studio';

interface StudioTopbarProps {
  project: Project;
  session: Session | null;
  onBack: () => void;
}

export function StudioTopbar({ project, session, onBack }: StudioTopbarProps) {
  return (
    <header className="studio-topbar">
      <button aria-label="Back to projects" className="icon-command" onClick={onBack} type="button">
        <ChevronLeft />
      </button>
      <div className="brand">
        <BookOpen /> Novel Studio
      </div>
      <div className="studio-project-title">{project.title}</div>
      <div className="studio-topbar__spacer" />
      {session?.kind === 'guest' ? (
        <span className="session-expiry">
          <Clock3 />
          {session.expires_at ? new Date(session.expires_at).toLocaleTimeString() : 'Guest'}
        </span>
      ) : null}
    </header>
  );
}
