import { test, expect } from '@playwright/test';

const BASE_URL =
  process.env.E2E_BASE_URL ||
  process.env.PLAYWRIGHT_BASE_URL ||
  'http://localhost:3000';

const DESKTOP_PROJECT = 'chromium-desktop';

test.describe('Dashboard interactions', () => {
  test('map entities toggle selection state', async ({ page }, testInfo) => {
    test.skip(
      testInfo.project.name !== DESKTOP_PROJECT,
      'Runs on chromium desktop only'
    );

    await page.goto(`${BASE_URL}/dashboard`);

    const entityNames = ['Aria', 'Kael', 'Shadowbane', 'Merchant'];
    for (const name of entityNames) {
      const entityButton = page.getByRole('button', { name });
      await entityButton.click();
      await expect(entityButton).toHaveClass(/selected/);
    }
  });

  test('quick actions toggle pipeline state', async ({ page }, testInfo) => {
    test.skip(
      testInfo.project.name !== DESKTOP_PROJECT,
      'Runs on chromium desktop only'
    );

    await page.setViewportSize({ width: 1400, height: 900 });
    await page.goto(`${BASE_URL}/dashboard`);

    const pipelineTile = page.getByTestId('turn-pipeline-status');
    const quickActionsTile = page.getByTestId('quick-actions');
    await quickActionsTile.getByTestId('quick-action-play').click();
    await expect(pipelineTile).toHaveClass(/active/);
    await expect(page.getByTestId('live-indicator')).toBeVisible();
    await quickActionsTile.getByTestId('quick-action-pause').click();
    await expect(pipelineTile).not.toHaveClass(/active/);
    await expect(page.getByTestId('live-indicator')).toHaveCount(0);
  });

  test('header controls respond to viewport changes', async ({ page }, testInfo) => {
    test.skip(
      testInfo.project.name !== DESKTOP_PROJECT,
      'Runs on chromium desktop only'
    );

    await page.setViewportSize({ width: 1400, height: 900 });
    await page.goto(`${BASE_URL}/dashboard`);

    const actions = page.locator('.dashboard-header__actions');
    await expect(actions).toBeVisible();

    const desktopDisplay = await actions.evaluate(
      (el) => getComputedStyle(el).display
    );
    expect(desktopDisplay).toBe('flex');

    await page.setViewportSize({ width: 820, height: 900 });
    await page.waitForTimeout(150);
    const tabletDisplay = await actions.evaluate(
      (el) => getComputedStyle(el).display
    );
    expect(tabletDisplay).toBe('grid');
  });
});
