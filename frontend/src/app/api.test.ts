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

  it('rejects project payloads that do not match the API contract', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ projects: [{ id: 'p1' }] }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );

    const error = await api.projects().catch((reason: unknown) => reason);
    expect(error).toMatchObject({ message: 'Invalid projects[0].title' });
  });

  it('preserves unified revision conflict code and details', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: 'REVISION_CONFLICT',
              message: 'Document changed since the requested base revision.',
              details: { current_revision_id: 'revision-b' },
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
      code: 'REVISION_CONFLICT',
      detail: expect.objectContaining({ current_revision_id: 'revision-b' }),
    });
  });

  it('still interprets the legacy detail error payload until cutover', async () => {
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

  it('falls back to the status message for unrecognised error bodies', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ unexpected: 'shape' }), {
          status: 422,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );

    const error = await api.projects().catch((reason: unknown) => reason);
    expect(error).toMatchObject({
      message: 'Request failed with status 422',
      status: 422,
    });
  });

  it('propagates caller cancellation through the internal request signal', async () => {
    const controller = new AbortController();
    vi.stubGlobal(
      'fetch',
      vi.fn(
        (_input: RequestInfo | URL, init?: RequestInit) =>
          new Promise((_resolve, reject) => {
            init?.signal?.addEventListener('abort', () => {
              reject(new DOMException('Aborted', 'AbortError'));
            });
          }),
      ),
    );

    const pending = api.projects({ signal: controller.signal });
    controller.abort();

    const error = await pending.catch((reason: unknown) => reason);
    expect(error).toMatchObject({ message: 'Request cancelled.' });
  });

  it('sends X-CSRF-Token header on write requests when cookie is present', async () => {
    vi.stubGlobal('document', { cookie: 'novel_engine_csrf=test-csrf-token' });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 'p1',
          title: 'Title',
          description: '',
          settings: {},
          import_hash: null,
          created_at: '2026-06-25T00:00:00Z',
          updated_at: '2026-06-25T00:00:00Z',
        }),
        {
          status: 201,
          headers: { 'Content-Type': 'application/json' },
        },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(api.createProject('Title', '')).resolves.toMatchObject({ id: 'p1' });
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/projects',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ 'X-CSRF-Token': 'test-csrf-token' }),
      }),
    );
  });

  it('does not send X-CSRF-Token header on read requests', async () => {
    vi.stubGlobal('document', { cookie: 'novel_engine_csrf=test-csrf-token' });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ projects: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(api.projects()).resolves.toEqual({ projects: [] });
    const init = fetchMock.mock.calls[0][1] as RequestInit | undefined;
    const headers = init?.headers as Record<string, string> | undefined;
    expect(headers?.['X-CSRF-Token']).toBeUndefined();
  });

  it('falls back to the legacy novel_studio_csrf cookie until cutover', async () => {
    vi.stubGlobal('document', { cookie: 'novel_studio_csrf=legacy-csrf-token' });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 'p1',
          title: 'Title',
          description: '',
          settings: {},
          import_hash: null,
          created_at: '2026-06-25T00:00:00Z',
          updated_at: '2026-06-25T00:00:00Z',
        }),
        {
          status: 201,
          headers: { 'Content-Type': 'application/json' },
        },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(api.createProject('Title', '')).resolves.toMatchObject({ id: 'p1' });
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/projects',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ 'X-CSRF-Token': 'legacy-csrf-token' }),
      }),
    );
  });
});
