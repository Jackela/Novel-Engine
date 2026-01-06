import { test, expect } from './fixtures';
import { DashboardPage } from './pages/DashboardPage';

/**
 * Dashboard Responsive Layout E2E Tests
 *
 * Validates the CommandLayout responsiveness:
 * - Mobile: floating menu button + drawer navigation
 * - Desktop: fixed sidebar navigation
 */

const MOBILE_VIEWPORT = { width: 375, height: 667 };
const TABLET_VIEWPORT = { width: 768, height: 1024 };
const DESKTOP_VIEWPORT = { width: 1440, height: 900 };

test.describe('Dashboard Responsive Layout', () => {
  let dashboardPage: DashboardPage;

  test.beforeEach(async ({ page }) => {
    dashboardPage = new DashboardPage(page);
  });

  test.describe('Mobile Layout (@mobile)', () => {
    test.beforeEach(async ({ page }) => {
      await page.setViewportSize(MOBILE_VIEWPORT);
    });

    test('Given mobile viewport, When dashboard loads, Then shows menu toggle and drawer navigation', async ({ page }) => {
      await dashboardPage.navigateToDashboard({ mockAPIs: true });

      const menuToggle = page.locator('[data-testid="mobile-menu-toggle"]');
      await expect(menuToggle).toBeVisible({ timeout: 15000 });

      const drawer = page.locator('[data-testid="sidebar-drawer"]');
      await expect(drawer).toBeHidden();

      await menuToggle.click();
      await expect(drawer).toBeVisible();
      await expect(page.locator('[data-testid="sidebar-navigation"]')).toBeVisible();
    });

    test('Given mobile layout, When using keyboard on menu toggle, Then drawer opens', async ({ page }) => {
      await dashboardPage.navigateToDashboard({ mockAPIs: true });

      const menuToggle = page.locator('[data-testid="mobile-menu-toggle"]');
      await menuToggle.focus();
      await page.keyboard.press('Enter');

      const drawer = page.locator('[data-testid="sidebar-drawer"]');
      await expect(drawer).toBeVisible();
    });
  });

  test.describe('Desktop Layout (@desktop)', () => {
    test.beforeEach(async ({ page }) => {
      await page.setViewportSize(DESKTOP_VIEWPORT);
    });

    test('Given desktop viewport, When dashboard loads, Then shows fixed sidebar navigation', async ({ page }) => {
      await dashboardPage.navigateToDashboard({ mockAPIs: true });

      const sidebar = page.locator('[data-testid="sidebar-desktop"]');
      await expect(sidebar).toBeVisible({ timeout: 15000 });
      await expect(page.locator('[data-testid="sidebar-navigation"]')).toBeVisible();

      const menuToggle = page.locator('[data-testid="mobile-menu-toggle"]');
      await expect(menuToggle).toBeHidden();
    });

    test('Given desktop layout, When sidebar is expanded, Then collapse button appears', async ({ page }) => {
      await dashboardPage.navigateToDashboard({ mockAPIs: true });

      const expandButton = page.locator('button[aria-label="Expand Sidebar"]');
      await expect(expandButton).toBeVisible();
      await expandButton.click();

      const collapseButton = page.locator('button[aria-label="Collapse Sidebar"]');
      await expect(collapseButton).toBeVisible();
    });
  });

  test.describe('Responsive Breakpoint Transitions', () => {
    test('Given desktop, When resized to mobile, Then mobile menu toggle appears', async ({ page }) => {
      await page.setViewportSize(DESKTOP_VIEWPORT);
      await dashboardPage.navigateToDashboard({ mockAPIs: true });

      const desktopSidebar = page.locator('[data-testid="sidebar-desktop"]');
      await expect(desktopSidebar).toBeVisible({ timeout: 15000 });

      await page.setViewportSize(MOBILE_VIEWPORT);
      await page.waitForTimeout(300);

      const menuToggle = page.locator('[data-testid="mobile-menu-toggle"]');
      await expect(menuToggle).toBeVisible();
    });

    test('Given mobile, When resized to desktop, Then fixed sidebar appears', async ({ page }) => {
      await page.setViewportSize(MOBILE_VIEWPORT);
      await dashboardPage.navigateToDashboard({ mockAPIs: true });

      const menuToggle = page.locator('[data-testid="mobile-menu-toggle"]');
      await expect(menuToggle).toBeVisible({ timeout: 15000 });

      await page.setViewportSize(DESKTOP_VIEWPORT);
      await page.waitForTimeout(300);

      const desktopSidebar = page.locator('[data-testid="sidebar-desktop"]');
      await expect(desktopSidebar).toBeVisible();
    });

    test('Given tablet viewport, Then mobile navigation is used', async ({ page }) => {
      await page.setViewportSize(TABLET_VIEWPORT);
      await dashboardPage.navigateToDashboard({ mockAPIs: true });

      const menuToggle = page.locator('[data-testid="mobile-menu-toggle"]');
      await expect(menuToggle).toBeVisible({ timeout: 15000 });
    });
  });
});
