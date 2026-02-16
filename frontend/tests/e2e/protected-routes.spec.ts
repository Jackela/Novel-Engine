import { test, expect } from './fixtures';
import { LandingPage } from './pages/LandingPage';
import { DashboardPage } from './pages/DashboardPage';
import { waitForDashboardReady, waitForLandingReady } from './utils/waitForReady';
import { prepareGuestSession, resetAuthState } from './utils/auth';
import { safeGoto } from './utils/navigation';

/**
 * Protected Routes E2E Test Suite
 *
 * OpenSpec: complete-e2e-tdd-evolution
 * Spec: e2e-route-coverage/spec.md - Protected Route E2E Coverage
 *
 * Tests verify:
 * 1. Unauthenticated access redirects to landing
 * 2. Authenticated access succeeds
 * 3. Auth state persistence
 */

test.describe('Protected Routes E2E Tests', () => {
  test.describe('Scenario: Unauthenticated access redirects', () => {
    /**
     * Given: User is not authenticated
     * When: User navigates directly to `/dashboard`
     * Then: User is redirected to `/`
     * And: Landing page is displayed
     */
    test('should redirect unauthenticated user from /dashboard to landing', async ({ page }) => {
      const landingPage = new LandingPage(page);

      await test.step('Given: User is not authenticated (fresh session)', async () => {
        await resetAuthState(page);
      });

      await test.step('When: User navigates directly to /dashboard', async () => {
        await safeGoto(page, '/dashboard');
        // Wait for potential redirect to complete
        await waitForLandingReady(page);
      });

      await test.step('Then: User is redirected to /', async () => {
        // Should be on landing page, not dashboard
        await expect(page).toHaveURL(/.*\/$|.*\/$/);
      });

      await test.step('And: Landing page is displayed', async () => {
        await expect(landingPage.mainTitle).toBeVisible();
        await expect(landingPage.launchEngineButton).toBeVisible();
      });
    });

    test('should redirect from other protected routes', async ({ page }) => {
      // Clear auth state
      await resetAuthState(page);

      // Try to access dashboard sub-routes (if any exist)
      await safeGoto(page, '/dashboard/settings');
      await waitForLandingReady(page);

      // Should redirect to landing
      const url = page.url();
      expect(url).not.toContain('/dashboard');
    });
  });

  test.describe('Scenario: Authenticated access succeeds', () => {
    /**
     * Given: User is authenticated (via guest mode or login)
     * When: User navigates to `/dashboard`
     * Then: Dashboard is displayed
     * And: No redirect occurs
     */
    test('should allow authenticated user to access dashboard', async ({ page }) => {
      const landingPage = new LandingPage(page);
      const dashboardPage = new DashboardPage(page);

      await test.step('Given: User authenticates via guest mode', async () => {
        // Navigate to landing page first
        await landingPage.navigateToLanding();

        // Click Launch Engine to authenticate (guest mode)
        await landingPage.clickLaunchEngine();

        // Should now be on dashboard
        await expect(page).toHaveURL(/.*\/dashboard/);
      });

      await test.step('When: User is on /dashboard', async () => {
        // Verify we're still on dashboard
        await expect(page).toHaveURL(/.*\/dashboard/);
      });

      await test.step('Then: Dashboard is displayed', async () => {
        await expect(dashboardPage.dashboardLayout).toBeVisible();
      });

      await test.step('And: No redirect occurred (verify by URL check)', async () => {
        const currentUrl = page.url();
        expect(currentUrl).toContain('/dashboard');
      });
    });

    test('should allow direct dashboard navigation when authenticated', async ({ page }) => {
      const landingPage = new LandingPage(page);
      const dashboardPage = new DashboardPage(page);

      // First authenticate
      await landingPage.navigateToLanding();
      await landingPage.clickLaunchEngine();
      await expect(page).toHaveURL(/.*\/dashboard/);

      // Now navigate away and back directly
      await safeGoto(page, '/');
      await waitForDashboardReady(page);

      // Navigate directly to dashboard - should work since authenticated
      await safeGoto(page, '/dashboard');
      await waitForDashboardReady(page);

      // Should stay on dashboard (not redirect)
      await expect(page).toHaveURL(/.*\/dashboard/);
      await expect(dashboardPage.dashboardLayout).toBeVisible();
    });
  });

  test.describe('Scenario: Auth state persistence', () => {
    /**
     * Given: User has previously authenticated
     * When: User returns to the application
     * Then: Previous auth state is restored
     * And: User can navigate directly to dashboard
     */
    test('should persist auth state across page reloads', async ({ page }) => {
      const landingPage = new LandingPage(page);
      const dashboardPage = new DashboardPage(page);

      await test.step('Given: User authenticates via guest mode', async () => {
        await landingPage.navigateToLanding();
        await landingPage.clickLaunchEngine();
        await expect(page).toHaveURL(/.*\/dashboard/);
      });

      await test.step('When: User reloads the page', async () => {
        await page.reload();
        await waitForDashboardReady(page);
      });

      await test.step('Then: Auth state is preserved', async () => {
        // Should still be on dashboard after reload
        await expect(page).toHaveURL(/.*\/dashboard/);
        await expect(dashboardPage.dashboardLayout).toBeVisible();
      });
    });

    test('should persist auth state in new browser context within session', async ({ browser }) => {
      const context1 = await browser.newContext();
      const page1 = await context1.newPage();
      const landingPage1 = new LandingPage(page1);

      // Authenticate in first page
      await landingPage1.navigateToLanding();
      await landingPage1.clickLaunchEngine();
      await expect(page1).toHaveURL(/.*\/dashboard/);

      // Get storage state
      const storageState = await context1.storageState();

      // Create new context with same storage state
      const context2 = await browser.newContext({ storageState });
      const page2 = await context2.newPage();

      // Try to go directly to dashboard
      await prepareGuestSession(page2);
      await safeGoto(page2, '/dashboard');
      await waitForDashboardReady(page2);

      // Should be able to access dashboard with persisted state
      await expect(page2).toHaveURL(/.*\/dashboard/);

      // Cleanup
      await context1.close();
      await context2.close();
    });
  });

  test.describe('Edge Cases', () => {
    test('should handle rapid navigation attempts', async ({ page }) => {
      const landingPage = new LandingPage(page);

      // Clear auth
      await resetAuthState(page);

      // Rapid navigation attempts to protected route
      const navigate = async (url: string) => {
        await page.goto(url, { waitUntil: 'domcontentloaded' }).catch(() => {});
      };
      await navigate('/dashboard');
      await navigate('/dashboard');
      await navigate('/dashboard');
      await waitForLandingReady(page);

      // Should end up on landing
      await expect(landingPage.mainTitle).toBeVisible();
    });

    test('should handle browser back button from dashboard', async ({ page }) => {
      const landingPage = new LandingPage(page);

      // Authenticate and go to dashboard
      await landingPage.navigateToLanding();
      await landingPage.clickLaunchEngine();
      await expect(page).toHaveURL(/.*\/dashboard/);

      // Press back button
      await page.goBack({ waitUntil: 'domcontentloaded' });
      await waitForDashboardReady(page);

      // Auth redirect should keep user on dashboard
      await expect(page).toHaveURL(/.*\/dashboard/);
    });
  });
});
