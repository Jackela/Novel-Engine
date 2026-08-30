import { BookOpen, ChevronLeft } from "lucide-react";

import type { Project } from "@/app/types/studio";

interface StudioTopbarProps {
  project: Project;
  onBack: () => void;
}

export function StudioTopbar({ project, onBack }: StudioTopbarProps) {
  return (
    <header className="studio-topbar">
      <button aria-label="Back to projects" className="icon-command" onClick={onBack} type="button">
        <ChevronLeft />
      </button>
      <div className="brand">
        <BookOpen /> Novel Engine
      </div>
      <div className="studio-project-title">{project.title}</div>
      <div className="studio-topbar__spacer" />
    </header>
  );
}
