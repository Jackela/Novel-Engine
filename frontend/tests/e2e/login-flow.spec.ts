import { test, expect } from '@playwright/test';
import { DashboardPage } from './pages/DashboardPage';

test.describe('Login Flow - Demo CTA', () => {
test('@experience-cta @smoke Landing CTA launches dashboard in guest mode', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);

    await page.goto('/');
    const demoCta = page.locator('[data-testid="cta-demo"]');
    await expect(demoCta).toBeVisible();

    await demoCta.focus();
    await page.keyboard.press('Enter');

    await dashboardPage.waitForDashboardLoad();

    await expect(page).toHaveURL(/\/dashboard/);
    await expect(dashboardPage.dashboardLayout).toBeVisible();
    await expect(dashboardPage.guestModeChip).toBeVisible();
    await expect(dashboardPage.guestModeBanner).toBeVisible();
    await expect(dashboardPage.summaryStrip).toBeVisible();
    await expect(dashboardPage.summaryStrip).toContainText(/Command Overview/i);

    const summaryText = await dashboardPage.summaryStrip.innerText();
    expect(summaryText).toMatch(/Run State/i);

    const quickActionButtons = await dashboardPage.quickActions.locator('[data-testid^="quick-action"]').count();
    expect(quickActionButtons).toBeGreaterThan(0);
  });
});
