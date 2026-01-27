import { test, expect } from './fixtures';
import { DashboardPage } from './pages/DashboardPage';
import { checkA11y } from './utils/a11y';

test.describe('Dashboard Interactions', () => {
  let dashboardPage: DashboardPage;

  test.beforeEach(async ({ page }) => {
    dashboardPage = new DashboardPage(page);
    await dashboardPage.navigateToDashboard({ mockAPIs: true });
  });

  test('Dashboard panels render', async () => {
    await expect(dashboardPage.pageTitle).toHaveText(/Dashboard/i);
    await expect(dashboardPage.worldStateMap).toBeVisible();
    await expect(dashboardPage.characterNetworks).toBeVisible();
    await expect(dashboardPage.narrativeTimeline).toBeVisible();
    await expect(dashboardPage.narrativePanel).toBeVisible();
    await expect(dashboardPage.analyticsPanel).toBeVisible();
    await expect(dashboardPage.signalsPanel).toBeVisible();
  });

  test('@experience-offline @smoke Dashboard panels remain visible when offline toggles', async () => {
    await expect(dashboardPage.dashboardLayout).toBeVisible();
    await expect(dashboardPage.worldStateMap).toBeVisible();
    await checkA11y(dashboardPage.page);

    await dashboardPage.page.context().setOffline(true);
    await dashboardPage.page.waitForTimeout(500);
    await expect(dashboardPage.dashboardLayout).toBeVisible();
    await expect(dashboardPage.worldStateMap).toBeVisible();

    await dashboardPage.page.context().setOffline(false);
    await expect(dashboardPage.worldStateMap).toBeVisible();
  });

  test('@experience-offline renders panels when API requests fail', async ({ page }) => {
    await page.route(/\/api\/characters(\/|\?|$)/, async route => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Simulated failure' }),
      });
    });

    dashboardPage = new DashboardPage(page);
    await dashboardPage.navigateToDashboard({ mockAPIs: true });

    await expect(dashboardPage.worldStateMap).toBeVisible();
    await expect(dashboardPage.analyticsPanel).toBeVisible();
    await checkA11y(page);
  });
});
