import { useEffect, useMemo } from 'react';

import type { DocumentKind, Project, StudioDocument } from '@/app/types/studio';

export function useActiveDocument(
  project: Project | null,
  section: string,
  activeId: string | null,
  setActiveId: (id: string | null) => void,
): StudioDocument | null {
  const activeDocument = useMemo(() => {
    const document = project?.documents?.find((item) => item.id === activeId) ?? null;
    if (!document) return null;
    if (section === 'outline' && document.kind !== 'outline') return null;
    if (section === 'characters' && document.kind !== 'character') return null;
    if (section === 'world' && document.kind !== 'world') return null;
    return document;
  }, [activeId, project, section]);

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
  }, [project, section, activeId, setActiveId]);

  return activeDocument;
}
