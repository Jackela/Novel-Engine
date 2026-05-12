import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { api } from '@/app/api';
import { sessionStorageKey } from '@/shared/storage';

import { render, screen, waitFor } from '../../../tests/test-utils';
import { AuthProvider } from './AuthProvider';
import { useAuth } from './useAuth';

function SessionProbe() {
  const {
    session,
    sessions,
    isLoading,
    signIn,
    signInAsGuest,
    switchSession,
    signOut,
    updateSessionSelection,
  } = useAuth();
  const guestSessionId = sessions.find((entry) => entry.kind === 'guest')?.id ?? null;

  return (
    <div>
      <div data-testid="loading-state">{isLoading ? 'loading' : 'ready'}</div>
      <div data-testid="session-state">{session ? session.kind : 'empty'}</div>
      <div data-testid="workspace-state">{session?.workspaceId ?? 'none'}</div>
      <div data-testid="story-selection">{session?.lastStoryId ?? 'none'}</div>
      <button
        data-testid="probe-sign-in"
        onClick={() =>
          void signIn({
            email: 'operator@novel.engine',
            password: 'demo-password',
          })
        }
        type="button"
      >
        Sign in
      </button>
      <button
        data-testid="probe-launch-guest"
        onClick={() => void signInAsGuest()}
        type="button"
      >
        Launch guest
      </button>
      <button
        data-testid="probe-switch-guest"
        onClick={() => {
          if (guestSessionId) {
            void switchSession(guestSessionId);
          }
        }}
        type="button"
      >
        Switch guest
      </button>
      <button data-testid="probe-sign-out" onClick={() => signOut()} type="button">
        Sign out
      </button>
      <button
        data-testid="probe-update-selection"
        onClick={() =>
          updateSessionSelection({
            lastStoryId: 'story-123',
            lastRunId: 'run-456',
            lastView: 'playback',
          })
        }
        type="button"
      >
        Update selection
      </button>
    </div>
  );
}

describe('AuthProvider', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('persists the backend login response shape', async () => {
    vi.spyOn(api, 'login').mockResolvedValue({
      access_token: 'access-token-123',
      refresh_token: 'refresh-token-456',
      token_type: 'bearer',
      workspace_id: 'workspace-123',
      user: {
        id: 'user-123',
        name: 'Operator',
        email: 'operator@novel.engine',
      },
    });

    const user = userEvent.setup();
    render(
      <AuthProvider>
        <SessionProbe />
      </AuthProvider>,
    );

    await user.click(screen.getByTestId('probe-sign-in'));

    await waitFor(() => {
      expect(screen.getByTestId('session-state')).toHaveTextContent('user');
    });

    const storedSession = JSON.parse(
      window.localStorage.getItem(sessionStorageKey) ?? 'null',
    ) as Record<string, unknown> | null;

    expect(storedSession).toMatchObject({
      kind: 'user',
      workspaceId: 'workspace-123',
      token: 'access-token-123',
      refreshToken: 'refresh-token-456',
      user: {
        id: 'user-123',
        name: 'Operator',
        email: 'operator@novel.engine',
      },
    });
  });

  it('switches back to a saved guest session after signing in', async () => {
    vi.spyOn(api, 'createGuestSession').mockImplementation(
      async (payload) =>
        ({
          workspace_id: payload?.workspace_id ?? 'guest-123',
          identity_kind: 'guest',
          workspace_kind: 'guest',
          active_workspace: {
            workspace_id: payload?.workspace_id ?? 'guest-123',
            workspace_kind: 'guest',
            label: 'Guest workspace',
            persistence: 'ephemeral',
            summary: 'Disposable workspace for drafting and flow verification.',
          },
        }) as Awaited<ReturnType<typeof api.createGuestSession>>,
    );
    vi.spyOn(api, 'login').mockResolvedValue({
      access_token: 'access-token-123',
      refresh_token: 'refresh-token-456',
      token_type: 'bearer',
      workspace_id: 'user-operator',
      user: {
        id: 'user-123',
        name: 'Operator',
        email: 'operator@novel.engine',
      },
    });

    const user = userEvent.setup();
    render(
      <AuthProvider>
        <SessionProbe />
      </AuthProvider>,
    );

    await user.click(screen.getByTestId('probe-launch-guest'));
    await waitFor(() => {
      expect(screen.getByTestId('workspace-state')).toHaveTextContent('guest-123');
    });

    await user.click(screen.getByTestId('probe-sign-in'));
    await waitFor(() => {
      expect(screen.getByTestId('workspace-state')).toHaveTextContent('user-operator');
    });

    await user.click(screen.getByTestId('probe-switch-guest'));
    await waitFor(() => {
      expect(screen.getByTestId('workspace-state')).toHaveTextContent('guest-123');
    });

    expect(api.createGuestSession).toHaveBeenLastCalledWith({ workspace_id: 'guest-123' });
  });

  it('restores and validates a saved user session on mount', async () => {
    window.localStorage.setItem(
      sessionStorageKey,
      JSON.stringify({
        kind: 'user',
        workspaceId: 'user-operator',
        token: 'saved-token',
        refreshToken: 'saved-refresh-token',
        user: {
          id: 'stale-user',
          name: 'stale',
          email: 'stale@novel.engine',
        },
      }),
    );
    vi.spyOn(api, 'getCurrentUser').mockResolvedValue({
      id: 'user-123',
      username: 'operator',
      email: 'operator@novel.engine',
      roles: ['author'],
    });

    render(
      <AuthProvider>
        <SessionProbe />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('session-state')).toHaveTextContent('user');
      expect(screen.getByTestId('workspace-state')).toHaveTextContent('user-operator');
    });
    expect(api.getCurrentUser).toHaveBeenCalledWith('saved-token');
  });

  it('updates active session selection and signs out the active session', async () => {
    vi.spyOn(api, 'createGuestSession').mockResolvedValue({
      workspace_id: 'guest-123',
      identity_kind: 'guest',
      workspace_kind: 'guest',
      active_workspace: {
        workspace_id: 'guest-123',
        workspace_kind: 'guest',
        label: 'Guest workspace',
        persistence: 'ephemeral',
        summary: 'Disposable workspace for drafting and flow verification.',
      },
    });

    const user = userEvent.setup();
    render(
      <AuthProvider>
        <SessionProbe />
      </AuthProvider>,
    );

    await user.click(screen.getByTestId('probe-launch-guest'));
    await waitFor(() => {
      expect(screen.getByTestId('session-state')).toHaveTextContent('guest');
    });

    await user.click(screen.getByTestId('probe-update-selection'));
    await waitFor(() => {
      expect(screen.getByTestId('story-selection')).toHaveTextContent('story-123');
    });

    await user.click(screen.getByTestId('probe-sign-out'));
    await waitFor(() => {
      expect(screen.getByTestId('session-state')).toHaveTextContent('empty');
    });
    expect(window.localStorage.getItem(sessionStorageKey)).toBeNull();
  });
});
