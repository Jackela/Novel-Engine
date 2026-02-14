import { test, expect } from './fixtures';
import { LandingPage } from './pages/LandingPage';
import { safeGoto } from './utils/navigation';
import {
  waitForDashboardReady,
  waitForLandingReady,
  waitForLoginReady,
} from './utils/waitForReady';
import { activateGuestSession } from './utils/auth';

/**
 * Navigation & Wildcard Route E2E Test Suite
 *
 * OpenSpec: complete-e2e-tdd-evolution
 * Spec: e2e-route-coverage/spec.md - Wildcard Route E2E Coverage
 *
 * Tests verify:
 * 1. Basic navigation smoke tests (TEST-001)
 * 2. Unknown routes redirect to landing
 * 3. Deep unknown paths redirect
 * 4. Route handling edge cases
 */

test.describe('Basic Navigation Smoke Tests', () => {
  /**
   * TEST-001: Verify landing page loads with correct title
   *
   * Acceptance Criteria:
   * - Visit '/' -> Check title is present
   */
  test('should load landing page with correct title', async ({ page }) => {
    await safeGoto(page, '/');
    await waitForLandingReady(page);

    // Check page title contains app name (document.title = 'Novel Engine')
    const title = await page.title();
    expect(title).toContain('Novel Engine');

    // Verify main heading is visible (h1 contains 'Narrative Engine')
    const mainHeading = page.locator('h1');
    await expect(mainHeading).toBeVisible();
    await expect(mainHeading).toContainText('Narrative Engine');
  });

  /**
   * TEST-001: Verify Weaver navigation via sidebar link
   *
   * Acceptance Criteria:
   * - Click 'Weaver' -> Check URL is '/weaver'
   */
  test('should navigate to Weaver page when clicking Weaver link', async ({ page }) => {
    // Activate guest session to access dashboard with sidebar
    await activateGuestSession(page);

    // Navigate to dashboard first (sidebar is visible there)
    await safeGoto(page, '/dashboard');
    await waitForDashboardReady(page);

    // Find and click the Weaver link in the sidebar
    const sidebar = page.locator('[data-testid="sidebar-navigation"]');
    await expect(sidebar).toBeAttached({ timeout: 5000 });

    const weaverLink = sidebar.locator('a[href="/weaver"]');
    await expect(weaverLink).toBeVisible({ timeout: 5000 });
    await weaverLink.click();

    // Verify URL changed to /weaver
    await expect(page).toHaveURL(/.*\/weaver$/);

    // Verify Weaver page content is visible
    await expect(page.getByRole('heading', { name: 'Story Weaver' })).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Wildcard Route E2E Tests', () => {
  test.describe('Scenario: Unknown routes redirect to landing', () => {
    /**
     * Given: The application is running
     * When: User navigates to `/unknown-route`
     * Then: User is redirected to `/`
     * And: Landing page is displayed
     */
    test('should redirect /unknown-route to landing page', async ({ page }) => {
      const landingPage = new LandingPage(page);

      await test.step('When: User navigates to /unknown-route', async () => {
        await safeGoto(page, '/unknown-route');
        await waitForLandingReady(page);
      });

      await test.step('Then: User is redirected to /', async () => {
        // URL should be landing page
        await expect(page).toHaveURL(/.*\/$/);
      });

      await test.step('And: Landing page is displayed', async () => {
        await expect(landingPage.mainTitle).toBeVisible();
        await expect(landingPage.launchEngineButton).toBeVisible();
      });
    });

    test('should redirect /random-page to landing', async ({ page }) => {
      const landingPage = new LandingPage(page);

      await safeGoto(page, '/random-page');
      await waitForLandingReady(page);

      await expect(landingPage.mainTitle).toBeVisible();
    });

    test('should redirect /settings to landing (nonexistent route)', async ({ page }) => {
      const landingPage = new LandingPage(page);

      await safeGoto(page, '/settings');
      await waitForLandingReady(page);

      await expect(landingPage.mainTitle).toBeVisible();
    });
  });

  test.describe('Scenario: Deep unknown paths redirect', () => {
    /**
     * Given: The application is running
     * When: User navigates to `/some/deep/unknown/path`
     * Then: User is redirected to `/`
     */
    test('should redirect /some/deep/unknown/path to landing', async ({ page }) => {
      const landingPage = new LandingPage(page);

      await test.step('When: User navigates to /some/deep/unknown/path', async () => {
        await safeGoto(page, '/some/deep/unknown/path');
        await waitForLandingReady(page);
      });

      await test.step('Then: User is redirected to /', async () => {
        await expect(landingPage.mainTitle).toBeVisible();
      });
    });

    test('should redirect /a/b/c/d/e to landing', async ({ page }) => {
      const landingPage = new LandingPage(page);

      await safeGoto(page, '/a/b/c/d/e');
      await waitForLandingReady(page);

      await expect(landingPage.mainTitle).toBeVisible();
    });

    test('should redirect paths with query params to landing', async ({ page }) => {
      const landingPage = new LandingPage(page);

      await safeGoto(page, '/unknown?foo=bar&baz=qux');
      await waitForLandingReady(page);

      await expect(landingPage.mainTitle).toBeVisible();
    });

    test('should redirect paths with hash fragments', async ({ page }) => {
      const landingPage = new LandingPage(page);

      await safeGoto(page, '/unknown#section');
      await waitForLandingReady(page);

      await expect(landingPage.mainTitle).toBeVisible();
    });
  });

  test.describe('Edge Cases', () => {
    test('should handle route with special characters', async ({ page }) => {
      const landingPage = new LandingPage(page);

      await safeGoto(page, '/page-with-dash');
      await waitForLandingReady(page);

      await expect(landingPage.mainTitle).toBeVisible();
    });

    test('should handle route with numbers', async ({ page }) => {
      const landingPage = new LandingPage(page);

      await safeGoto(page, '/page123');
      await waitForLandingReady(page);

      await expect(landingPage.mainTitle).toBeVisible();
    });

    test('should handle route with underscore', async ({ page }) => {
      const landingPage = new LandingPage(page);

      await safeGoto(page, '/page_underscore');
      await waitForLandingReady(page);

      await expect(landingPage.mainTitle).toBeVisible();
    });

    test('should handle encoded characters in route', async ({ page }) => {
      const landingPage = new LandingPage(page);

      await safeGoto(page, '/page%20with%20spaces');
      await waitForLandingReady(page);

      await expect(landingPage.mainTitle).toBeVisible();
    });
  });
});

test.describe('Valid Routes Navigation', () => {
  test('should navigate between valid routes correctly', async ({ page }) => {
    const landingPage = new LandingPage(page);

    // Start at landing
    await landingPage.navigateToLanding();
    await expect(landingPage.mainTitle).toBeVisible();

    // Navigate to dashboard via CTA
    await landingPage.clickLaunchEngine();
    await waitForDashboardReady(page);

    // Navigate back to landing (should redirect to dashboard)
    await safeGoto(page, '/');
    await waitForDashboardReady(page);
    await expect(page).toHaveURL(/.*\/dashboard/);
  });

  test('should handle rapid valid route changes', async ({ page }) => {
    const landingPage = new LandingPage(page);

    // Rapid navigation between valid routes
    const navigate = async (url: string) => {
      await safeGoto(page, url);
    };
    await navigate('/');
    await navigate('/login');
    await navigate('/');

    const landingCta = page.locator('[data-testid="cta-launch"]');
    const loginHeading = page.locator('main h1, [role="main"] h1');
    const finalPage = await Promise.race([
      landingCta.waitFor({ state: 'visible', timeout: 10000 }).then(() => 'landing'),
      loginHeading.waitFor({ state: 'visible', timeout: 10000 }).then(() => 'login'),
    ]);

    if (finalPage === 'landing') {
      await waitForLandingReady(page);
      await expect(landingPage.mainTitle).toBeVisible();
    } else {
      await waitForLoginReady(page);
      await expect(loginHeading).toBeVisible();
    }
  });
});
