import { test, expect } from './fixtures';
import { LandingPage } from './pages/LandingPage';
import { DashboardPage } from './pages/DashboardPage';
import { waitForDashboardReady } from './utils/waitForReady';
import { resetAuthState } from './utils/auth';

/**
 * User Journey E2E Test Suite
 *
 * OpenSpec: complete-e2e-tdd-evolution
 * Spec: e2e-user-flows/spec.md - Complete User Journey Coverage
 *
 * Tests verify:
 * 1. New user journey from landing to dashboard
 * 2. Returning user journey with auth persistence
 * 3. Full user interaction flow
 */

test.describe('Complete User Journey E2E Tests', () => {
  test.describe('Scenario: New user journey', () => {
    /**
     * Given: User is not authenticated
     * When: User visits the application
     * Then: Landing page is displayed
     * When: User clicks "Launch Engine"
     * Then: User is authenticated (guest mode)
     * And: Dashboard is displayed
     * And: Character list is visible
     * And: Activity stream shows connection status
     */
    test('should complete new user journey from landing to dashboard', async ({ page }) => {
      const landingPage = new LandingPage(page);
      const dashboardPage = new DashboardPage(page);

      await test.step('Given: User is not authenticated (fresh session)', async () => {
        await resetAuthState(page);
      });

      await test.step('When: User visits the application', async () => {
        await landingPage.navigateToLanding();
      });

      await test.step('Then: Landing page is displayed', async () => {
        await expect(landingPage.mainTitle).toBeVisible();
        const titleText = await landingPage.getMainTitleText();
        expect(titleText.toUpperCase()).toContain('NARRATIVE ENGINE');
      });

      await test.step('When: User clicks "Launch Engine"', async () => {
        await landingPage.clickLaunchEngine();
      });

      await test.step('Then: User is authenticated (guest mode)', async () => {
        // Should be on dashboard now
        await expect(page).toHaveURL(/.*\/dashboard/);

        // Guest mode indicator should be visible
        await expect(dashboardPage.guestModeChip).toBeVisible();
      });

      await test.step('And: Dashboard is displayed', async () => {
        await expect(dashboardPage.dashboardLayout).toBeVisible();
        await expect(dashboardPage.bentoGrid).toBeVisible();
      });

      await test.step('And: Character list/network is visible', async () => {
        await dashboardPage.switchDashboardTab('Network');
        // Character networks component should be present
        await expect(dashboardPage.characterNetworks).toBeVisible();
      });

      await test.step('And: Activity stream shows connection status', async () => {
        // Real-time activity should show connection
        await expect(dashboardPage.realTimeActivity).toBeVisible();
        await expect(dashboardPage.connectionStatus).toBeVisible();
      });

      // Take final screenshot
      await page.screenshot({
        path: 'test-results/screenshots/new-user-journey-complete.png',
        fullPage: true
      });
    });

    test('should show all dashboard components after authentication', async ({ page }) => {
      const landingPage = new LandingPage(page);
      const dashboardPage = new DashboardPage(page);

      // Complete authentication flow
      await landingPage.navigateToLanding();
      await landingPage.clickLaunchEngine();

      // Verify all major dashboard components
      await expect(dashboardPage.worldStateMap).toBeVisible();
      await expect(dashboardPage.realTimeActivity).toBeVisible();
      await expect(dashboardPage.performanceMetrics).toBeVisible();
      await expect(dashboardPage.turnPipelineStatus).toBeVisible();
      await expect(dashboardPage.quickActions).toBeVisible();
    });
  });

  test.describe('Scenario: Returning user journey', () => {
    /**
     * Given: User has previously authenticated
     * When: User returns to the application
     * Then: Previous auth state is restored
     * And: User can navigate directly to dashboard
     */
    test('should restore returning user session', async ({ page }) => {
      const landingPage = new LandingPage(page);
      const dashboardPage = new DashboardPage(page);

      await test.step('Given: User has previously authenticated', async () => {
        // First, authenticate the user
        await landingPage.navigateToLanding();
        await landingPage.clickLaunchEngine();
        await expect(page).toHaveURL(/.*\/dashboard/);
      });

      await test.step('When: User returns to the application (reload)', async () => {
        await page.reload();
        await waitForDashboardReady(page);
      });

      await test.step('Then: Previous auth state is restored', async () => {
        // Should still be on dashboard
        await expect(page).toHaveURL(/.*\/dashboard/);
        await expect(dashboardPage.dashboardLayout).toBeVisible();
      });

      await test.step('And: User can navigate directly to dashboard', async () => {
        // Navigate away and back
        await page.goto('/');
        await waitForDashboardReady(page);

        // Should be able to go back to dashboard
        await page.goto('/dashboard');
        await waitForDashboardReady(page);

        await expect(page).toHaveURL(/.*\/dashboard/);
      });
    });

    test('should maintain session across multiple page visits', async ({ page }) => {
      const landingPage = new LandingPage(page);
      const dashboardPage = new DashboardPage(page);

      // Initial authentication
      await landingPage.navigateToLanding();
      await landingPage.clickLaunchEngine();

      // Multiple navigations
      for (let i = 0; i < 3; i++) {
        await page.goto('/');
        await waitForDashboardReady(page);
        await page.goto('/dashboard');
        await waitForDashboardReady(page);

        // Should remain authenticated
        await expect(page).toHaveURL(/.*\/dashboard/);
        await expect(dashboardPage.dashboardLayout).toBeVisible();
      }
    });
  });

  test.describe('Dashboard Interaction Flow', () => {
    test('should allow dashboard component interactions', async ({ page }) => {
      const landingPage = new LandingPage(page);
      const dashboardPage = new DashboardPage(page);

      // Setup: Authenticate and navigate to dashboard
      await landingPage.navigateToLanding();
      await landingPage.clickLaunchEngine();
      await dashboardPage.waitForDashboardLoad();

      // Verify quick actions are interactive
      const quickActionCount = await dashboardPage.quickActions
        .locator('[data-testid^="quick-action"]')
        .count();
      expect(quickActionCount).toBeGreaterThan(0);

      // Verify bento grid layout is correct
      const layoutValid = await dashboardPage.validateComponentLayout();
      expect(layoutValid.worldStateMap).toBe(true);
      expect(layoutValid.realTimeActivity).toBe(true);
    });

    test('should display system health status', async ({ page }) => {
      const landingPage = new LandingPage(page);
      const dashboardPage = new DashboardPage(page);

      await landingPage.navigateToLanding();
      await landingPage.clickLaunchEngine();
      await dashboardPage.waitForDashboardLoad();

      // Check system health
      await expect(dashboardPage.systemHealth).toBeVisible();
      await expect(dashboardPage.performanceMetrics).toBeVisible();
    });
  });

  test.describe('User Flow Performance', () => {
    test('should complete user journey within reasonable time', async ({ page }) => {
      const landingPage = new LandingPage(page);
      const dashboardPage = new DashboardPage(page);

      const startTime = Date.now();

      // Full journey
      await landingPage.navigateToLanding();
      await landingPage.clickLaunchEngine();
      await dashboardPage.waitForDashboardLoad();

      const endTime = Date.now();
      const totalTime = endTime - startTime;

      // Should complete within 10 seconds
      expect(totalTime).toBeLessThan(10000);

      console.log(`User journey completed in ${totalTime}ms`);
    });
  });
});
