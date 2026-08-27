import { act, useState } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { api } from '@/app/api';
import type { Project, StudioDocument, StudioJob } from '@/app/types/studio';

import { wholeBookPlan } from './wholeBookPlan';
import { useWholeBookLoop } from './useWholeBookLoop';

vi.mock('@/app/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/app/api')>();

  return {
    ...actual,
    api: {
      ...actual.api,
      proposal: vi.fn<typeof actual.api.proposal>(),
      acceptProposal: vi.fn<typeof actual.api.acceptProposal>(),
      project: vi.fn<typeof actual.api.project>(),
    },
  };
});

type HookResult = ReturnType<typeof useWholeBookLoop>;

interface HarnessSnapshot {
  readonly hook: HookResult;
  readonly project: Project | null;
  readonly accepted: StudioDocument[];
}

interface Deferred<T> {
  readonly promise: Promise<T>;
  resolve: (value: T) => void;
}

const mountedRoots: Array<{ container: HTMLDivElement; root: Root }> = [];

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolveValue) => {
    resolve = resolveValue;
  });
  return { promise, resolve };
}

function chapter(id: string, overrides: Partial<StudioDocument> = {}): StudioDocument {
  return {
    id,
    project_id: 'project-1',
    kind: 'chapter',
    title: `Titled ${id}`,
    position: 0,
    volume_id: 'volume-1',
    current_revision_id: `revision-${id}`,
    content_markdown: '',
    metadata: {},
    revision_source: 'author',
    word_count: 0,
    created_at: '2026-08-27T00:00:00Z',
    updated_at: '2026-08-27T00:00:00Z',
    ...overrides,
  };
}

function projectWith(documents: StudioDocument[]): Project {
  return {
    id: 'project-1',
    title: 'Clockwork Harbor',
    description: '',
    settings: {},
    import_hash: null,
    created_at: '2026-08-27T00:00:00Z',
    updated_at: '2026-08-27T00:00:00Z',
    documents,
  };
}

const firstChapter = chapter('one', { title: 'Chapter One', position: 0 });
const secondChapter = chapter('two', { title: 'Chapter Two', position: 1 });
const baseProject = projectWith([firstChapter, secondChapter]);

function proposalJobFor(documentId: string): StudioJob {
  return {
    id: `job-${documentId}`,
    project_id: baseProject.id,
    document_id: documentId,
    kind: 'proposal',
    operation: 'generate',
    status: 'completed',
    provider: 'mock',
    model: 'studio-copilot-v1',
    request: {},
    result: { proposal_markdown: `Generated prose for ${documentId}.` },
    error: null,
    retry_of_job_id: null,
    events: [],
    created_at: '2026-08-27T00:01:00Z',
    updated_at: '2026-08-27T00:01:00Z',
  };
}

afterEach(() => {
  for (const { container, root } of mountedRoots) {
    act(() => {
      root.unmount();
    });
    container.remove();
  }
  mountedRoots.length = 0;
  vi.resetAllMocks();
});

function renderLoopHook(initialProject: Project): {
  readonly result: () => HarnessSnapshot;
} {
  let current: HarnessSnapshot | undefined;

  function Wrapper(): null {
    const [project, setProject] = useState<Project | null>(initialProject);
    const [accepted, setAccepted] = useState<StudioDocument[]>([]);
    const hook = useWholeBookLoop({
      projectId: initialProject.id,
      provider: 'mock',
      setProject,
      loadJobs: vi.fn(),
      onAccepted: (document) => setAccepted((previous) => [...previous, document]),
    });
    current = { hook, project, accepted };
    return null;
  }

  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  mountedRoots.push({ container, root });
  act(() => {
    root.render(<Wrapper />);
  });

  return {
    result: () => {
      if (current === undefined) throw new Error('Expected hook result after render.');
      return current;
    },
  };
}

/** Release every step immediately while recording the exact call sequence. */
function traceApiCalls(events: string[], refreshedProject: Project = baseProject): void {
  vi.mocked(api.proposal).mockImplementation(async (_projectId, documentId) => {
    events.push(`proposal:${documentId}`);
    return proposalJobFor(documentId);
  });
  vi.mocked(api.acceptProposal).mockImplementation(async (_projectId, jobId) => {
    events.push(`accept:${jobId}`);
    return proposalJobFor(jobId.replace('job-', ''));
  });
  vi.mocked(api.project).mockImplementation(async () => {
    events.push('refresh');
    return refreshedProject;
  });
}

