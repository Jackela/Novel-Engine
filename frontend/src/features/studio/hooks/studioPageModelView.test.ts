import { describe, expect, it, vi } from 'vitest';

import { project as projectFixture } from '@/test/factories';

import { buildStudioNavigatorProps } from './studioPageModelView';

const project = projectFixture({ title: 'Novel' });

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
