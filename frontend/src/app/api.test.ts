import { afterEach, describe, expect, it, vi } from 'vitest';

import { api } from '@/app/api';

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      'Content-Type': 'application/json',
    },
  });
}

describe('api', () => {
  afterEach(() => {
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  it('uses cookie credentials without bearer tokens for workspace requests', async () => {
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(jsonResponse({ workspaces: [] }));

    await api.listWorkspaces();

    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/workspaces',
      expect.objectContaining({
        credentials: 'include',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
        }),
      }),
    );
    expect(fetchSpy.mock.calls[0]?.[1]?.headers).not.toHaveProperty('Authorization');
  });

  it('creates a workspace through the local workspace endpoint', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      jsonResponse({
        workspace_id: 'salt-ledger',
        story: {
          title: 'The Salt Ledger',
          genre: 'mystery',
          premise: 'A courier receives a page that names debts before they happen.',
          target_chapters: 3,
          tone: 'sharp',
          themes: [],
        },
        chapters: [],
        latest_review: null,
        exports: [],
        runs: [],
        jobs: [],
      }, 201),
    );

    const result = await api.createWorkspace({
      workspace_id: 'salt-ledger',
      title: 'The Salt Ledger',
      genre: 'mystery',
      premise: 'A courier receives a page that names debts before they happen.',
      target_chapters: 3,
    });

    expect(result.workspace_id).toBe('salt-ledger');
    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/workspaces',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          workspace_id: 'salt-ledger',
          title: 'The Salt Ledger',
          genre: 'mystery',
          premise: 'A courier receives a page that names debts before they happen.',
          target_chapters: 3,
        }),
      }),
    );
  });

  it('covers auth and workspace endpoints with cookie requests', async () => {
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockImplementation(async () => jsonResponse({ ok: true }));

    await api.createGuestSession({ workspace_id: 'guest-1' });
    await api.login({ email: 'operator@novel.engine', password: 'demo-password' });
    await api.refreshSession();
    await api.logout();
    await api.getCurrentUser();
    await api.listProviders();
    await api.listWorkspaces();
    await api.getWorkspace('salt ledger');

    const calledPaths = fetchSpy.mock.calls.map((call) => String(call[0]));
    expect(calledPaths).toEqual(
      expect.arrayContaining([
        '/api/guest/session',
        '/api/auth/login',
        '/api/auth/refresh',
        '/api/auth/logout',
        '/api/auth/me',
        '/api/providers',
        '/api/workspaces',
        '/api/workspaces/salt%20ledger',
      ]),
    );
  });

  it('runs and polls a workspace job', async () => {
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(
        jsonResponse(
          {
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
          },
          202,
        ),
      )
      .mockResolvedValueOnce(
        jsonResponse({
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
        }),
      );

    await api.createWorkspaceJob('salt-ledger', {
      operation: 'run',
      target_chapters: 3,
      provider: 'mock',
    });
    const polled = await api.getWorkspaceJob('salt-ledger', 'job-1');

    expect(polled.status).toBe('completed');
    expect(fetchSpy.mock.calls[0]?.[0]).toBe('/api/workspaces/salt-ledger/jobs');
    expect(fetchSpy.mock.calls[1]?.[0]).toBe(
      '/api/workspaces/salt-ledger/jobs/job-1',
    );
  });

  it('surfaces JSON detail messages for failed requests', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      jsonResponse({ detail: 'Workspace not found' }, 404),
    );

    await expect(api.getWorkspace('missing')).rejects.toThrow('Workspace not found');
  });

  it('handles nested JSON, text, timeout, and network failures', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      jsonResponse({ error: { message: 'Nested failure' } }, 400),
    );
    await expect(api.getWorkspace('nested')).rejects.toThrow('Nested failure');

    vi.mocked(globalThis.fetch).mockResolvedValueOnce(
      new Response('plain failure', {
        status: 500,
        headers: { 'Content-Type': 'text/plain' },
      }),
    );
    await expect(api.getWorkspace('plain')).rejects.toThrow('plain failure');

    vi.mocked(globalThis.fetch).mockResolvedValueOnce(
      new Response('<html>bad gateway</html>', {
        status: 503,
        headers: { 'Content-Type': 'text/html' },
      }),
    );
    await expect(api.getWorkspace('html')).rejects.toThrow(
      'Service temporarily unavailable. Start the backend API and retry.',
    );

    vi.mocked(globalThis.fetch).mockRejectedValueOnce(
      Object.assign(new Error('aborted'), { name: 'AbortError' }),
    );
    await expect(api.getWorkspace('timeout')).rejects.toThrow('Request cancelled.');

    vi.mocked(globalThis.fetch).mockRejectedValueOnce(new TypeError('failed'));
    await expect(api.getWorkspace('network')).rejects.toThrow(
      'Service temporarily unavailable. Start the backend API and retry.',
    );
  });
});
