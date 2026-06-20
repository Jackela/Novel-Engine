import { act, useState } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { api } from '@/app/api';
import type { Project, StudioDocument, StudioJob } from '@/app/types/studio';
import type { InspectorTab } from '@/features/studio/studioConstants';

import { useStudioProposal } from './useStudioProposal';

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

type HookResult = ReturnType<typeof useStudioProposal>;

interface HarnessSnapshot {
  readonly hook: HookResult;
  readonly project: Project | null;
  readonly inspector: InspectorTab;
  readonly error: string | null;
  readonly accepted: StudioDocument | null;
}

const mountedRoots: Array<{ container: HTMLDivElement; root: Root }> = [];

const firstDocument: StudioDocument = {
  id: 'document-1',
  project_id: 'project-1',
  kind: 'chapter',
  title: 'Chapter One',
  position: 0,
  current_revision_id: 'revision-1',
  content_markdown: 'Original scene',
  metadata: {},
  revision_source: 'manual',
  word_count: 2,
  created_at: '2026-06-18T00:00:00Z',
  updated_at: '2026-06-18T00:00:00Z',
};

const secondDocument: StudioDocument = {
  ...firstDocument,
  id: 'document-2',
  title: 'Chapter Two',
  current_revision_id: 'revision-2',
};

const baseProject: Project = {
  id: 'project-1',
  title: 'Clockwork Harbor',
  description: 'A harbor of brass clocks.',
  settings: {},
  import_hash: null,
  created_at: '2026-06-18T00:00:00Z',
  updated_at: '2026-06-18T00:00:00Z',
  documents: [firstDocument, secondDocument],
};

const proposalJob: StudioJob = {
  id: 'job-1',
  project_id: baseProject.id,
  document_id: firstDocument.id,
  kind: 'proposal',
  operation: 'continue',
  status: 'completed',
  provider: 'mock',
  model: 'studio-copilot-v1',
  request: {},
  result: { proposal_markdown: 'A generated continuation.' },
  error: null,
  retry_of_job_id: null,
  events: [],
  created_at: '2026-06-18T00:01:00Z',
  updated_at: '2026-06-18T00:01:00Z',
};

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

function renderProposalHook(): {
  readonly result: () => HarnessSnapshot;
  readonly rerender: (document: StudioDocument) => void;
  readonly loadJobs: ReturnType<typeof vi.fn<() => void>>;
} {
  let activeDocument = firstDocument;
  let current: HarnessSnapshot | undefined;
  const loadJobs = vi.fn<() => void>();

  function Wrapper(): null {
    const [project, setProject] = useState<Project | null>(baseProject);
    const [inspector, setInspector] = useState<InspectorTab>('history');
    const [error, setError] = useState<string | null>('previous error');
    const [accepted, setAccepted] = useState<StudioDocument | null>(null);
    const hook = useStudioProposal(
      baseProject.id,
      activeDocument,
      project,
      setProject,
      setInspector,
      setError,
      loadJobs,
      (document) => setAccepted(document),
    );
    current = { hook, project, inspector, error, accepted };
    return null;
  }

  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  mountedRoots.push({ container, root });

  const render = () => root.render(<Wrapper />);
  act(render);

  return {
    result: () => {
      if (current === undefined) {
        throw new Error('Expected hook result after render.');
      }
      return current;
    },
    rerender: (document) => {
      activeDocument = document;
      act(render);
    },
    loadJobs,
  };
}

describe('useStudioProposal', () => {
  it('publishes a generated proposal with the mock provider fallback', async () => {
    // Given
    vi.mocked(api.proposal).mockResolvedValue(proposalJob);
    const harness = renderProposalHook();
    act(() => {
      harness.result().hook.setInstruction('Expand the scene');
    });

    // When
    await act(async () => {
      await harness.result().hook.runProposal('continue');
    });

    // Then
    expect(api.proposal).toHaveBeenCalledWith(
      baseProject.id,
      firstDocument.id,
      'continue',
      'Expand the scene',
      'mock',
    );
    expect(harness.result().hook.proposal).toEqual(proposalJob);
    expect(harness.result().inspector).toBe('copilot');
    expect(harness.result().error).toBeNull();
  });

  it('refreshes project state and the accepted document after accepting a proposal', async () => {
    // Given
    const acceptedDocument = {
      ...firstDocument,
      current_revision_id: 'revision-accepted',
      content_markdown: 'Accepted continuation',
    };
    const refreshedProject = {
      ...baseProject,
      documents: [acceptedDocument, secondDocument],
    };
    vi.mocked(api.acceptProposal).mockResolvedValue(proposalJob);
    vi.mocked(api.project).mockResolvedValue(refreshedProject);
    const harness = renderProposalHook();
    act(() => {
      harness.result().hook.setProposal(proposalJob);
    });

    // When
    await act(async () => {
      await harness.result().hook.acceptProposal();
    });

    // Then
    expect(harness.result().project).toEqual(refreshedProject);
    expect(harness.result().accepted).toEqual(acceptedDocument);
    expect(harness.result().hook.proposal).toBeNull();
    expect(harness.loadJobs).toHaveBeenCalledTimes(1);
  });

  it('clears a stale proposal when the active document changes', () => {
    // Given
    const harness = renderProposalHook();
    act(() => {
      harness.result().hook.setProposal(proposalJob);
    });
    expect(harness.result().hook.proposal).toEqual(proposalJob);

    // When
    harness.rerender(secondDocument);

    // Then
    expect(harness.result().hook.proposal).toBeNull();
  });
});
