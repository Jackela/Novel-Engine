import { test, expect } from '@playwright/test';
import { DashboardPage } from './pages/DashboardPage';

test.describe('Dashboard Interactions', () => {
  let dashboardPage: DashboardPage;

  test.beforeEach(async ({ page }) => {
    dashboardPage = new DashboardPage(page);
    await dashboardPage.navigateToDashboard({ mockAPIs: true });
  });

  test('Quick Actions drive pipeline state', async () => {
    await dashboardPage.playButton.first().click();

    const processingMarker = dashboardPage.turnPipelineStatus.locator(
      '[data-testid="pipeline-stage-marker"][data-status="processing"]',
    );
    await processingMarker.first().waitFor({ state: 'attached', timeout: 10000 });
    await expect(dashboardPage.liveIndicator).toBeVisible();

    await dashboardPage.pauseButton.first().click();
    await expect(
      dashboardPage.turnPipelineStatus.locator('[data-testid="pipeline-run-state"]'),
    ).toHaveText(/Paused/i);

    await dashboardPage.refreshButton.first().click();
    await dashboardPage.page.waitForTimeout(1000);
    await expect(dashboardPage.quickActions).toBeVisible();
  });

  test('World map selection reveals character details', async () => {
    const worldMap = dashboardPage.worldStateMap;
    const location = worldMap.locator('[data-location="merchant-quarter"]');

    await location.click();
    await dashboardPage.page.waitForTimeout(200);
    expect(await location.locator('li').count()).toBeGreaterThan(0);

    await location.click();
    await dashboardPage.page.waitForTimeout(200);
    expect(await location.locator('li').count()).toBe(0);
  });

  test('@experience-offline @smoke Connection indicator reflects offline recovery', async () => {
    const indicator = dashboardPage.connectionStatus.first();
    const liveLabel = dashboardPage.liveIndicator;

    await expect(indicator).toHaveAttribute('data-status', /live|online|standby|idle/);

    await dashboardPage.page.context().setOffline(true);
    await expect(indicator).toHaveAttribute('data-status', 'offline');
    await expect(liveLabel).toHaveText(/offline/i);

    await dashboardPage.page.waitForTimeout(500);

    await dashboardPage.page.context().setOffline(false);
    await expect(indicator).toHaveAttribute('data-status', /live|online|standby|idle/);
    await expect(liveLabel).not.toHaveText(/offline/i);
  });

  test('@experience-offline renders fallback dataset when characters API fails', async ({ page }) => {
    // Force characters API to fail so fallback dataset renders
    dashboardPage = new DashboardPage(page);
    await dashboardPage.navigateToDashboard({ mockAPIs: true, failCharacters: true });

    await dashboardPage.waitForDashboardLoad();
    await expect(dashboardPage.worldStateMap).toBeVisible();
    await expect(page.getByTestId('fallback-dataset-alert').first()).toBeVisible();
  });
});
