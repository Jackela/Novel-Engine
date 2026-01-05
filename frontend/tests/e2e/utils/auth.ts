import { type Page } from '@playwright/test';

export const resetAuthState = async (page: Page) => {
  await page.context().clearCookies();
  await page.addInitScript(() => {
    try {
      localStorage.clear();
      sessionStorage.clear();
    } catch {
      // ignore storage errors on opaque origins
    }
  });
};

export const mockGuestSessionApi = async (page: Page) => {
  await page.route(/\/api\/guest\/session/, async route => {
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
      localStorage.setItem('guest_session_active', '1');
      sessionStorage.setItem('guest_session_active', '1');
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
