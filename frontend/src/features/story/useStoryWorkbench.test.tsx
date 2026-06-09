import { act } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { api } from '@/app/api';
import type { WorkspaceJob, WorkspaceStatus } from '@/app/types/story';

import { render, screen, waitFor } from '../../../tests/test-utils';
import { useStoryWorkbench } from './useStoryWorkbench';

function makeWorkspace(
  id = 'salt-ledger',
  chapters = 0,
  jobs: WorkspaceJob[] = [],
): WorkspaceStatus {
  return {
    workspace_id: id,
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
      word_count: 250,
      summary: `Chapter ${index + 1} summary`,
      sidecar: {},
    })),
    latest_review: null,
    exports: [],
    runs: [],
    jobs,
  };
}

function makeJob(
  status: WorkspaceJob['status'] = 'completed',
  overrides: Partial<WorkspaceJob> = {},
): WorkspaceJob {
  return {
    job_id: 'job-1',
    workspace_id: 'salt-ledger',
    operation: 'run',
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
    ...overrides,
    status,
  };
}

function cancellableJobResponse() {
  let resolveJob: (job: WorkspaceJob) => void = () => undefined;
  const promise = (signal?: AbortSignal): Promise<WorkspaceJob> =>
    new Promise((resolve, reject) => {
      resolveJob = resolve;
      signal?.addEventListener(
        'abort',
        () => reject(new Error('Request cancelled.')),
        { once: true },
      );
    });
  return {
    promise,
    resolve: (job: WorkspaceJob = makeJob()) => resolveJob(job),
  };
}

function mockProviders() {
  vi.spyOn(api, 'listProviders').mockResolvedValue({
    default_provider: 'mock',
    providers: [
      {
        provider: 'mock',
        label: 'mock offline demo',
        configured: true,
        is_default: true,
        model: 'deterministic-story-v1',
      },
    ],
  });
}

function Harness({
  onSelectionChange = vi.fn(),
  preferredWorkspaceId,
  preferredJobId,
}: {
  onSelectionChange?: (selection: {
    workspaceId: string | null;
    jobId: string | null;
    view: 'workspace' | 'playback';
    workspace?: WorkspaceStatus | null;
  }) => void;
  preferredWorkspaceId?: string | null;
  preferredJobId?: string | null;
}) {
  const workbench = useStoryWorkbench({
    authorId: 'workspace-123',
    preferredWorkspaceId,
    preferredJobId,
    onSelectionChange,
  });

  return (
    <div>
      <p data-testid="count">{workbench.workspaces.length}</p>
      <p data-testid="active">{workbench.activeWorkspaceId ?? 'none'}</p>
      <p data-testid="job">{workbench.currentJob?.status ?? 'none'}</p>
      <p data-testid="job-label">
        {workbench.currentJob
          ? `${workbench.currentJob.operation} ${workbench.currentJob.status}`
          : 'none'}
      </p>
      <p data-testid="busy">{workbench.isBusy ? 'busy' : 'idle'}</p>
      <p data-testid="error">{workbench.error ?? 'none'}</p>
      <button
        type="button"
        data-testid="create"
        onClick={() =>
          void workbench.createWorkspace({
            title: 'The Salt Ledger',
            genre: 'mystery',
            premise: 'A courier receives a page that names debts before they happen.',
            target_chapters: 3,
          })
        }
      >
        create
      </button>
      <button
        type="button"
        data-testid="run"
        onClick={() =>
          void workbench.runJob('run', { target_chapters: 3 }).catch(() => undefined)
        }
      >
        run
      </button>
      <button
        type="button"
        data-testid="review"
        onClick={() =>
          void workbench.runJob('review').catch(() => undefined)
        }
      >
        review
      </button>
      <button
        type="button"
        data-testid="select-other"
        onClick={() => void workbench.selectWorkspace('moon-index')}
      >
        select other
      </button>
    </div>
  );
}

