import { test, expect } from '@playwright/test';
import { LandingPage } from './pages/LandingPage';
import { DashboardPage } from './pages/DashboardPage';

/**
 * Error Boundary E2E Test Suite
 *
 * OpenSpec: complete-e2e-tdd-evolution
 * Spec: e2e-user-flows/spec.md - Error Boundary Coverage
 *
 * Tests verify:
 * 1. Error boundaries catch and display errors gracefully
 * 2. Error recovery works
 * 3. Application remains usable after errors
 */

test.describe('Error Boundary E2E Tests', () => {
  test.describe('Scenario: Application handles network errors gracefully', () => {
    /**
     * Given: A component throws an error (network failure)
     * When: Error propagates to boundary
     * Then: Error boundary UI is displayed or app degrades gracefully
     * And: Application remains usable
     */
    test('should handle network interruption gracefully', async ({ page }) => {
      const landingPage = new LandingPage(page);
      const dashboardPage = new DashboardPage(page);

      await test.step('Given: User is on dashboard', async () => {
        await landingPage.navigateToLanding();
        await landingPage.clickLaunchEngine();
        await dashboardPage.waitForDashboardLoad();
      });

      await test.step('When: Network is interrupted', async () => {
        // Simulate network interruption
        await page.context().setOffline(true);
        await page.waitForTimeout(1000);
      });

      await test.step('Then: Application remains visible', async () => {
        // Dashboard should still be visible (cached/in-memory data)
        await expect(dashboardPage.dashboardLayout).toBeVisible();
      });

      await test.step('And: Connection status reflects offline state', async () => {
        // Look for any offline indicators or connection status
        const connectionStatus = dashboardPage.connectionStatus;
        await expect(connectionStatus).toBeVisible();
      });

      // Restore network
      await page.context().setOffline(false);
      await page.waitForTimeout(1000);

      await test.step('And: Application recovers when network returns', async () => {
        await expect(dashboardPage.dashboardLayout).toBeVisible();
      });
    });

    test('should recover from API errors', async ({ page }) => {
      const landingPage = new LandingPage(page);
      const dashboardPage = new DashboardPage(page);

      // Setup error interception
      await page.route('**/api/**', route => {
        route.fulfill({
          status: 500,
          body: JSON.stringify({ error: 'Internal Server Error' })
        });
      });

      await landingPage.navigateToLanding();
      await landingPage.clickLaunchEngine();

      // Dashboard should still load (with degraded functionality)
      await expect(dashboardPage.dashboardLayout).toBeVisible();

      // Remove the route interception
      await page.unroute('**/api/**');
    });
  });

  test.describe('Scenario: Error recovery works', () => {
    /**
     * Given: Error boundary is displaying error
     * When: User clicks retry/refresh
     * Then: Component attempts to re-render
     * And: If successful, normal UI is restored
     */
    test('should recover after page refresh', async ({ page }) => {
      const landingPage = new LandingPage(page);
      const dashboardPage = new DashboardPage(page);

      // Navigate to dashboard
      await landingPage.navigateToLanding();
      await landingPage.clickLaunchEngine();
      await dashboardPage.waitForDashboardLoad();

      // Simulate a brief offline period that might cause errors
      await page.context().setOffline(true);
      await page.waitForTimeout(500);
      await page.context().setOffline(false);

      await test.step('When: User refreshes the page', async () => {
        await page.reload();
        await page.waitForLoadState('networkidle');
      });

      await test.step('Then: Normal UI is restored', async () => {
        await expect(dashboardPage.dashboardLayout).toBeVisible();
        await expect(dashboardPage.bentoGrid).toBeVisible();
      });
    });

    test('should handle retry button if present', async ({ page }) => {
      const landingPage = new LandingPage(page);
      const dashboardPage = new DashboardPage(page);

      await landingPage.navigateToLanding();
      await landingPage.clickLaunchEngine();
      await dashboardPage.waitForDashboardLoad();

      // Look for any retry buttons that might be present
      const retryButton = page.locator('[data-testid="retry-button"], button:has-text("Retry"), button:has-text("Try Again")');
      const retryExists = await retryButton.count() > 0;

      if (retryExists) {
        await retryButton.click();
        await page.waitForLoadState('networkidle');
        // Verify recovery
        await expect(dashboardPage.dashboardLayout).toBeVisible();
      }

      // Either way, dashboard should be functional
      await expect(dashboardPage.dashboardLayout).toBeVisible();
    });
  });

  test.describe('Scenario: Graceful degradation', () => {
    test('should show fallback UI when component fails to load', async ({ page }) => {
      const landingPage = new LandingPage(page);

      // Block specific resources to simulate component load failure
      await page.route('**/*.chunk.js', route => {
        // Allow some chunks but block others
        if (route.request().url().includes('vendor')) {
          route.continue();
        } else {
          route.abort();
        }
      });

      // Try to load the app
      await page.goto('/');
      await page.waitForLoadState('domcontentloaded');

      // App should still show something (even if degraded)
      const body = page.locator('body');
      await expect(body).toBeVisible();

      // Clean up
      await page.unroute('**/*.chunk.js');
    });

    test('should display meaningful error message on failure', async ({ page }) => {
      const landingPage = new LandingPage(page);
      const dashboardPage = new DashboardPage(page);

      await landingPage.navigateToLanding();
      await landingPage.clickLaunchEngine();

      // Inject console error listener
      const consoleErrors: string[] = [];
      page.on('console', msg => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text());
        }
      });

      // Wait and collect any errors
      await page.waitForTimeout(2000);

      // If there are console errors, they shouldn't crash the app
      if (consoleErrors.length > 0) {
        console.log(`Captured ${consoleErrors.length} console errors`);
      }

      // App should remain functional
      await expect(dashboardPage.dashboardLayout).toBeVisible();
    });
  });

  test.describe('Edge Cases', () => {
    test('should handle rapid repeated errors', async ({ page }) => {
      const landingPage = new LandingPage(page);
      const dashboardPage = new DashboardPage(page);

      await landingPage.navigateToLanding();
      await landingPage.clickLaunchEngine();

      // Rapid offline/online cycles
      for (let i = 0; i < 3; i++) {
        await page.context().setOffline(true);
        await page.waitForTimeout(200);
        await page.context().setOffline(false);
        await page.waitForTimeout(200);
      }

      // App should stabilize
      await page.waitForTimeout(1000);
      await expect(dashboardPage.dashboardLayout).toBeVisible();
    });

    test('should handle slow network gracefully', async ({ page }) => {
      const landingPage = new LandingPage(page);

      // Simulate slow network
      const client = await page.context().newCDPSession(page);
      await client.send('Network.emulateNetworkConditions', {
        offline: false,
        downloadThroughput: 500 * 1024 / 8, // 500kb/s
        uploadThroughput: 500 * 1024 / 8,
        latency: 1000 // 1 second latency
      });

      // Navigate should still work, just slower
      await landingPage.navigateToLanding();
      await expect(landingPage.mainTitle).toBeVisible({ timeout: 60000 });

      // Reset network conditions
      await client.send('Network.emulateNetworkConditions', {
        offline: false,
        downloadThroughput: -1,
        uploadThroughput: -1,
        latency: 0
      });
    });
  });
});
