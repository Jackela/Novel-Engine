import { type Page } from '@playwright/test';

export const resetAuthState = async (page: Page) => {
  await page.context().clearCookies();
  await page.addInitScript(() => {
    try {
      localStorage.clear();
      sessionStorage.clear();
      localStorage.setItem('e2e_bypass_auth', '0');
      localStorage.removeItem('e2e_preserve_auth');
    } catch {
      // ignore storage errors on opaque origins
    }
  });
};

export const mockGuestSessionApi = async (page: Page) => {
  await page.route(/\/api\/guest\/sessions/, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ workspace_id: 'ws-mock', created: false }),
    });
  });
};

export const activateGuestSession = async (page: Page) => {
  await page.addInitScript(() => {
    try {
      const guestToken = {
        accessToken: 'guest',
        refreshToken: '',
        tokenType: 'Guest',
        expiresAt: Date.now() + 60 * 60 * 1000,
        refreshExpiresAt: 0,
        user: {
          id: 'guest',
          username: 'guest',
          email: '',
          roles: ['guest'],
        },
      };
      const payload = {
        state: {
          token: guestToken,
          isGuest: true,
          workspaceId: 'ws-mock',
        },
        version: 0,
      };
      localStorage.setItem('novel-engine-auth', JSON.stringify(payload));
      localStorage.setItem('novelengine_guest_session', '1');
      sessionStorage.setItem('novelengine_guest_session', '1');
      localStorage.setItem('e2e_bypass_auth', '1');
      localStorage.setItem('e2e_preserve_auth', '1');
    } catch {
      // ignore storage errors on opaque origins
    }
  });
};

export const prepareGuestSession = async (page: Page, options: { activate?: boolean } = {}) => {
  await mockGuestSessionApi(page);
  if (options.activate ?? true) {
    await activateGuestSession(page);
  }
};
