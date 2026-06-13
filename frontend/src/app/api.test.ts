import { afterEach, describe, expect, it, vi } from 'vitest';

import { api } from './api';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('Studio API client', () => {
  it('uses the project contract and includes cookies', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ projects: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(api.projects()).resolves.toEqual({ projects: [] });
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/projects',
      expect.objectContaining({ credentials: 'include' }),
    );
  });

  it('preserves revision conflict detail', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: {
              message: 'Document changed since the requested base revision.',
              current_revision_id: 'revision-b',
            },
          }),
          { status: 409, headers: { 'Content-Type': 'application/json' } },
        ),
      ),
    );

    const request = api.saveDocument('project', 'document', {
      content_markdown: 'stale',
      base_revision_id: 'revision-a',
    });
    await expect(request).rejects.toMatchObject({
      status: 409,
      detail: expect.objectContaining({ current_revision_id: 'revision-b' }),
    });
  });

  it('propagates caller cancellation through the internal request signal', async () => {
    const controller = new AbortController();
    vi.stubGlobal(
      'fetch',
      vi.fn((_input: RequestInfo | URL, init?: RequestInit) => new Promise((_resolve, reject) => {
        init?.signal?.addEventListener('abort', () => {
          reject(new DOMException('Aborted', 'AbortError'));
        });
      })),
    );

    const pending = api.projects({ signal: controller.signal });
    controller.abort();

    await expect(pending).rejects.toThrow('Request cancelled.');
  });
});
