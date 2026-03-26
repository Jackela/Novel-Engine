import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';

import { api } from '@/app/api';
import { sessionStorageKey } from '@/shared/storage';

describe('api', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('attaches the stored bearer token to authenticated requests', async () => {
    window.localStorage.setItem(
      sessionStorageKey,
      JSON.stringify({
        kind: 'user',
        workspaceId: 'workspace-123',
        token: 'access-token-123',
        refreshToken: 'refresh-token-456',
        user: {
          id: 'user-123',
          name: 'Operator',
          email: 'operator@novel.engine',
        },
      }),
    );

    const response = new Response(
      JSON.stringify({
        status: 'healthy',
        mode: 'remote',
        workspaceId: 'workspace-123',
        headline: 'Live dashboard',
        summary: 'Backend is healthy.',
        activeCharacters: 3,
        activeSignals: 1,
      }),
      {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
        },
      },
    );
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(response);

    await api.getDashboardStatus('workspace-123');

    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/v1/dashboard/status?workspace_id=workspace-123',
      expect.objectContaining({
        credentials: 'include',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
          Authorization: 'Bearer access-token-123',
        }),
      }),
    );
  });
});