describe('useWholeBookLoop (#318)', () => {
  it('drafts and auto-accepts every planned chapter in reading order', async () => {
    const events: string[] = [];
    traceApiCalls(events);
    const harness = renderLoopHook(baseProject);

    await act(async () => {
      await harness.result().hook.start(wholeBookPlan(baseProject));
    });

    expect(events).toEqual([
      'proposal:one',
      'accept:job-one',
      'refresh',
      'proposal:two',
      'accept:job-two',
      'refresh',
    ]);
    expect(harness.result().hook.phase).toEqual({
      kind: 'done',
      generated: 2,
      stoppedEarly: false,
    });
    expect(harness.result().accepted.map((document) => document.id)).toEqual(['one', 'two']);
    expect(vi.mocked(api.proposal).mock.calls[0]?.[2]).toBe('generate');
  });

  it('abandons an in-flight draft once stopped and never starts the next chapter', async () => {
    const events: string[] = [];
    const firstDraft = deferred<StudioJob>();
    const secondDraft = deferred<StudioJob>();
    traceApiCalls(events);
    // The deferred stubs must record their own initiation: a vitest
    // mockReturnValueOnce shadows the traceApiCalls implementation entirely,
    // and this fixture pins the call sequence through the shared events log.
    vi.mocked(api.proposal)
      .mockImplementationOnce(async (_projectId, documentId) => {
        events.push(`proposal:${documentId}`);
        return firstDraft.promise;
      })
      .mockImplementationOnce(async (_projectId, documentId) => {
        events.push(`proposal:${documentId}`);
        return secondDraft.promise;
      });

    const harness = renderLoopHook(baseProject);
    let finished: Promise<void> = Promise.resolve();

    await act(async () => {
      finished = harness.result().hook.start(wholeBookPlan(baseProject));
      firstDraft.resolve(proposalJobFor(firstChapter.id));
      await vi.waitFor(() =>
        expect(events.filter((event) => event.startsWith('proposal:'))).toHaveLength(2),
      );
      // Stop lands while the second draft request is still unresolved.
      harness.result().hook.stop();
      secondDraft.resolve(proposalJobFor(secondChapter.id));
      await finished;
    });

    expect(events.filter((event) => event === 'accept:job-two')).toEqual([]);
    expect(events.filter((event) => event === 'refresh')).toHaveLength(1);
    expect(harness.result().hook.phase).toEqual({
      kind: 'done',
      generated: 1,
      stoppedEarly: true,
    });
    expect(harness.result().accepted.map((document) => document.id)).toEqual(['one']);
  });

  it('surfaces a proposal failure with the failing chapter identified', async () => {
    const events: string[] = [];
    traceApiCalls(events);
    vi.mocked(api.proposal).mockRejectedValue(new Error('Provider exploded.'));
    const harness = renderLoopHook(baseProject);

    await act(async () => {
      await harness.result().hook.start(wholeBookPlan(baseProject));
    });

    expect(harness.result().hook.phase).toEqual({
      kind: 'failed',
      generated: 0,
      failedChapterTitle: 'Chapter One',
      message: 'Provider exploded.',
    });
    expect(events.some((event) => event.startsWith('accept:'))).toBe(false);
  });

  it('stops after an accept failure and keeps earlier chapters intact', async () => {
    const events: string[] = [];
    traceApiCalls(events);
    // Same shadowing rule as above: the value-level stubs also record their
    // initiation. The failing accept stays unrecorded on purpose — it never
    // lands — while its rejection is what the loop must surface.
    vi.mocked(api.proposal)
      .mockImplementationOnce(async (_projectId, documentId) => {
        events.push(`proposal:${documentId}`);
        return proposalJobFor(firstChapter.id);
      })
      .mockImplementationOnce(async (_projectId, documentId) => {
        events.push(`proposal:${documentId}`);
        return proposalJobFor(secondChapter.id);
      })
      .mockRejectedValue(new Error('Provider exploded again.'));
    vi.mocked(api.acceptProposal)
      .mockImplementationOnce(async (_projectId, jobId) => {
        events.push(`accept:${jobId}`);
        return proposalJobFor(firstChapter.id);
      })
      .mockRejectedValue(new Error('Accept rejected by the server.'));
    const harness = renderLoopHook(baseProject);

    await act(async () => {
      await harness.result().hook.start(wholeBookPlan(baseProject));
    });

    expect(events.slice(0, 3)).toEqual(['proposal:one', 'accept:job-one', 'refresh']);
    expect(events.some((event) => event === 'accept:job-two')).toBe(false);
    expect(harness.result().hook.phase).toEqual({
      kind: 'failed',
      generated: 1,
      failedChapterTitle: 'Chapter Two',
      message: 'Accept rejected by the server.',
    });
    expect(harness.result().accepted.map((document) => document.id)).toEqual(['one']);
  });

  it('ignores a start request while the loop is already running', async () => {
    const gate = deferred<StudioJob>();
    traceApiCalls([]);
    vi.mocked(api.proposal).mockImplementation((_projectId, documentId) =>
      documentId === firstChapter.id ? gate.promise : Promise.resolve(proposalJobFor(documentId)),
    );
    const harness = renderLoopHook(baseProject);
    let ignoredStart: Promise<void> = Promise.resolve();
    let realStart: Promise<void> = Promise.resolve();

    act(() => {
      realStart = harness.result().hook.start(wholeBookPlan(baseProject));
      ignoredStart = harness.result().hook.start(wholeBookPlan(baseProject));
    });
    expect(harness.result().hook.phase).toEqual({ kind: 'running', current: 1, total: 2 });

    await act(async () => {
      gate.resolve(proposalJobFor(firstChapter.id));
      await realStart;
      await ignoredStart;
    });

    expect(vi.mocked(api.proposal)).toHaveBeenCalledTimes(2);
    expect(vi.mocked(api.acceptProposal)).toHaveBeenCalledTimes(2);
    expect(harness.result().hook.phase).toEqual({
      kind: 'done',
      generated: 2,
      stoppedEarly: false,
    });
  });

  it('reports idle before any run starts', () => {
    const harness = renderLoopHook(baseProject);
    expect(harness.result().hook.phase).toEqual({ kind: 'idle' });
  });
});
