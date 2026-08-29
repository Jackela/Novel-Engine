import { act, useRef, useState } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, vi } from 'vitest';

import { api } from '@/app/api';
import type { Project, StudioDocument, StudioJob } from '@/app/types/studio';

import { useWholeBookLoop } from './useWholeBookLoop';

export type HookResult = ReturnType<typeof useWholeBookLoop>;

export interface HarnessSnapshot {
  readonly hook: HookResult;
  readonly project: Project | null;
  readonly accepted: StudioDocument[];
}

export interface Deferred<T> {
  readonly promise: Promise<T>;
  resolve: (value: T) => void;
}

const mountedRoots: Array<{ container: HTMLDivElement; root: Root }> = [];

export function deferred<T>(): Deferred<T> {
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

export const firstChapter = chapter('one', { title: 'Chapter One', position: 0 });
export const secondChapter = chapter('two', { title: 'Chapter Two', position: 1 });
export const baseProject = projectWith([firstChapter, secondChapter]);

export function proposalJobFor(documentId: string): StudioJob {
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

export function renderLoopHook(initialProject: Project): {
  readonly result: () => HarnessSnapshot;
  readonly unmount: () => void;
} {
  let current: HarnessSnapshot | undefined;

  function Wrapper(): null {
    const [project, setProject] = useState<Project | null>(initialProject);
    // Accepted documents are recorded in a ref: tests only observe them
    // through snapshots, so the extra re-render would be pure overhead.
    const accepted = useRef<StudioDocument[]>([]);
    const hook = useWholeBookLoop({
      projectId: initialProject.id,
      provider: 'mock',
      setProject,
      loadJobs: vi.fn(),
      onAccepted: (document) => {
        accepted.current = [...accepted.current, document];
      },
    });
    current = { hook, project, accepted: accepted.current };
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
    // Unmount now and keep afterEach from unmounting the same root twice.
    unmount: () => {
      const index = mountedRoots.findIndex((entry) => entry.root === root);
      if (index >= 0) mountedRoots.splice(index, 1);
      act(() => {
        root.unmount();
      });
      container.remove();
    },
  };
}

/** Release every step immediately while recording the exact call sequence. */
export function traceApiCalls(events: string[], refreshedProject: Project = baseProject): void {
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
