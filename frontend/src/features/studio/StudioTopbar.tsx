import { BookOpen, ChevronLeft, Clock3, Download, Settings2, ShieldCheck } from 'lucide-react';

import type { ExportFormat, Project, Session } from '@/app/types/studio';

interface StudioTopbarProps {
  project: Project;
  session: Session | null;
  onBack: () => void;
  onReview: () => void;
  onExport: (format: ExportFormat) => void;
  onSettings: () => void;
}

export function StudioTopbar({
  project,
  session,
  onBack,
  onReview,
  onExport,
  onSettings,
}: StudioTopbarProps) {
  return (
    <header className="studio-topbar">
      <button className="icon-command" onClick={onBack} title="Projects" type="button">
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
      <button className="command" onClick={onReview} type="button">
        <ShieldCheck /> Review
      </button>
      <details className="export-menu">
        <summary aria-haspopup="menu" className="command command--primary" role="button">
          <Download /> Export
        </summary>
        <div className="export-menu__items">
          {(['markdown', 'docx', 'epub'] as ExportFormat[]).map((format) => (
            <button key={format} onClick={() => onExport(format)} type="button">
              {format.toUpperCase()}
            </button>
          ))}
        </div>
      </details>
      <button className="icon-command" onClick={onSettings} title="Project settings" type="button">
        <Settings2 />
      </button>
    </header>
  );
}
