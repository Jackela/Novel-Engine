import { expect, type Page, type Locator } from '@playwright/test';

type ReadyTarget = string | Locator;

const DEFAULT_TIMEOUT_MS = 30000;

const toLocator = (page: Page, target: ReadyTarget) =>
  typeof target === 'string' ? page.locator(target) : target;

export const waitForLandingReady = async (page: Page) => {
  const cta = page.locator('[data-testid="cta-launch"]');
  await expect(cta).toBeVisible({ timeout: DEFAULT_TIMEOUT_MS });
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
    const cta = page.locator('[data-testid="cta-launch"]');
    const ctaVisible = await cta.isVisible().catch(() => false);
    if (ctaVisible) {
      await page.route(/\/api\/guest\/session/, async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ workspace_id: 'ws-mock', created: false }),
        });
      });
      await cta.click();
      await page.waitForURL('**/dashboard', { timeout: DEFAULT_TIMEOUT_MS }).catch(() => {});
    } else if (!page.url().includes('/dashboard')) {
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
