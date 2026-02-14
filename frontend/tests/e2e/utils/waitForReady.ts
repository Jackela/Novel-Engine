import { expect, type Page, type Locator } from '@playwright/test';

type ReadyTarget = string | Locator;

const DEFAULT_TIMEOUT_MS = 30000;

const toLocator = (page: Page, target: ReadyTarget) =>
  typeof target === 'string' ? page.locator(target) : target;

export const waitForLandingReady = async (page: Page) => {
  const cta = page.locator('[data-testid="cta-launch"]');
  const heroTitle = page.getByRole('heading', { name: /narrative engine/i });

  await Promise.any([
    cta.waitFor({ state: 'visible', timeout: DEFAULT_TIMEOUT_MS }),
    heroTitle.waitFor({ state: 'visible', timeout: DEFAULT_TIMEOUT_MS }),
  ]);
};

export const waitForLoginReady = async (page: Page) => {
  const heading = page.locator('main h1, [role="main"] h1');
  await expect(heading).toBeVisible({ timeout: DEFAULT_TIMEOUT_MS });
};

export const waitForDashboardReady = async (page: Page) => {
  const layout = page.locator('[data-testid="dashboard-layout"]');
  const isVisible = await layout
    .waitFor({ state: 'visible', timeout: 2000 })
    .then(() => true)
    .catch(() => false);

  if (!isVisible) {
    await page.evaluate(() => {
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
        // ignore storage errors
      }
    });

    if (page.url().includes('/dashboard')) {
      await page.reload({ waitUntil: 'domcontentloaded' });
    } else {
      await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
    }
  }

  await expect(layout).toBeVisible({ timeout: DEFAULT_TIMEOUT_MS });
  await page
    .locator('[data-testid="world-state-map"]')
    .first()
    .waitFor({ state: 'attached', timeout: DEFAULT_TIMEOUT_MS })
    .catch(() => {});
};

export const waitForRouteReady = async (
  page: Page,
  target: ReadyTarget,
  options: { url?: RegExp | string; timeoutMs?: number } = {}
) => {
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  if (options.url) {
    await page.waitForURL(options.url, { timeout: timeoutMs });
  }
  const locator = toLocator(page, target);
  await expect(locator).toBeVisible({ timeout: timeoutMs });
};
