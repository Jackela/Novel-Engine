import { useState } from "react";
import type { NavigateFunction } from "react-router-dom";

import type { Project } from "@/app/types/studio";

import type { ProjectShellReadAuthority } from "./projectShellReadAuthority";
import { useActiveDocument } from "./useActiveDocument";
import { usePageCurrentDocument } from "./usePageCurrentDocument";

interface PageActiveDocumentInput {
  projectId: string;
  project: Project | null;
  section: string;
  lifecycle: symbol;
  shellReadAuthority: ProjectShellReadAuthority;
  navigate: NavigateFunction;
}

/**
 * The document-selection state domain of the studio page: the Navigator's
 * active document id, the summary it resolves to within the current project
 * and section, and the loaded body behind that summary.
 */
export function usePageActiveDocument({
  projectId,
  project,
  section,
  lifecycle,
  shellReadAuthority,
  navigate,
}: PageActiveDocumentInput) {
  const [activeId, setActiveId] = useState<string | null>(null);
  const activeSummary = useActiveDocument(project, section, activeId);
  const currentDocument = usePageCurrentDocument(
    projectId,
    activeSummary,
    lifecycle,
    shellReadAuthority,
    navigate,
  );
  return {
    activeId,
    setActiveId,
    activeSummary,
    currentDocument,
    activeDocument: currentDocument.document,
  };
}
