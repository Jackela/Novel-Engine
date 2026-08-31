import { BookOpen, ChevronLeft } from "lucide-react";

import { productIdentity } from "@/app/productIdentity";
import type { Project } from "@/app/types/studio";

interface StudioTopbarProps {
  project: Project;
  onBack: () => void;
}

export function StudioTopbar({ project, onBack }: StudioTopbarProps) {
  return (
    <header className="studio-topbar">
      <button
        aria-label="Back to projects"
        className="ui-command--icon"
        onClick={onBack}
        type="button"
      >
        <ChevronLeft />
      </button>
      <div className="ui-brand">
        <BookOpen /> {productIdentity.name}
      </div>
      <div className="studio-topbar__project-title">{project.title}</div>
      <div className="studio-topbar__spacer" />
    </header>
  );
}
