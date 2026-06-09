import { MemoryRouter, useLocation } from 'react-router-dom';
import { act } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { SessionState } from '@/app/types/auth';
import type { WorkspaceJob, WorkspaceStatus } from '@/app/types/story';
import { useAuth } from '@/features/auth/useAuth';
import { fireEvent, render, screen } from '../../../tests/test-utils';

import { StoryWorkbenchPage } from './StoryWorkbenchPage';
import type { UseStoryWorkbenchResult } from './useStoryWorkbench';
import { useStoryWorkbench } from './useStoryWorkbench';

vi.mock('@/features/auth/useAuth', () => ({
  useAuth: vi.fn(),
}));

vi.mock('./useStoryWorkbench', () => ({
  useStoryWorkbench: vi.fn(),
}));

const session: SessionState = {
  id: 'guest-1',
  kind: 'guest',
  workspaceId: 'guest-workspace',
  activeWorkspace: {
    workspaceId: 'guest-workspace',
    workspaceKind: 'guest',
    label: 'Guest workspace',
    persistence: 'ephemeral',
    summary: 'Guest workspace summary',
  },
};

function makeWorkspace(chapters = 0): WorkspaceStatus {
  return {
    workspace_id: 'salt-ledger',
    story: {
      title: 'The Salt Ledger',
      genre: 'mystery',
      premise: 'A courier receives a page that names debts before they happen.',
      target_chapters: 3,
      tone: 'sharp',
      themes: [],
    },
    chapters: Array.from({ length: chapters }, (_, index) => ({
      chapter_number: index + 1,
      filename: `chapter-${String(index + 1).padStart(3, '0')}.md`,
      artifact_id: `chapter-${String(index + 1).padStart(3, '0')}.md`,
      relative_path: `manuscript/chapters/chapter-${String(index + 1).padStart(3, '0')}.md`,
      word_count: 240,
      summary: `Chapter ${index + 1} summary`,
      sidecar: {},
    })),
    latest_review: {
      story_title: 'The Salt Ledger',
      checked_at: '2026-01-01T00:00:00Z',
      blockers: [],
      warnings: [
        {
          severity: 'warning',
          code: 'thin_chapter',
          message: 'Chapter is brief.',
          location: 'chapter-001',
          suggestion: 'Consider expanding it.',
          details: {},
        },
      ],
      suggestions: [
        {
          severity: 'suggestion',
          code: 'editorial_next_pass',
          message: 'Run a prose pass.',
          location: 'manuscript',
          suggestion: 'Tighten rhythm.',
          details: {},
        },
      ],
      style_notes: [],
      export_blocked: false,
    },
    exports: [],
    runs: [
      {
        run_id: 'run-1',
        artifact_id: 'run-1',
        relative_path: 'artifacts/runs/run-1',
        events: [],
        artifact_count: 3,
        last_event: {
          timestamp: '2026-01-01T00:00:00Z',
          operation: 'run',
          status: 'completed',
          details: {},
        },
      },
    ],
    jobs: [],
  };
}

function makeJob(): WorkspaceJob {
  return {
    job_id: 'job-1',
    workspace_id: 'salt-ledger',
    operation: 'run',
    status: 'completed',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:01Z',
    provider: 'mock',
    result: {
      result_type: 'run',
      run_id: 'run-1',
      review: {
        story_title: 'The Salt Ledger',
        checked_at: '2026-01-01T00:00:01Z',
        blockers: [],
        warnings: [],
        suggestions: [],
        style_notes: [],
        export_blocked: false,
      },
    },
    error: null,
    failure_artifact: null,
    events: [],
  };
}

function LocationProbe() {
  const location = useLocation();
  return <p data-testid="location-search">{location.search || 'none'}</p>;
}

function renderWorkbench(workbench: Partial<UseStoryWorkbenchResult> = {}) {
  const createWorkspace = vi.fn().mockResolvedValue(makeWorkspace());
  const runJob = vi.fn().mockResolvedValue(makeJob());
  const auth = {
    session,
    sessions: [session],
    activeSessionId: session.id,
    isLoading: false,
    signInAsGuest: vi.fn(),
    signIn: vi.fn(),
    signOut: vi.fn(),
    switchSession: vi.fn(),
    updateSessionSelection: vi.fn(),
  };
  vi.mocked(useAuth).mockReturnValue(auth);
  vi.mocked(useStoryWorkbench).mockReturnValue({
    workspaces: [],
    activeWorkspaceId: null,
    workspace: null,
    currentJob: null,
    providers: [
      {
        provider: 'mock',
        label: 'mock offline demo',
        configured: true,
        is_default: true,
        model: 'deterministic-story-v1',
      },
      {
        provider: 'dashscope',
        label: 'DashScope',
        configured: false,
        is_default: false,
        model: 'qwen3.5-flash',
      },
    ],
    defaultProvider: 'mock',
    isLoading: false,
    isBusy: false,
    error: null,
    refreshLibrary: vi.fn(),
    selectWorkspace: vi.fn(),
    createWorkspace,
    runJob,
    ...workbench,
  });

  render(
    <MemoryRouter
      future={{
        v7_relativeSplatPath: true,
        v7_startTransition: true,
      }}
    >
      <StoryWorkbenchPage />
      <LocationProbe />
    </MemoryRouter>,
  );

  return { auth, createWorkspace, runJob };
}

