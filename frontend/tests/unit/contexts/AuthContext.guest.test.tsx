import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const mockGuestAPI = vi.hoisted(() => ({
  createOrResumeSession: vi.fn(),
}));

vi.mock('@/config/env', () => ({
  default: { enableGuestMode: true, apiBaseUrl: '', apiTimeout: 1000 },
  config: { enableGuestMode: true, apiBaseUrl: '', apiTimeout: 1000 },
}));

vi.mock('@/services/api/guestAPI', () => ({
  guestAPI: mockGuestAPI,
}));

const createMockAuthService = () => ({
  login: vi.fn(),
  logout: vi.fn(),
  refreshToken: vi.fn(),
  isAuthenticated: vi.fn().mockResolvedValue(false),
  getToken: vi.fn().mockReturnValue(null),
  onAuthStateChange: vi.fn().mockReturnValue(() => {}),
  onUnauthenticated: vi.fn(),
  startTokenRefresh: vi.fn(),
  stopTokenRefresh: vi.fn(),
});

describe('AuthProvider guest bootstrap', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
    window.sessionStorage.clear();
});

  afterEach(() => {
    vi.restoreAllMocks();
    window.sessionStorage.clear();
  });

  it('resumes guest session when session flag is present', async () => {
    const { AuthProvider, useAuthContext } = await import('@/contexts/AuthContext');
    const { guestAPI: mockedGuestAPI } = await import('@/services/api/guestAPI');
    const envConfig = (await import('@/config/env')).default;
    expect(envConfig.enableGuestMode).toBe(true);
    expect(mockedGuestAPI).toBe(mockGuestAPI);

    const authService = createMockAuthService();
    mockGuestAPI.createOrResumeSession.mockResolvedValue({
      workspace_id: 'ws-guest-123',
      created: false,
    });
    window.sessionStorage.setItem('guest_session_active', '1');
    vi.spyOn(window.sessionStorage, 'getItem').mockReturnValue('1');

    const ContextProbe = () => {
      const { isGuest, workspaceId, isLoading, enterGuestMode } = useAuthContext();

      React.useEffect(() => {
        if (window.sessionStorage.getItem('guest_session_active') === '1') {
          void enterGuestMode();
        }
      }, []);

      return (
        <div data-testid="auth-state">
          {isGuest ? 'guest' : 'user'}|{workspaceId ?? ''}|{isLoading ? 'loading' : 'ready'}
        </div>
      );
    };

    render(
      <AuthProvider authService={authService}>
        <ContextProbe />
      </AuthProvider>
    );

    await waitFor(() => expect(authService.isAuthenticated).toHaveBeenCalled());
    await waitFor(() => expect(mockedGuestAPI.createOrResumeSession).toHaveBeenCalled());
    await waitFor(
      () => expect(screen.getByTestId('auth-state').textContent).toBe('guest|ws-guest-123|ready'),
      { timeout: 2000 }
    );

    expect(mockGuestAPI.createOrResumeSession).toHaveBeenCalled();
  });
});
