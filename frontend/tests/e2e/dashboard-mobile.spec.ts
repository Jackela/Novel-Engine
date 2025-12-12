import { test, expect, Page } from '@playwright/test';
import { DashboardPage } from './pages/DashboardPage';

/**
 * Dashboard Mobile Responsive E2E Tests
 *
 * Tests the responsive behavior of DashboardLayout:
 * - Desktop: Three-column layout with collapsible panels
 * - Mobile (<md breakpoint): Tabbed layout with Engine, World, Insights tabs
 *
 * Following CLAUDE.md BDD style: Given/When/Then
 */

// Mobile viewport configuration
const MOBILE_VIEWPORT = { width: 375, height: 667 }; // iPhone SE
const TABLET_VIEWPORT = { width: 768, height: 1024 }; // iPad
const DESKTOP_VIEWPORT = { width: 1440, height: 900 }; // Standard desktop

test.describe('Dashboard Responsive Layout', () => {
  let dashboardPage: DashboardPage;

  test.beforeEach(async ({ page }) => {
    dashboardPage = new DashboardPage(page);
  });

  test.describe('Mobile Layout (@mobile)', () => {
    test.beforeEach(async ({ page }) => {
      await page.setViewportSize(MOBILE_VIEWPORT);
    });

    test('Given mobile viewport, When dashboard loads, Then shows tabbed layout', async ({ page }) => {
      // Given: Mobile viewport is set (done in beforeEach)

      // When: Navigate to dashboard
      await dashboardPage.navigateToDashboard({ mockAPIs: true });

      // Then: Tabbed layout should be visible
      const tabs = page.locator('[role="tablist"]');
      await expect(tabs).toBeVisible({ timeout: 15000 });

      // Verify all three tabs exist
      await expect(page.locator('[id="dashboard-tab-0"]')).toBeVisible(); // Engine
      await expect(page.locator('[id="dashboard-tab-1"]')).toBeVisible(); // World
      await expect(page.locator('[id="dashboard-tab-2"]')).toBeVisible(); // Insights

      // Verify three-column layout is NOT visible
      const sidebarRegion = page.locator('.dashboard-sidebar');
      const asideRegion = page.locator('.dashboard-aside');
      await expect(sidebarRegion).not.toBeVisible();
      await expect(asideRegion).not.toBeVisible();
    });

    test('Given mobile layout, When user taps Engine tab, Then Engine content displays', async ({ page }) => {
      // Given: Mobile dashboard is loaded
      await dashboardPage.navigateToDashboard({ mockAPIs: true });
      await page.waitForSelector('[role="tablist"]', { timeout: 15000 });

      // When: Tap on Engine tab (index 0)
      await page.locator('[id="dashboard-tab-0"]').click();

      // Then: Engine tab panel should be visible
      const enginePanel = page.locator('[id="dashboard-tabpanel-0"]');
      await expect(enginePanel).toBeVisible();
      await expect(enginePanel).not.toHaveAttribute('hidden', '');

      // Other panels should be hidden
      await expect(page.locator('[id="dashboard-tabpanel-1"]')).toHaveAttribute('hidden', '');
      await expect(page.locator('[id="dashboard-tabpanel-2"]')).toHaveAttribute('hidden', '');
    });

    test('Given mobile layout, When user taps Insights tab, Then Insights content displays', async ({ page }) => {
      // Given: Mobile dashboard is loaded
      await dashboardPage.navigateToDashboard({ mockAPIs: true });
      await page.waitForSelector('[role="tablist"]', { timeout: 15000 });

      // When: Tap on Insights tab (index 2)
      await page.locator('[id="dashboard-tab-2"]').click();

      // Then: Insights tab panel should be visible
      const insightsPanel = page.locator('[id="dashboard-tabpanel-2"]');
      await expect(insightsPanel).toBeVisible();
      await expect(insightsPanel).not.toHaveAttribute('hidden', '');

      // Other panels should be hidden
      await expect(page.locator('[id="dashboard-tabpanel-0"]')).toHaveAttribute('hidden', '');
      await expect(page.locator('[id="dashboard-tabpanel-1"]')).toHaveAttribute('hidden', '');
    });

    test('Given mobile layout, Then World tab is selected by default', async ({ page }) => {
      // Given/When: Mobile dashboard is loaded
      await dashboardPage.navigateToDashboard({ mockAPIs: true });
      await page.waitForSelector('[role="tablist"]', { timeout: 15000 });

      // Then: World tab (index 1) should be selected
      const worldTab = page.locator('[id="dashboard-tab-1"]');
      await expect(worldTab).toHaveAttribute('aria-selected', 'true');

      // World panel should be visible
      const worldPanel = page.locator('[id="dashboard-tabpanel-1"]');
      await expect(worldPanel).not.toHaveAttribute('hidden', '');
    });

    test('Given mobile layout, Then tabs have proper accessibility attributes', async ({ page }) => {
      // Given/When: Mobile dashboard is loaded
      await dashboardPage.navigateToDashboard({ mockAPIs: true });
      await page.waitForSelector('[role="tablist"]', { timeout: 15000 });

      // Then: Tablist should have aria-label
      const tablist = page.locator('[role="tablist"]');
      await expect(tablist).toHaveAttribute('aria-label', 'Dashboard sections');

      // Each tab should have aria-controls pointing to its panel
      await expect(page.locator('[id="dashboard-tab-0"]')).toHaveAttribute(
        'aria-controls',
        'dashboard-tabpanel-0'
      );
      await expect(page.locator('[id="dashboard-tab-1"]')).toHaveAttribute(
        'aria-controls',
        'dashboard-tabpanel-1'
      );
      await expect(page.locator('[id="dashboard-tab-2"]')).toHaveAttribute(
        'aria-controls',
        'dashboard-tabpanel-2'
      );
    });

    test('Given mobile layout, When cycling through tabs, Then content updates correctly', async ({ page }) => {
      // Given: Mobile dashboard is loaded
      await dashboardPage.navigateToDashboard({ mockAPIs: true });
      await page.waitForSelector('[role="tablist"]', { timeout: 15000 });

      // When/Then: Cycle through all tabs
      const tabs = ['dashboard-tab-0', 'dashboard-tab-1', 'dashboard-tab-2'];
      const panels = ['dashboard-tabpanel-0', 'dashboard-tabpanel-1', 'dashboard-tabpanel-2'];

      for (let i = 0; i < tabs.length; i++) {
        await page.locator(`[id="${tabs[i]}"]`).click();
        await page.waitForTimeout(100); // Allow animation

        // Current panel visible
        await expect(page.locator(`[id="${panels[i]}"]`)).not.toHaveAttribute('hidden', '');

        // Other panels hidden
        for (let j = 0; j < panels.length; j++) {
          if (i !== j) {
            await expect(page.locator(`[id="${panels[j]}"]`)).toHaveAttribute('hidden', '');
          }
        }
      }
    });
  });

  test.describe('Desktop Layout (@desktop)', () => {
    test.beforeEach(async ({ page }) => {
      await page.setViewportSize(DESKTOP_VIEWPORT);
    });

    test('Given desktop viewport, When dashboard loads, Then shows three-column layout', async ({ page }) => {
      // Given: Desktop viewport is set (done in beforeEach)

      // When: Navigate to dashboard
      await dashboardPage.navigateToDashboard({ mockAPIs: true });

      // Then: Three-column layout should be visible
      const dashboardLayout = page.locator('.dashboard-layout');
      await expect(dashboardLayout).toBeVisible({ timeout: 15000 });

      // Sidebar (Engine) and Aside (Insights) regions should exist
      const sidebarRegion = page.locator('[role="complementary"][aria-label="Engine panel"]');
      const asideRegion = page.locator('[role="complementary"][aria-label="Insights panel"]');
      const mainRegion = page.locator('[role="main"]');

      await expect(sidebarRegion).toBeVisible();
      await expect(asideRegion).toBeVisible();
      await expect(mainRegion).toBeVisible();

      // Tabbed layout should NOT be visible
      const tabs = page.locator('.dashboard-layout--mobile [role="tablist"]');
      await expect(tabs).not.toBeVisible();
    });

    test('Given desktop layout, When sidebar is collapsed, Then Show button appears', async ({ page }) => {
      // Given: Desktop dashboard is loaded
      await dashboardPage.navigateToDashboard({ mockAPIs: true });
      await page.waitForSelector('.dashboard-layout', { timeout: 15000 });

      // When: Click Hide button on sidebar
      const hideButton = page.locator('button[aria-label="Hide engine panel"]');
      await expect(hideButton).toBeVisible();
      await hideButton.click();

      // Then: Show button should appear
      const showButton = page.locator('button[aria-label="Show engine panel"]');
      await expect(showButton).toBeVisible({ timeout: 5000 });
    });

    test('Given collapsed sidebar, When Show button clicked, Then sidebar reopens', async ({ page }) => {
      // Given: Desktop dashboard with collapsed sidebar
      await dashboardPage.navigateToDashboard({ mockAPIs: true });
      await page.waitForSelector('.dashboard-layout', { timeout: 15000 });

      const hideButton = page.locator('button[aria-label="Hide engine panel"]');
      await hideButton.click();

      const showButton = page.locator('button[aria-label="Show engine panel"]');
      await expect(showButton).toBeVisible({ timeout: 5000 });

      // When: Click Show button
      await showButton.click();

      // Then: Sidebar should be visible again
      const sidebarRegion = page.locator('[role="complementary"][aria-label="Engine panel"]');
      await expect(sidebarRegion).toHaveAttribute('data-state', 'open', { timeout: 5000 });
    });
  });

  test.describe('Responsive Breakpoint Transitions', () => {
    test('Given desktop, When resized to mobile, Then layout transitions to tabs', async ({ page }) => {
      // Given: Desktop viewport with three-column layout
      await page.setViewportSize(DESKTOP_VIEWPORT);
      await dashboardPage.navigateToDashboard({ mockAPIs: true });

      // Verify three-column layout
      const dashboardLayout = page.locator('.dashboard-layout:not(.dashboard-layout--mobile)');
      await expect(dashboardLayout).toBeVisible({ timeout: 15000 });

      // When: Resize to mobile viewport
      await page.setViewportSize(MOBILE_VIEWPORT);
      await page.waitForTimeout(500); // Allow for layout reflow

      // Then: Tabbed layout should appear
      const tabs = page.locator('[role="tablist"]');
      await expect(tabs).toBeVisible({ timeout: 10000 });

      // Mobile class should be applied
      const mobileLayout = page.locator('.dashboard-layout--mobile');
      await expect(mobileLayout).toBeVisible();
    });

    test('Given mobile, When resized to desktop, Then layout transitions to three-column', async ({ page }) => {
      // Given: Mobile viewport with tabbed layout
      await page.setViewportSize(MOBILE_VIEWPORT);
      await dashboardPage.navigateToDashboard({ mockAPIs: true });

      // Verify tabbed layout
      const tabs = page.locator('[role="tablist"]');
      await expect(tabs).toBeVisible({ timeout: 15000 });

      // When: Resize to desktop viewport
      await page.setViewportSize(DESKTOP_VIEWPORT);
      await page.waitForTimeout(500); // Allow for layout reflow

      // Then: Three-column layout should appear
      const sidebarRegion = page.locator('[role="complementary"][aria-label="Engine panel"]');
      await expect(sidebarRegion).toBeVisible({ timeout: 10000 });

      // Tabs should not be visible
      const mobileTabs = page.locator('.dashboard-layout--mobile [role="tablist"]');
      await expect(mobileTabs).not.toBeVisible();
    });

    test('Given tablet viewport, Then appropriate layout is shown', async ({ page }) => {
      // Given/When: Tablet viewport
      await page.setViewportSize(TABLET_VIEWPORT);
      await dashboardPage.navigateToDashboard({ mockAPIs: true });
      await page.waitForTimeout(500);

      // Then: Based on MUI md breakpoint (900px), tablet at 768px should show mobile layout
      // MUI breakpoints: xs=0, sm=600, md=900, lg=1200, xl=1536
      const tabs = page.locator('[role="tablist"]');
      await expect(tabs).toBeVisible({ timeout: 15000 });
    });
  });

  test.describe('Keyboard Navigation (@a11y)', () => {
    test('Given mobile layout, When using arrow keys on tabs, Then focus moves between tabs', async ({ page }) => {
      // Given: Mobile dashboard
      await page.setViewportSize(MOBILE_VIEWPORT);
      await dashboardPage.navigateToDashboard({ mockAPIs: true });
      await page.waitForSelector('[role="tablist"]', { timeout: 15000 });

      // When: Focus first tab and press Right arrow
      const firstTab = page.locator('[id="dashboard-tab-0"]');
      await firstTab.focus();
      await page.keyboard.press('ArrowRight');

      // Then: Second tab should be focused
      const secondTab = page.locator('[id="dashboard-tab-1"]');
      await expect(secondTab).toBeFocused();
    });

    test('Given desktop layout, When pressing Cmd+[ shortcut, Then sidebar toggles', async ({ page }) => {
      // Given: Desktop dashboard
      await page.setViewportSize(DESKTOP_VIEWPORT);
      await dashboardPage.navigateToDashboard({ mockAPIs: true });
      await page.waitForSelector('.dashboard-layout', { timeout: 15000 });

      // Verify sidebar is initially open
      const sidebarRegion = page.locator('[role="complementary"][aria-label="Engine panel"]');
      await expect(sidebarRegion).toHaveAttribute('data-state', 'open');

      // When: Press Cmd+[ (Meta+BracketLeft)
      await page.keyboard.press('Meta+[');
      await page.waitForTimeout(300); // Wait for animation

      // Then: Sidebar should be closing/closed
      await expect(sidebarRegion).toHaveAttribute('data-state', 'closing');

      // Show button should appear
      const showButton = page.locator('button[aria-label="Show engine panel"]');
      await expect(showButton).toBeVisible({ timeout: 5000 });
    });
  });
});
