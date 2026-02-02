import { test, expect } from './fixtures';
import { DashboardPage } from './pages/DashboardPage';

test.describe('Guest workspace persistence', () => {
  test('guest creates character, runs narrative, and sees it after refresh', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);
    await dashboardPage.navigateToDashboard({ mockAPIs: true });

    const characterName = `Test_Character_${Date.now()}`;
    const characterNamePattern = new RegExp(
      characterName.replace(/_/g, '[_\\s]'),
      'i'
    );

    await test.step('Create a character via UI', async () => {
      await page.goto('/characters');
      await page
        .getByRole('button', { name: /new character|create character/i })
        .click();
      await page.getByLabel('Name').fill(characterName);
      await page.getByLabel('Character Description').fill('A test character for persistence checks.');
      await page.getByTestId('faction-select').click();
      await page.getByRole('option', { name: /Alliance Network/i }).click();
      await page.getByLabel(/Role/i).fill('Explorer');
      await page.getByRole('button', { name: /create character/i }).click();
      await expect(
        page.getByText(characterNamePattern, { exact: false })
      ).toBeVisible();
    });

    await test.step('Start a run and see narrative output', async () => {
      await page.goto('/dashboard');
      await dashboardPage.playButton.first().click();
      await expect(dashboardPage.liveIndicator).toBeVisible();
      await page.getByRole('tab', { name: /Narrative/i }).click();
      await expect(page.getByText(/Narrative generated for/i)).toBeVisible();
    });

    await test.step('Refresh and confirm character persists', async () => {
      await page.reload();
      await page.goto('/characters');
      await expect(
        page.getByText(characterNamePattern, { exact: false })
      ).toBeVisible();
    });
  });
});
