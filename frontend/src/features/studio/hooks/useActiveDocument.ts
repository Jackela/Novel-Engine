import { useMemo } from 'react';

import type { DocumentKind, Project, StudioDocument } from '@/app/types/studio';

function documentKindForSection(section: string): DocumentKind | null {
  switch (section) {
    case 'outline':
      return 'outline';
    case 'characters':
      return 'character';
    case 'world':
      return 'world';
    default:
      return null;
  }
}

export function useActiveDocument(
  project: Project | null,
  section: string,
  activeId: string | null,
): StudioDocument | null {
  return useMemo(() => {
    const documents = project?.documents ?? [];
    const activeDocument = documents.find((document) => document.id === activeId) ?? null;
    const sectionKind = documentKindForSection(section);

    if (sectionKind === null) {
      return activeDocument ?? documents[0] ?? null;
    }

    if (activeDocument?.kind === sectionKind) {
      return activeDocument;
    }

    return documents.find((document) => document.kind === sectionKind) ?? null;
  }, [activeId, project, section]);
}
