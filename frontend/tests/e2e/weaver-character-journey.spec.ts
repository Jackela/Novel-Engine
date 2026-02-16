import { test, expect } from './fixtures';
import { LandingPage } from './pages/LandingPage';
import { DashboardPage } from './pages/DashboardPage';
import { safeGoto } from './utils/navigation';

test.describe('Weaver Journey - Login to Weaver', () => {
  test('@weaver-smoke Login -> Create Character -> Open Weaver', async ({ page }) => {
    const landingPage = new LandingPage(page);
    const dashboardPage = new DashboardPage(page);

    await landingPage.navigateToLanding();
    await landingPage.clickLaunchEngine();
    await dashboardPage.waitForDashboardLoad();
    await expect(page).toHaveURL(/\/dashboard/);

    await safeGoto(page, '/characters');
    await page.waitForURL('**/characters**', { timeout: 20_000 });
    await expect(page.getByRole('heading', { name: 'Characters' })).toBeVisible({
      timeout: 20_000,
    });

    const newCharacterButton = page.getByRole('button', { name: 'New Character' });
    await expect(newCharacterButton).toBeVisible();
    await newCharacterButton.click();
    await expect(page.getByLabel('Agent ID')).toBeVisible();

    const agentId = `e2e-agent-${Date.now()}`;
    const characterName = 'E2E Voyager';
    await page.getByLabel('Agent ID').fill(agentId);
    await page.getByLabel('Name').fill(characterName);

    await page.getByRole('button', { name: /Create Character/i }).click();
    await expect(page.getByRole('heading', { name: 'Characters' })).toBeVisible();
    await expect(page.getByText(characterName)).toBeVisible();

    await safeGoto(page, '/weaver');
    await expect(page.getByRole('heading', { name: 'Story Weaver' })).toBeVisible();
  });
});
