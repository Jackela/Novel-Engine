import { test, expect } from '@playwright/test';
import { DashboardPage } from './pages/DashboardPage';
import { LandingPage } from './pages/LandingPage';

/**
 * Login Flow E2E Test Suite
 *
 * OpenSpec: complete-e2e-tdd-evolution
 * Spec: e2e-route-coverage/spec.md - Login Page E2E Coverage
 *
 * Tests verify:
 * 1. Guest mode launch from landing page
 * 2. Login placeholder page renders
 * 3. Login page accessibility
 */

test.describe('Login Flow - Launch Engine CTA', () => {
  test('@experience-cta Landing CTA launches dashboard in guest mode', async ({ page }) => {
    const landingPage = new LandingPage(page);
    const dashboardPage = new DashboardPage(page);

    // Navigate to landing page
    await landingPage.navigateToLanding();

    // Find and verify the Launch Engine button
    await expect(landingPage.launchEngineButton).toBeVisible();

    // Click using keyboard for accessibility
    await landingPage.launchEngineButton.focus();
    await page.keyboard.press('Enter');

    // Wait for dashboard to load
    await dashboardPage.waitForDashboardLoad();

    // Verify navigation
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(dashboardPage.dashboardLayout).toBeVisible();

    // Verify guest mode indicators
    await expect(dashboardPage.guestModeChip).toBeVisible();
    await expect(dashboardPage.guestModeBanner).toBeVisible();

    // Verify summary strip shows expected content
    await expect(dashboardPage.summaryStrip).toBeVisible();
    await expect(dashboardPage.summaryStrip).toContainText(/Command Overview/i);

    const summaryText = await dashboardPage.summaryStrip.innerText();
    expect(summaryText).toMatch(/Run State/i);

    // Verify quick actions are available
    const quickActionButtons = await dashboardPage.quickActions.locator('[data-testid^="quick-action"]').count();
    expect(quickActionButtons).toBeGreaterThan(0);
  });

  test('Launch Engine button click navigates to dashboard', async ({ page }) => {
    const landingPage = new LandingPage(page);
    const dashboardPage = new DashboardPage(page);

    await landingPage.navigateToLanding();
    await landingPage.clickLaunchEngine();

    await expect(page).toHaveURL(/\/dashboard/);
    await expect(dashboardPage.dashboardLayout).toBeVisible();
  });
});

test.describe('Login Page - Placeholder', () => {
  /**
   * Scenario: Login placeholder renders
   * Given: The application is running
   * When: User navigates to `/login`
   * Then: Login placeholder message is displayed
   */
  test('should display login placeholder page', async ({ page }) => {
    await test.step('When: User navigates to /login', async () => {
      await page.goto('/login');
      await page.waitForLoadState('networkidle');
    });

    await test.step('Then: Login placeholder message is displayed', async () => {
      // Look for login-related content
      const content = await page.textContent('body');
      expect(content).toBeTruthy();

      // The page should have some visible content (placeholder)
      const mainContent = page.locator('main, #root, [role="main"]');
      await expect(mainContent).toBeVisible();
    });
  });

  test('should have accessible login placeholder', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    // Check basic accessibility - page should have content
    const title = await page.title();
    expect(title).toBeTruthy();

    // Page should be interactive (not blank)
    const bodyContent = await page.locator('body').textContent();
    expect(bodyContent?.trim().length).toBeGreaterThan(0);
  });

  test('should allow navigation from login page', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    // Should be able to navigate back to landing
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const landingPage = new LandingPage(page);
    await expect(landingPage.mainTitle).toBeVisible();
  });
});

test.describe('Login Flow - Keyboard Accessibility', () => {
  test('should support keyboard-only navigation for launch', async ({ page }) => {
    const landingPage = new LandingPage(page);
    const dashboardPage = new DashboardPage(page);

    await landingPage.navigateToLanding();

    // Tab to the Launch Engine button
    await page.keyboard.press('Tab');

    // Keep tabbing until we find the button (max 10 tabs)
    let foundButton = false;
    for (let i = 0; i < 10; i++) {
      const focusedElement = await page.evaluate(() => document.activeElement?.tagName);
      if (focusedElement === 'BUTTON') {
        const buttonText = await page.evaluate(() => document.activeElement?.textContent);
        if (buttonText?.toLowerCase().includes('launch')) {
          foundButton = true;
          break;
        }
      }
      await page.keyboard.press('Tab');
    }

    expect(foundButton).toBe(true);

    // Press Enter to activate
    await page.keyboard.press('Enter');

    // Verify navigation
    await dashboardPage.waitForDashboardLoad();
    await expect(page).toHaveURL(/\/dashboard/);
  });
});
