import userEvent from '@testing-library/user-event';
import { act } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { api } from '@/app/api';
import { readSessionCatalog } from '@/shared/storage';

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
      <div data-testid="workspace-selection">{session?.lastWorkspaceId ?? 'none'}</div>
      <div data-testid="active-workspace-label">
        {session?.activeWorkspace?.label ?? 'none'}
      </div>
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
            lastWorkspaceId: 'workspace-123',
            lastJobId: 'job-456',
            lastView: 'playback',
            activeWorkspace: {
              workspaceId: 'workspace-123',
              workspaceKind: 'guest',
              label: 'The Salt Ledger',
              persistence: 'ephemeral',
              summary: 'workspace-123 / 2 chapters',
            },
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

    const storedSession = readSessionCatalog().sessions[0];

    expect(storedSession).toMatchObject({
      kind: 'user',
      workspaceId: 'workspace-123',
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
      workspace_id: 'user-123-safe',
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
    await user.click(screen.getByTestId('probe-update-selection'));
    await waitFor(() => {
      expect(screen.getByTestId('active-workspace-label')).toHaveTextContent(
        'The Salt Ledger',
      );
    });

    await user.click(screen.getByTestId('probe-sign-in'));
    await waitFor(() => {
      expect(screen.getByTestId('workspace-state')).toHaveTextContent('user-123-safe');
    });

    await user.click(screen.getByTestId('probe-switch-guest'));
    await waitFor(() => {
      expect(screen.getByTestId('workspace-state')).toHaveTextContent('guest-123');
    });
    expect(screen.getByTestId('active-workspace-label')).toHaveTextContent(
      'The Salt Ledger',
    );

    expect(api.createGuestSession).toHaveBeenLastCalledWith({ workspace_id: 'guest-123' });
  });

  it('restores and validates a saved user session on mount', async () => {
    window.localStorage.setItem(
      'novel-engine-session-catalog',
      JSON.stringify({
        version: 3,
        activeSessionId: 'user:user-operator',
        sessions: [
          {
            id: 'user:user-operator',
            kind: 'user',
            workspaceId: 'user-operator',
            user: {
              id: 'stale-user',
              name: 'stale',
              email: 'stale@novel.engine',
            },
            activeWorkspace: {
              workspaceId: 'saved-user-story',
              workspaceKind: 'user',
              label: 'Saved User Story',
              persistence: 'persistent',
              summary: 'saved-user-story / 2 chapters',
            },
            lastWorkspaceId: null,
            lastJobId: null,
            lastView: 'workspace',
          },
        ],
      }),
    );
    vi.spyOn(api, 'getCurrentUser').mockResolvedValue({
      id: 'user-123',
      username: 'operator',
      email: 'operator@novel.engine',
      roles: ['author'],
      workspace_id: 'user-123-safe',
      identity_kind: 'user',
      workspace_kind: 'user',
      active_workspace: {
        workspace_id: 'user-123-safe',
        workspace_kind: 'user',
        label: 'Signed-in workspace',
        persistence: 'persistent',
        summary: 'Stable author workspace bound to the authenticated identity.',
      },
    });

    render(
      <AuthProvider>
        <SessionProbe />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(api.getCurrentUser).toHaveBeenCalledWith();
    });
    await act(async () => {
      await Promise.resolve();
    });
    await waitFor(() => {
      expect(screen.getByTestId('session-state')).toHaveTextContent('user');
      expect(screen.getByTestId('workspace-state')).toHaveTextContent('user-123-safe');
      expect(screen.getByTestId('loading-state')).toHaveTextContent('ready');
      expect(screen.getByTestId('active-workspace-label')).toHaveTextContent(
        'Saved User Story',
      );
    });
  });

  it('updates active session selection and signs out the active session', async () => {
    vi.spyOn(api, 'logout').mockResolvedValue({ message: 'Successfully logged out' });
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
      expect(screen.getByTestId('workspace-selection')).toHaveTextContent(
        'workspace-123',
      );
    });
    expect(screen.getByTestId('active-workspace-label')).toHaveTextContent(
      'The Salt Ledger',
    );
    expect(readSessionCatalog().sessions[0].activeWorkspace).toMatchObject({
      workspaceId: 'workspace-123',
      label: 'The Salt Ledger',
      summary: 'workspace-123 / 2 chapters',
    });

    await user.click(screen.getByTestId('probe-sign-out'));
    await waitFor(() => {
      expect(screen.getByTestId('session-state')).toHaveTextContent('empty');
    });
    expect(readSessionCatalog().activeSessionId).toBeNull();
  });
});
