import { BookOpen, ChevronLeft } from "lucide-react";
import type { Ref } from "react";

import { productIdentity } from "@/app/productIdentity";
import type { Project } from "@/app/types/studio";

interface StudioTopbarProps {
  project: Project;
  onBack: () => void;
  headingRef?: Ref<HTMLHeadingElement>;
}

export function StudioTopbar({ project, onBack, headingRef }: StudioTopbarProps) {
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
      <h1
        className="studio-topbar__project-title"
        id="studio-project-title"
        ref={headingRef}
        tabIndex={-1}
      >
        {project.title}
      </h1>
      <div className="studio-topbar__spacer" />
    </header>
  );
}
