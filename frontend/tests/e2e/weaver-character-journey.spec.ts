import { test, expect } from './fixtures';
import { LandingPage } from './pages/LandingPage';
import { DashboardPage } from './pages/DashboardPage';

test.describe('Weaver Journey - Login to Weaver', () => {
  test('@weaver-smoke Login -> Create Character -> Open Weaver', async ({ page }) => {
    const landingPage = new LandingPage(page);
    const dashboardPage = new DashboardPage(page);

    await landingPage.navigateToLanding();
    await landingPage.clickLaunchEngine();
    await dashboardPage.waitForDashboardLoad();
    await expect(page).toHaveURL(/\/dashboard/);

    await page.goto('/characters', { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'Characters' })).toBeVisible();

    await page.getByRole('button', { name: 'New Character' }).click();
    await expect(page.getByRole('heading', { name: /Create Character/i })).toBeVisible();

    const agentId = `e2e-agent-${Date.now()}`;
    const characterName = 'E2E Voyager';
    await page.getByLabel('Agent ID').fill(agentId);
    await page.getByLabel('Name').fill(characterName);

    await page.getByRole('button', { name: /Create Character/i }).click();
    await expect(page.getByRole('heading', { name: 'Characters' })).toBeVisible();
    await expect(page.getByText(characterName)).toBeVisible();

    await page.goto('/weaver', { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'Story Weaver' })).toBeVisible();
  });
});
