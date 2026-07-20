import { describe, expect, it, vi } from 'vitest';

import type { Project } from '@/app/types/studio';

import { buildStudioNavigatorProps } from './studioPageModelView';

const project: Project = {
  id: 'project-1',
  title: 'Novel',
  description: '',
  settings: {},
  import_hash: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  documents: [],
};

describe('buildStudioNavigatorProps', () => {
  it('keeps navigation state local and adapts actions to the view interface', () => {
    const navigate = vi.fn();
    const createDocument = vi.fn();
    const moveDocument = vi.fn();
    const props = buildStudioNavigatorProps(
      {
        project,
        section: 'outline',
        activeId: null,
        search: 'chapter',
        isSearching: false,
        searchResults: [],
        onSearchChange: vi.fn(),
        onSearchSubmit: vi.fn(),
        onSelectDocument: vi.fn(),
        createDocument,
        moveDocument,
        isCreatingDocument: true,
        isMovingDocument: false,
      },
      navigate,
    );

    props.onNavigateSection('review');
    props.onCreateDocument('chapter');
    props.onMoveDocument('document-1', -1);

    expect(navigate).toHaveBeenCalledWith('/projects/project-1/review');
    expect(createDocument).toHaveBeenCalledWith('chapter');
    expect(moveDocument).toHaveBeenCalledWith('document-1', -1);
    expect(props.isCreatingDocument).toBe(true);
    expect(props.section).toBe('outline');
  });
});
