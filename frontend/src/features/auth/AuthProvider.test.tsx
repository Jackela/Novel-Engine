import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { api } from '@/app/api';
import { sessionStorageKey } from '@/shared/storage';

import { render, screen, waitFor } from '../../../tests/test-utils';
import { AuthProvider } from './AuthProvider';
import { useAuth } from './useAuth';

function SessionProbe() {
  const { session, signIn } = useAuth();

  return (
    <div>
      <div data-testid="session-state">{session ? session.kind : 'empty'}</div>
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
});
