import { test, expect } from '@playwright/test';
import { LandingPage } from './pages/LandingPage';

/**
 * Navigation & Wildcard Route E2E Test Suite
 *
 * OpenSpec: complete-e2e-tdd-evolution
 * Spec: e2e-route-coverage/spec.md - Wildcard Route E2E Coverage
 *
 * Tests verify:
 * 1. Unknown routes redirect to landing
 * 2. Deep unknown paths redirect
 * 3. Route handling edge cases
 */

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
        await page.goto('/unknown-route');
        await page.waitForLoadState('networkidle');
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

      await page.goto('/random-page');
      await page.waitForLoadState('networkidle');

      await expect(landingPage.mainTitle).toBeVisible();
    });

    test('should redirect /settings to landing (nonexistent route)', async ({ page }) => {
      const landingPage = new LandingPage(page);

      await page.goto('/settings');
      await page.waitForLoadState('networkidle');

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
        await page.goto('/some/deep/unknown/path');
        await page.waitForLoadState('networkidle');
      });

      await test.step('Then: User is redirected to /', async () => {
        await expect(landingPage.mainTitle).toBeVisible();
      });
    });

    test('should redirect /a/b/c/d/e to landing', async ({ page }) => {
      const landingPage = new LandingPage(page);

      await page.goto('/a/b/c/d/e');
      await page.waitForLoadState('networkidle');

      await expect(landingPage.mainTitle).toBeVisible();
    });

    test('should redirect paths with query params to landing', async ({ page }) => {
      const landingPage = new LandingPage(page);

      await page.goto('/unknown?foo=bar&baz=qux');
      await page.waitForLoadState('networkidle');

      await expect(landingPage.mainTitle).toBeVisible();
    });

    test('should redirect paths with hash fragments', async ({ page }) => {
      const landingPage = new LandingPage(page);

      await page.goto('/unknown#section');
      await page.waitForLoadState('networkidle');

      await expect(landingPage.mainTitle).toBeVisible();
    });
  });

  test.describe('Edge Cases', () => {
    test('should handle route with special characters', async ({ page }) => {
      const landingPage = new LandingPage(page);

      await page.goto('/page-with-dash');
      await page.waitForLoadState('networkidle');

      await expect(landingPage.mainTitle).toBeVisible();
    });

    test('should handle route with numbers', async ({ page }) => {
      const landingPage = new LandingPage(page);

      await page.goto('/page123');
      await page.waitForLoadState('networkidle');

      await expect(landingPage.mainTitle).toBeVisible();
    });

    test('should handle route with underscore', async ({ page }) => {
      const landingPage = new LandingPage(page);

      await page.goto('/page_underscore');
      await page.waitForLoadState('networkidle');

      await expect(landingPage.mainTitle).toBeVisible();
    });

    test('should handle encoded characters in route', async ({ page }) => {
      const landingPage = new LandingPage(page);

      await page.goto('/page%20with%20spaces');
      await page.waitForLoadState('networkidle');

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
    await expect(page).toHaveURL(/.*\/dashboard/);

    // Navigate back to landing
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await expect(landingPage.mainTitle).toBeVisible();
  });

  test('should handle rapid valid route changes', async ({ page }) => {
    const landingPage = new LandingPage(page);

    // Rapid navigation between valid routes
    await page.goto('/');
    await page.goto('/login');
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Should end up on landing
    await expect(landingPage.mainTitle).toBeVisible();
  });
});
