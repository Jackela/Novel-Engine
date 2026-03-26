import { test, expect } from '@playwright/test';

test.describe('frontend smoke', () => {
  test('guest session reaches dashboard', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByTestId('landing-page')).toBeVisible();
    await page.getByTestId('launch-guest').click();

    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.getByTestId('dashboard-page')).toBeVisible();
    await expect(page.getByTestId('workspace-badge')).toContainText('Guest /');
    await expect(page.getByTestId('event-mode')).toHaveText('Backend stream');
    await expect(page.getByTestId('event-feed')).toBeVisible();
  });

  test('login reaches dashboard and can start orchestration', async ({ page }) => {
    await page.goto('/login');

    await page.getByTestId('login-email').fill('operator@novel.engine');
    await page.getByTestId('login-password').fill('demo-password');
    await page.getByTestId('login-submit').click();

    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.getByTestId('workspace-badge')).toContainText('Workspace / user-operator');
    await expect(page.getByTestId('event-mode')).toHaveText('Backend stream');

    await page.getByTestId('start-orchestration').click();
    await expect(page.getByTestId('orchestration-status')).toContainText('Turn 0 / 3');
  });

  test('direct dashboard access restores session', async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem(
        'novel-engine-session',
        JSON.stringify({
          kind: 'guest',
          workspaceId: 'workspace-direct-test',
        }),
      );
    });

    await page.goto('/dashboard');

    await expect(page.getByTestId('dashboard-page')).toBeVisible();
    await expect(page.getByTestId('workspace-badge')).toContainText('workspace-direct-test');
    await expect(page.getByTestId('event-mode')).toHaveText('Backend stream');
    await page.getByTestId('start-orchestration').click();
    await expect(page.getByTestId('orchestration-status')).toContainText('Turn');
  });
});
