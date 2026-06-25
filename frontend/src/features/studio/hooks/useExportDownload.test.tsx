import { act, useState } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { api } from '@/app/api';
import type { Project, StudioExport } from '@/app/types/studio';

import { useExportDownload } from './useExportDownload';

vi.mock('@/app/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/app/api')>();

  return {
    ...actual,
    api: {
      ...actual.api,
      createExport: vi.fn<typeof actual.api.createExport>(),
      download: vi.fn<typeof actual.api.download>(),
    },
  };
});

interface HarnessSnapshot {
  readonly exports: StudioExport[];
  readonly error: string | null;
  readonly exportProject: ReturnType<typeof useExportDownload>['exportProject'];
}

const mountedRoots: Array<{ container: HTMLDivElement; root: Root }> = [];
const project: Project = {
  id: 'project-1',
  title: 'Clockwork Harbor',
  description: 'A harbor of brass clocks.',
  settings: {},
  import_hash: null,
  created_at: '2026-06-19T00:00:00Z',
  updated_at: '2026-06-19T00:00:00Z',
  documents: [],
};
const studioExport: StudioExport = {
  id: 'export-1',
  project_id: project.id,
  snapshot_id: 'snapshot-1',
  format: 'markdown',
  size_bytes: 128,
  checksum_sha256: 'checksum-1',
  created_at: '2026-06-19T00:01:00Z',
  download_url: '/downloads/export-1',
};

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  for (const { container, root } of mountedRoots) {
    act(() => {
      root.unmount();
    });
    container.remove();
  }
  mountedRoots.length = 0;
  vi.clearAllTimers();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.resetAllMocks();
  vi.restoreAllMocks();
});

function renderExportHook(selectedProject: Project | null = project): {
  readonly result: () => HarnessSnapshot;
} {
  let current: HarnessSnapshot | undefined;

  function Wrapper(): null {
    const [exports, setExports] = useState<StudioExport[]>([]);
    const [error, setError] = useState<string | null>(null);
    const { exportProject } = useExportDownload(selectedProject, project.id, setExports, setError);
    current = { exports, error, exportProject };
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
      if (current === undefined) {
        throw new Error('Expected hook result after render.');
      }
      return current;
    },
  };
}

describe('useExportDownload', () => {
  it('downloads markdown with an md filename and revokes the object URL', async () => {
    // Given
    const blob = new Blob(['# Clockwork Harbor'], { type: 'text/markdown' });
    const createObjectURL = vi.fn<(value: Blob) => string>().mockReturnValue('blob:export-1');
    const revokeObjectURL = vi.fn<(value: string) => void>();
    let clickedHref = '';
    let clickedDownload = '';
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL });
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
      this: HTMLAnchorElement,
    ) {
      clickedHref = this.href;
      clickedDownload = this.download;
    });
    vi.mocked(api.createExport).mockResolvedValue(studioExport);
    vi.mocked(api.download).mockResolvedValue(blob);
    const harness = renderExportHook();

    // When
    await act(async () => {
      await harness.result().exportProject('markdown');
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    // Then
    expect(harness.result().exports).toEqual([studioExport]);
    expect(clickedHref).toBe('blob:export-1');
    expect(clickedDownload).toBe('Clockwork Harbor.md');
    expect(createObjectURL).toHaveBeenCalledWith(blob);
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:export-1');
  });

  it('reports the export error without creating a download link', async () => {
    // Given
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click');
    vi.mocked(api.createExport).mockRejectedValue(new Error('export unavailable'));
    const harness = renderExportHook();

    // When
    await act(async () => {
      await harness.result().exportProject('docx');
    });

    // Then
    expect(harness.result().error).toBe('export unavailable');
    expect(harness.result().exports).toEqual([]);
    expect(click).not.toHaveBeenCalled();
    expect(api.download).not.toHaveBeenCalled();
  });

  it('does nothing when no project is selected', async () => {
    // Given
    const harness = renderExportHook(null);

    // When
    await act(async () => {
      await harness.result().exportProject('epub');
    });

    // Then
    expect(harness.result().exports).toEqual([]);
    expect(harness.result().error).toBeNull();
    expect(api.createExport).not.toHaveBeenCalled();
  });
});
