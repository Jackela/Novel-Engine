import { act } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { api } from '@/app/api';
import type { StudioJob } from '@/app/types/studio';

import { wholeBookPlan } from './wholeBookPlan';
import {
  baseProject,
  deferred,
  firstChapter,
  proposalJobFor,
  renderLoopHook,
  secondChapter,
  traceApiCalls,
} from './useWholeBookLoop.test-harness';

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

describe('useWholeBookLoop interruption', () => {
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

  it('#390 halts the loop when the page unmounts: no further chapter is drafted or accepted', async () => {
    const events: string[] = [];
    const firstDraft = deferred<StudioJob>();
    traceApiCalls(events);
    vi.mocked(api.proposal).mockImplementationOnce(async (_projectId, documentId) => {
      events.push(`proposal:${documentId}`);
      return firstDraft.promise;
    });

    const harness = renderLoopHook(baseProject);
    let finished: Promise<void> = Promise.resolve();

    await act(async () => {
      finished = harness.result().hook.start(wholeBookPlan(baseProject));
      await vi.waitFor(() =>
        expect(events.filter((event) => event.startsWith('proposal:'))).toHaveLength(1),
      );
      // Unmount while the first draft is still in flight.
      harness.unmount();
      firstDraft.resolve(proposalJobFor(firstChapter.id));
      await finished;
    });

    // The unmounted run never accepts the in-flight draft and never starts
    // the next chapter.
    expect(events.some((event) => event.startsWith('accept:'))).toBe(false);
    expect(events.filter((event) => event.startsWith('proposal:'))).toEqual(['proposal:one']);
    expect(vi.mocked(api.acceptProposal)).not.toHaveBeenCalled();
  });
});