describe('useStoryWorkbench', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('loads workspaces and selects the first workspace', async () => {
    mockProviders();
    vi.spyOn(api, 'listWorkspaces').mockResolvedValue({
      workspaces: [makeWorkspace()],
    });

    render(<Harness />);
    await act(async () => {
      await Promise.resolve();
    });

    await waitFor(() => expect(screen.getByTestId('count')).toHaveTextContent('1'));
    expect(screen.getByTestId('active')).toHaveTextContent('salt-ledger');
  });

  it('creates a workspace and syncs it into state', async () => {
    mockProviders();
    vi.spyOn(api, 'listWorkspaces').mockResolvedValue({ workspaces: [] });
    vi.spyOn(api, 'createWorkspace').mockResolvedValue(makeWorkspace());

    render(<Harness />);
    await waitFor(() => expect(screen.getByTestId('count')).toHaveTextContent('0'));

    await act(async () => {
      screen.getByTestId('create').click();
    });

    await waitFor(() => expect(screen.getByTestId('active')).toHaveTextContent('salt-ledger'));
    expect(api.createWorkspace).toHaveBeenCalledWith(
      expect.objectContaining({ title: 'The Salt Ledger' }),
    );
  });

  it('runs, polls, and refreshes a workspace job', async () => {
    mockProviders();
    vi.spyOn(api, 'listWorkspaces').mockResolvedValue({
      workspaces: [makeWorkspace()],
    });
    vi.spyOn(api, 'createWorkspaceJob').mockResolvedValue(makeJob('queued'));
    vi.spyOn(api, 'getWorkspaceJob').mockResolvedValue(makeJob());
    vi.spyOn(api, 'getWorkspace').mockResolvedValue(makeWorkspace('salt-ledger', 3));

    render(<Harness />);
    await act(async () => {
      await Promise.resolve();
    });
    await waitFor(() => expect(screen.getByTestId('active')).toHaveTextContent('salt-ledger'));

    await act(async () => {
      screen.getByTestId('run').click();
    });

    await waitFor(() => expect(screen.getByTestId('job')).toHaveTextContent('completed'));
    expect(api.createWorkspaceJob).toHaveBeenCalledWith(
      'salt-ledger',
      expect.objectContaining({ operation: 'run', target_chapters: 3 }),
    );
    expect(api.getWorkspaceJob).toHaveBeenCalledWith(
      'salt-ledger',
      'job-1',
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });

  it('reconciles quick review completion from refreshed workspace status', async () => {
    mockProviders();
    const selectionSpy = vi.fn();
    const queuedReview = makeJob('queued', {
      job_id: 'review-1',
      operation: 'review',
      result: null,
    });
    const completedReview = makeJob('completed', {
      job_id: 'review-1',
      operation: 'review',
      result: {
        result_type: 'review',
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
    });
    const completedWorkspace = makeWorkspace('salt-ledger', 1, [completedReview]);
    vi.spyOn(api, 'listWorkspaces').mockResolvedValue({
      workspaces: [makeWorkspace('salt-ledger', 1)],
    });
    vi.spyOn(api, 'createWorkspaceJob').mockResolvedValue(queuedReview);
    vi.spyOn(api, 'getWorkspaceJob').mockResolvedValue(queuedReview);
    vi.spyOn(api, 'getWorkspace').mockResolvedValue(completedWorkspace);

    render(<Harness onSelectionChange={selectionSpy} />);
    await act(async () => {
      await Promise.resolve();
    });
    await waitFor(() => expect(screen.getByTestId('active')).toHaveTextContent('salt-ledger'));

    await act(async () => {
      screen.getByTestId('review').click();
    });

    await waitFor(() =>
      expect(screen.getByTestId('job-label')).toHaveTextContent('review completed'),
    );
    expect(selectionSpy).toHaveBeenLastCalledWith(
      expect.objectContaining({
        workspaceId: 'salt-ledger',
        jobId: 'review-1',
        view: 'playback',
        workspace: completedWorkspace,
      }),
    );
    expect(selectionSpy).not.toHaveBeenCalledWith(
      expect.objectContaining({
        jobId: 'review-1',
        workspace: undefined,
      }),
    );
    expect(api.getWorkspaceJob).toHaveBeenCalledWith(
      'salt-ledger',
      'review-1',
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
    expect(api.getWorkspace).toHaveBeenCalledWith(
      'salt-ledger',
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });

  it('resumes polling a non-terminal preferred review job from the library', async () => {
    mockProviders();
    const selectionSpy = vi.fn();
    const queuedReview = makeJob('running', {
      job_id: 'review-resume-1',
      operation: 'review',
      result: null,
    });
    const completedReview = makeJob('completed', {
      job_id: 'review-resume-1',
      operation: 'review',
      result: {
        result_type: 'review',
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
    });
    const completedWorkspace = makeWorkspace('salt-ledger', 1, [completedReview]);
    const listWorkspacesSpy = vi.spyOn(api, 'listWorkspaces').mockResolvedValue({
      workspaces: [makeWorkspace('salt-ledger', 1, [queuedReview])],
    });
    vi.spyOn(api, 'getWorkspaceJob').mockResolvedValue(completedReview);
    vi.spyOn(api, 'getWorkspace').mockResolvedValue(completedWorkspace);

    render(
      <Harness
        onSelectionChange={selectionSpy}
        preferredWorkspaceId="salt-ledger"
        preferredJobId="review-resume-1"
      />,
    );

    await waitFor(() => expect(listWorkspacesSpy).toHaveBeenCalled());
    await waitFor(() =>
      expect(screen.getByTestId('job-label')).toHaveTextContent('review completed'),
    );
    expect(api.getWorkspaceJob).toHaveBeenCalledWith(
      'salt-ledger',
      'review-resume-1',
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
    expect(selectionSpy).toHaveBeenLastCalledWith(
      expect.objectContaining({
        workspaceId: 'salt-ledger',
        jobId: 'review-resume-1',
        view: 'playback',
        workspace: completedWorkspace,
      }),
    );
  });

  it('continues polling through a transient workspace refresh failure', async () => {
    mockProviders();
    const queuedReview = makeJob('queued', {
      job_id: 'review-transient-1',
      operation: 'review',
      result: null,
    });
    const completedReview = makeJob('completed', {
      job_id: 'review-transient-1',
      operation: 'review',
      result: {
        result_type: 'review',
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
    });
    const completedWorkspace = makeWorkspace('salt-ledger', 1, [completedReview]);
    vi.spyOn(api, 'listWorkspaces').mockResolvedValue({
      workspaces: [makeWorkspace('salt-ledger', 1)],
    });
    vi.spyOn(api, 'createWorkspaceJob').mockResolvedValue(queuedReview);
    vi.spyOn(api, 'getWorkspaceJob').mockResolvedValue(queuedReview);
    vi.spyOn(api, 'getWorkspace')
      .mockRejectedValueOnce(new Error('Service temporarily unavailable. Start the backend API and retry.'))
      .mockResolvedValue(completedWorkspace);

    render(<Harness />);
    await act(async () => {
      await Promise.resolve();
    });
    await waitFor(() => expect(screen.getByTestId('active')).toHaveTextContent('salt-ledger'));

    await act(async () => {
      screen.getByTestId('review').click();
    });

    await waitFor(() =>
      expect(screen.getByTestId('job-label')).toHaveTextContent('review completed'),
    );
    expect(screen.getByTestId('error')).toHaveTextContent('none');
  });

  it('does not downgrade a terminal polled job with a stale workspace snapshot', async () => {
    mockProviders();
    const queuedRun = makeJob('queued', { job_id: 'run-1' });
    const completedRun = makeJob('completed', { job_id: 'run-1' });
    const staleRunningRun = makeJob('running', { job_id: 'run-1' });
    vi.spyOn(api, 'listWorkspaces').mockResolvedValue({
      workspaces: [makeWorkspace()],
    });
    vi.spyOn(api, 'createWorkspaceJob').mockResolvedValue(queuedRun);
    vi.spyOn(api, 'getWorkspaceJob').mockResolvedValue(completedRun);
    vi.spyOn(api, 'getWorkspace').mockResolvedValue(
      makeWorkspace('salt-ledger', 3, [staleRunningRun]),
    );

    render(<Harness />);
    await act(async () => {
      await Promise.resolve();
    });
    await waitFor(() => expect(screen.getByTestId('active')).toHaveTextContent('salt-ledger'));

    await act(async () => {
      screen.getByTestId('run').click();
    });

    await waitFor(() =>
      expect(screen.getByTestId('job-label')).toHaveTextContent('run completed'),
    );
    expect(screen.getByTestId('busy')).toHaveTextContent('idle');
  });

  it('cancels stale polling when switching workspaces', async () => {
    mockProviders();
    const pendingPoll = cancellableJobResponse();
    vi.spyOn(api, 'listWorkspaces').mockResolvedValue({
      workspaces: [makeWorkspace('salt-ledger'), makeWorkspace('moon-index')],
    });
    vi.spyOn(api, 'createWorkspaceJob').mockResolvedValue(makeJob('queued'));
    vi.spyOn(api, 'getWorkspaceJob').mockImplementation((_, __, options) =>
      pendingPoll.promise(options?.signal ?? undefined),
    );
    vi.spyOn(api, 'getWorkspace').mockResolvedValue(makeWorkspace('moon-index', 1));

    render(<Harness />);
    await act(async () => {
      await Promise.resolve();
    });
    await waitFor(() => expect(screen.getByTestId('active')).toHaveTextContent('salt-ledger'));

    await act(async () => {
      screen.getByTestId('run').click();
    });
    await waitFor(() => expect(screen.getByTestId('job')).toHaveTextContent('queued'));

    await act(async () => {
      screen.getByTestId('select-other').click();
    });

    await waitFor(() => expect(screen.getByTestId('active')).toHaveTextContent('moon-index'));
    expect(screen.getByTestId('job')).toHaveTextContent('none');
    expect(screen.getByTestId('busy')).toHaveTextContent('idle');

    await act(async () => {
      pendingPoll.resolve(makeJob('completed'));
      await Promise.resolve();
    });
    expect(screen.getByTestId('active')).toHaveTextContent('moon-index');
  });

  it('does not let an old poll clear the busy state for a newer job', async () => {
    mockProviders();
    const firstPoll = cancellableJobResponse();
    const secondPoll = cancellableJobResponse();
    const firstJob = makeJob('queued');
    const secondJob = { ...makeJob('queued'), job_id: 'job-2' };
    vi.spyOn(api, 'listWorkspaces').mockResolvedValue({
      workspaces: [makeWorkspace()],
    });
    vi.spyOn(api, 'createWorkspaceJob')
      .mockResolvedValueOnce(firstJob)
      .mockResolvedValueOnce(secondJob);
    vi.spyOn(api, 'getWorkspaceJob')
      .mockImplementationOnce((_, __, options) =>
        firstPoll.promise(options?.signal ?? undefined),
      )
      .mockImplementationOnce((_, __, options) =>
        secondPoll.promise(options?.signal ?? undefined),
      );
    vi.spyOn(api, 'getWorkspace').mockResolvedValue(makeWorkspace('salt-ledger', 3));

    render(<Harness />);
    await act(async () => {
      await Promise.resolve();
    });
    await waitFor(() => expect(screen.getByTestId('active')).toHaveTextContent('salt-ledger'));

    await act(async () => {
      screen.getByTestId('run').click();
    });
    await waitFor(() => expect(screen.getByTestId('job')).toHaveTextContent('queued'));

    await act(async () => {
      screen.getByTestId('run').click();
    });
    await waitFor(() => expect(screen.getByTestId('busy')).toHaveTextContent('busy'));

    await act(async () => {
      firstPoll.resolve(makeJob('completed'));
      await Promise.resolve();
    });
    expect(screen.getByTestId('busy')).toHaveTextContent('busy');

    await act(async () => {
      secondPoll.resolve({ ...secondJob, status: 'completed' });
    });
    await waitFor(() => expect(screen.getByTestId('busy')).toHaveTextContent('idle'));
    expect(screen.getByTestId('job')).toHaveTextContent('completed');
  });
});
