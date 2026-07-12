import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, describe, expect, it } from 'vitest';

import type { Project, StudioDocument } from '@/app/types/studio';

import { useActiveDocument } from './useActiveDocument';

interface HookArgs {
  readonly project: Project | null;
  readonly section: string;
  readonly activeId: string | null;
}

const chapter: StudioDocument = {
  id: 'chapter-1',
  project_id: 'project-1',
  kind: 'chapter',
  title: 'Chapter One',
  position: 0,
  current_revision_id: 'revision-1',
  content_markdown: 'Chapter content',
  metadata: {},
  revision_source: 'manual',
  word_count: 2,
  created_at: '2026-06-20T00:00:00Z',
  updated_at: '2026-06-20T00:00:00Z',
};
const outline: StudioDocument = {
  ...chapter,
  id: 'outline-1',
  kind: 'outline',
  title: 'Story Outline',
  position: 1,
};
const character: StudioDocument = {
  ...chapter,
  id: 'character-1',
  kind: 'character',
  title: 'Ada',
  position: 2,
};
const project: Project = {
  id: 'project-1',
  title: 'Clockwork Harbor',
  description: '',
  settings: {},
  import_hash: null,
  created_at: '2026-06-20T00:00:00Z',
  updated_at: '2026-06-20T00:00:00Z',
  documents: [chapter, outline, character],
};
const mountedRoots: Array<{ container: HTMLDivElement; root: Root }> = [];

afterEach(() => {
  for (const { container, root } of mountedRoots) {
    act(() => {
      root.unmount();
    });
    container.remove();
  }
  mountedRoots.length = 0;
});

function renderActiveDocument(initialArgs: HookArgs): {
  readonly result: () => StudioDocument | null;
  readonly rerender: (args: HookArgs) => void;
} {
  let args = initialArgs;
  let current: StudioDocument | null = null;

  function Wrapper(): null {
    current = useActiveDocument(args.project, args.section, args.activeId);
    return null;
  }

  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  mountedRoots.push({ container, root });

  const render = () => root.render(<Wrapper />);
  act(render);

  return {
    result: () => current,
    rerender: (nextArgs) => {
      args = nextArgs;
      act(render);
    },
  };
}

describe('useActiveDocument', () => {
  it('returns the selected document when it belongs to the current section', () => {
    // Given / When
    const hook = renderActiveDocument({
      project,
      section: 'manuscript',
      activeId: chapter.id,
    });

    // Then
    expect(hook.result()).toEqual(chapter);
  });

  it('returns the first document matching a scoped section', () => {
    // Given
    const hook = renderActiveDocument({
      project,
      section: 'manuscript',
      activeId: chapter.id,
    });

    // When
    hook.rerender({ project, section: 'characters', activeId: chapter.id });

    // Then
    expect(hook.result()).toEqual(character);
  });

  it('returns null when a scoped section has no matching document', () => {
    // Given / When
    const hook = renderActiveDocument({
      project: { ...project, documents: [chapter] },
      section: 'world',
      activeId: chapter.id,
    });

    // Then
    expect(hook.result()).toBeNull();
  });
});
