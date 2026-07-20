import { act, type FormEvent, type ReactElement } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { Project, Session, StudioDocument } from '@/app/types/studio';

import { StudioInspector } from './StudioInspector';
import { StudioNavigator } from './StudioNavigator';
import { StudioTopbar } from './StudioTopbar';

const mountedRoots: Array<{ container: HTMLDivElement; root: Root }> = [];

function render(element: ReactElement): HTMLDivElement {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => {
    root.render(element);
  });
  mountedRoots.push({ container, root });
  return container;
}

function click(element: Element | null): void {
  if (!(element instanceof HTMLElement)) {
    throw new Error('Expected a clickable element.');
  }
  act(() => {
    element.click();
  });
}

afterEach(() => {
  for (const { container, root } of mountedRoots) {
    act(() => {
      root.unmount();
    });
    container.remove();
  }
  mountedRoots.length = 0;
});

const baseDocument: StudioDocument = {
  id: 'doc-1',
  project_id: 'project-1',
  kind: 'chapter',
  title: 'Opening',
  position: 1,
  current_revision_id: 'revision-abcdefghi',
  content_markdown: '# Opening',
  metadata: {},
  revision_source: 'author',
  word_count: 42,
  created_at: '2026-06-16T00:00:00Z',
  updated_at: '2026-06-16T00:00:00Z',
};

const secondDocument: StudioDocument = {
  ...baseDocument,
  id: 'doc-2',
  title: 'Second',
  position: 2,
  current_revision_id: 'revision-second',
  word_count: 12,
};

const baseProject: Project = {
  id: 'project-1',
  title: 'Clockwork Harbor',
  description: '',
  settings: {},
  import_hash: null,
  created_at: '2026-06-16T00:00:00Z',
  updated_at: '2026-06-16T00:00:00Z',
  documents: [baseDocument, secondDocument],
};