describe('StoryWorkbenchPage', () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  it('renders the workspace entry flow', () => {
    renderWorkbench();

    expect(screen.getByTestId('studio-workbench-page')).toHaveTextContent(
      'Novel Engine / Local Workspace',
    );
    expect(screen.getByTestId('studio-create-draft')).toHaveTextContent('Create workspace');
  });

  it('does not render workbench content or call hooks before a session exists', () => {
    vi.mocked(useStoryWorkbench).mockClear();
    vi.mocked(useAuth).mockReturnValue({
      session: null,
      sessions: [],
      activeSessionId: null,
      isLoading: false,
      signInAsGuest: vi.fn(),
      signIn: vi.fn(),
      signOut: vi.fn(),
      switchSession: vi.fn(),
      updateSessionSelection: vi.fn(),
    });

    render(
      <MemoryRouter
        future={{
          v7_relativeSplatPath: true,
          v7_startTransition: true,
        }}
      >
        <StoryWorkbenchPage />
      </MemoryRouter>,
    );

    expect(screen.queryByTestId('studio-workbench-page')).not.toBeInTheDocument();
    expect(useStoryWorkbench).not.toHaveBeenCalled();
  });

  it('creates a workspace from the form', async () => {
    const { createWorkspace } = renderWorkbench();

    fireEvent.input(screen.getByTestId('studio-title-input'), {
      target: { value: 'The Salt Ledger' },
    });
    fireEvent.input(screen.getByTestId('studio-premise-input'), {
      target: {
        value: 'A courier receives a page that names debts before they happen.',
      },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId('studio-create-draft'));
      await Promise.resolve();
    });

    expect(createWorkspace).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'The Salt Ledger',
        target_chapters: 3,
      }),
    );
  });

  it('shows workspace status and triggers workspace jobs', async () => {
    const { runJob } = renderWorkbench({
      workspaces: [makeWorkspace(3)],
      activeWorkspaceId: 'salt-ledger',
      workspace: makeWorkspace(3),
      currentJob: makeJob(),
    });

    expect(screen.getByTestId('studio-active-title')).toHaveTextContent('The Salt Ledger');
    expect(screen.getByTestId('studio-chapter-list')).toHaveTextContent('chapter-001.md');
    expect(screen.getByTestId('studio-review-panel')).toHaveTextContent('thin_chapter');
    expect(screen.getByTestId('studio-workflow-state')).toHaveTextContent('run completed');

    await act(async () => {
      fireEvent.click(screen.getByTestId('studio-export'));
      await Promise.resolve();
    });
    expect(runJob).toHaveBeenCalledWith('export', { provider: 'mock' });

    await act(async () => {
      fireEvent.click(screen.getByTestId('studio-run-workspace'));
      await Promise.resolve();
    });
    expect(runJob).toHaveBeenCalledWith('run', { target_chapters: 3, provider: 'mock' });
  });

  it('lets the workbench hook own job URL selection after job actions', async () => {
    const { runJob } = renderWorkbench({
      workspaces: [makeWorkspace(3)],
      activeWorkspaceId: 'salt-ledger',
      workspace: makeWorkspace(3),
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('studio-review'));
      await Promise.resolve();
    });

    expect(runJob).toHaveBeenCalledWith('review', { provider: 'mock' });
    expect(screen.getByTestId('location-search')).toHaveTextContent('none');
  });

  it('persists selected workspace metadata from workbench selection changes', () => {
    const selectedWorkspace = makeWorkspace(2);
    const { auth } = renderWorkbench({
      workspaces: [selectedWorkspace],
      activeWorkspaceId: 'salt-ledger',
      workspace: selectedWorkspace,
    });
    const options = vi.mocked(useStoryWorkbench).mock.calls[0]?.[0];
    if (typeof options === 'string' || !options?.onSelectionChange) {
      throw new Error('Expected object options with onSelectionChange.');
    }

    act(() => {
      options.onSelectionChange?.({
        workspaceId: 'salt-ledger',
        jobId: null,
        view: 'workspace',
        workspace: selectedWorkspace,
      });
    });

    expect(auth.updateSessionSelection).toHaveBeenCalledWith({
      lastWorkspaceId: 'salt-ledger',
      lastJobId: null,
      lastView: 'workspace',
      activeWorkspace: {
        workspaceId: 'salt-ledger',
        workspaceKind: 'guest',
        label: 'The Salt Ledger',
        persistence: 'ephemeral',
        summary: 'salt-ledger / 2 chapters',
      },
    });
  });

  it('passes the selected provider to workspace jobs', async () => {
    const { runJob } = renderWorkbench({
      workspaces: [makeWorkspace(3)],
      activeWorkspaceId: 'salt-ledger',
      workspace: makeWorkspace(3),
      providers: [
        {
          provider: 'mock',
          label: 'mock offline demo',
          configured: true,
          is_default: false,
          model: 'deterministic-story-v1',
        },
        {
          provider: 'dashscope',
          label: 'DashScope',
          configured: true,
          is_default: true,
          model: 'qwen3.5-flash',
        },
      ],
    });

    fireEvent.change(screen.getByTestId('studio-provider-select'), {
      target: { value: 'dashscope' },
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('studio-run-workspace'));
      await Promise.resolve();
    });

    expect(runJob).toHaveBeenCalledWith('run', {
      target_chapters: 3,
      provider: 'dashscope',
    });
  });
});