describe('Studio split components', () => {
  it('exposes the inspector tabs and active panel as an associated ARIA tab set', () => {
    const setInspector = vi.fn();
    const container = render(
      <StudioInspector
        error={null}
        inspector="copilot"
        instruction=""
        jobs={[]}
        latestReview={null}
        loadedRevisionId={null}
        proposal={null}
        providers={[]}
        exports={[]}
        revisions={[]}
        settingsForm={{ title: '', description: '', provider: '' }}
        onAcceptProposal={vi.fn()}
        onLoadJobs={vi.fn()}
        onRestoreRevision={vi.fn()}
        onRetryJob={vi.fn()}
        onRunProposal={vi.fn()}
        onRunReview={vi.fn()}
        onUpdateSettings={vi.fn()}
        setInspector={setInspector}
        setInstruction={vi.fn()}
        setProposal={vi.fn()}
        setSettingsForm={vi.fn()}
      />,
    );

    const tablist = container.querySelector('[role="tablist"]');
    const disclosure = container.querySelector('details.studio-inspector__disclosure');
    const tabs = Array.from(container.querySelectorAll('[role="tab"]'));
    const activeTab = tabs.find((tab) => tab.getAttribute('aria-selected') === 'true');
    const panels = Array.from(container.querySelectorAll('[role="tabpanel"]'));
    const activePanel = panels.find((panel) => !panel.hasAttribute('hidden'));

    expect(tablist).not.toBeNull();
    expect(disclosure).not.toBeNull();
    expect(disclosure?.querySelector('summary')?.textContent).toContain('Inspector');
    expect(disclosure?.hasAttribute('open')).toBe(true);
    expect(tabs).toHaveLength(5);
    expect(panels).toHaveLength(5);
    expect(activeTab?.textContent).toContain('Copilot');
    expect(tabs.filter((tab) => tab.getAttribute('aria-selected') === 'false')).toHaveLength(4);
    expect(activeTab?.getAttribute('aria-controls')).toBe(activePanel?.id);
    expect(activePanel?.getAttribute('aria-labelledby')).toBe(activeTab?.id);
    expect(
      tabs.every((tab) => panels.some((panel) => panel.id === tab.getAttribute('aria-controls'))),
    ).toBe(true);
    expect(panels.filter((panel) => panel.hasAttribute('hidden'))).toHaveLength(4);

    click(tabs.find((tab) => tab.textContent?.includes('Review')) ?? null);
    expect(setInspector).toHaveBeenCalledWith('review');
  });

  it('supports APG tablist keyboard navigation and keeps one tab in the tab sequence', () => {
    const setInspector = vi.fn();
    const container = render(
      <StudioInspector
        error={null}
        inspector="copilot"
        instruction=""
        jobs={[]}
        latestReview={null}
        loadedRevisionId={null}
        proposal={null}
        providers={[]}
        exports={[]}
        revisions={[]}
        settingsForm={{ title: '', description: '', provider: '' }}
        onAcceptProposal={vi.fn()}
        onLoadJobs={vi.fn()}
        onRestoreRevision={vi.fn()}
        onRetryJob={vi.fn()}
        onRunProposal={vi.fn()}
        onRunReview={vi.fn()}
        onUpdateSettings={vi.fn()}
        setInspector={setInspector}
        setInstruction={vi.fn()}
        setProposal={vi.fn()}
        setSettingsForm={vi.fn()}
      />,
    );

    const tabs = Array.from(container.querySelectorAll<HTMLButtonElement>('[role="tab"]'));
    expect(tabs.filter((tab) => tab.tabIndex === 0)).toHaveLength(1);

    act(() => {
      tabs[0].dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    });
    expect(setInspector).toHaveBeenCalledWith('review');

    act(() => {
      tabs[0].dispatchEvent(new KeyboardEvent('keydown', { key: 'End', bubbles: true }));
    });
    expect(setInspector).toHaveBeenCalledWith('jobs');

    act(() => {
      tabs[2].dispatchEvent(new KeyboardEvent('keydown', { key: 'Home', bubbles: true }));
    });
    expect(setInspector).toHaveBeenCalledWith('copilot');
  });

  it('does not expose an unselected tablist while the settings route is active', () => {
    const container = render(
      <StudioInspector
        error={null}
        inspector="settings"
        instruction=""
        jobs={[]}
        latestReview={null}
        loadedRevisionId={null}
        proposal={null}
        providers={[]}
        exports={[]}
        revisions={[]}
        settingsForm={{ title: '', description: '', provider: '' }}
        onAcceptProposal={vi.fn()}
        onLoadJobs={vi.fn()}
        onRestoreRevision={vi.fn()}
        onRetryJob={vi.fn()}
        onRunProposal={vi.fn()}
        onRunReview={vi.fn()}
        onUpdateSettings={vi.fn()}
        setInspector={vi.fn()}
        setInstruction={vi.fn()}
        setProposal={vi.fn()}
        setSettingsForm={vi.fn()}
      />,
    );

    const tabs = Array.from(container.querySelectorAll('[role="tab"]'));

    expect(container.querySelector('[role="tablist"]')).toBeNull();
    expect(tabs).toHaveLength(0);
    expect(container.querySelector('form.inspector-content')).not.toBeNull();
  });

  it('keeps topbar navigation focused on returning to the project library', () => {
    const back = vi.fn();
    const guestSession: Session = {
      session_id: 'session-1',
      kind: 'guest',
      owner_id: null,
      expires_at: '2026-06-16T12:00:00Z',
    };

    const container = render(
      <StudioTopbar project={baseProject} session={guestSession} onBack={back} />,
    );

    expect(container.textContent).toContain('Clockwork Harbor');
    click(container.querySelector('button[aria-label="Back to projects"]'));
    expect(back).toHaveBeenCalledTimes(1);
    expect(container.querySelector('.export-menu')).toBeNull();
  });

  it('keeps navigation callbacks scoped to section, search, and document actions', () => {
    const callbacks = {
      searchChange: vi.fn(),
      searchSubmit: vi.fn((event: FormEvent) => event.preventDefault()),
      navigateSection: vi.fn(),
      selectDocument: vi.fn(),
      createDocument: vi.fn(),
      moveDocument: vi.fn(),
    };

    const container = render(
      <StudioNavigator
        project={baseProject}
        section="manuscript"
        activeId="doc-1"
        search="harbor"
        isSearching={false}
        searchResults={[{ document_id: 'doc-1', title: 'Opening', excerpt: 'Harbor' }]}
        onSearchChange={callbacks.searchChange}
        onSearchSubmit={callbacks.searchSubmit}
        onNavigateSection={callbacks.navigateSection}
        onSelectDocument={callbacks.selectDocument}
        onCreateDocument={callbacks.createDocument}
        onMoveDocument={callbacks.moveDocument}
      />,
    );

    expect(container.querySelector('summary.studio-nav__summary')).not.toBeNull();
    expect(container.querySelector('summary')?.textContent).toContain('Project navigation');
    expect(container.querySelector('summary')?.hasAttribute('aria-label')).toBe(false);
    expect(container.querySelector('button[aria-label="Add Manuscript"]')).not.toBeNull();
    expect(container.querySelector('button[aria-label="Move Second down"]')).not.toBeNull();

    click(Array.from(container.querySelectorAll('.section-nav button'))[1]);
    click(container.querySelector('.search-results button'));
    click(container.querySelector('.document-group header button'));
    click(container.querySelector('.document-order button:last-child'));
    act(() => {
      container.querySelector('form')?.dispatchEvent(new Event('submit', { bubbles: true }));
    });

    expect(callbacks.navigateSection).toHaveBeenCalledWith('outline');
    expect(callbacks.selectDocument).toHaveBeenCalledWith('doc-1');
    expect(callbacks.createDocument).toHaveBeenCalledWith('chapter');
    expect(callbacks.moveDocument).toHaveBeenCalledWith('doc-1', 1);
    expect(callbacks.searchSubmit).toHaveBeenCalledTimes(1);
  });
});
