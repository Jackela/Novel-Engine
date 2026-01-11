import { test, expect, Page } from '@playwright/test';

// Test configuration
const BASE_URL = 'http://localhost:3000';
const TEST_TIMEOUT = 30000;

test.describe('Character Creation E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the application
    await page.goto(BASE_URL);

    // Wait for the page to load
    await page.waitForLoadState('networkidle');

    // Check if we need to handle the landing page
    const launchButton = page.locator('button:has-text("Launch Engine")');
    if (await launchButton.isVisible()) {
      await launchButton.click();
      await page.waitForURL('**/dashboard');
    }
  });

  test('should create a new character successfully', async ({ page }) => {
    // Click the "New Operative" or create character button
    const createButton = page.locator('button:has-text("New Operative"), button:has-text("Create Character")').first();
    await createButton.click();

    // Wait for the dialog/modal to appear
    await expect(page.locator('role=dialog')).toBeVisible();

    // Fill in the character form
    await page.fill('input[name="name"], input[placeholder*="name" i]', 'E2E Test Agent Alpha');
    await page.fill('input[name="faction"], input[placeholder*="faction" i]', 'Test Faction');
    await page.fill('input[name="role"], input[placeholder*="role" i]', 'Test Role');
    await page.fill('textarea[name="description"], textarea[placeholder*="description" i]', 'E2E test character created by automated testing');

    // Set stats (if visible)
    const strengthInput = page.locator('input[name="strength"], input[placeholder*="strength" i]');
    if (await strengthInput.isVisible()) {
      await strengthInput.fill('7');
    }

    const agilityInput = page.locator('input[name="agility"], input[placeholder*="agility" i]');
    if (await agilityInput.isVisible()) {
      await agilityInput.fill('8');
    }

    // Submit the form
    const submitButton = page.locator('button[type="submit"], button:has-text("Create"), button:has-text("Submit")').first();
    await submitButton.click();

    // Wait for the dialog to close
    await expect(page.locator('role=dialog')).not.toBeVisible({ timeout: 5000 });

    // Verify the character appears in the list
    await expect(page.locator('text=E2E Test Agent Alpha')).toBeVisible({ timeout: 5000 });

    // Verify no error messages
    const errorAlert = page.locator('[role="alert"]:has-text("error"), .error-message');
    await expect(errorAlert).not.toBeVisible();
  });

  test('should show validation error for invalid input', async ({ page }) => {
    // Click create button
    const createButton = page.locator('button:has-text("New Operative"), button:has-text("Create Character")').first();
    await createButton.click();

    // Wait for dialog
    await expect(page.locator('role=dialog')).toBeVisible();

    // Fill with invalid data (name too short)
    await page.fill('input[name="name"], input[placeholder*="name" i]', 'A');

    // Try to submit
    const submitButton = page.locator('button[type="submit"], button:has-text("Create"), button:has-text("Submit")').first();
    await submitButton.click();

    // Verify validation error is shown
    const errorMessage = page.locator('text=/must be at least/i, text=/too short/i, text=/invalid/i').first();
    await expect(errorMessage).toBeVisible({ timeout: 3000 });

    // Verify dialog is still open
    await expect(page.locator('role=dialog')).toBeVisible();
  });

  test('should allow canceling character creation', async ({ page }) => {
    // Click create button
    const createButton = page.locator('button:has-text("New Operative"), button:has-text("Create Character")').first();
    await createButton.click();

    // Wait for dialog
    await expect(page.locator('role=dialog')).toBeVisible();

    // Fill partial data
    await page.fill('input[name="name"], input[placeholder*="name" i]', 'Canceled Character');

    // Click cancel/close
    const cancelButton = page.locator('button:has-text("Cancel"), button[aria-label="Close"], button[aria-label="close"]').first();
    await cancelButton.click();

    // Verify dialog closed
    await expect(page.locator('role=dialog')).not.toBeVisible({ timeout: 3000 });

    // Verify character was not created
    await expect(page.locator('text=Canceled Character')).not.toBeVisible();
  });

  test('should persist created character after page reload', async ({ page }) => {
    // Create a character
    const createButton = page.locator('button:has-text("New Operative"), button:has-text("Create Character")').first();
    await createButton.click();

    await expect(page.locator('role=dialog')).toBeVisible();

    const characterName = `Persistent Character ${Date.now()}`;
    await page.fill('input[name="name"], input[placeholder*="name" i]', characterName);
    await page.fill('input[name="faction"], input[placeholder*="faction" i]', 'Test Faction');
    await page.fill('input[name="role"], input[placeholder*="role" i]', 'Test Role');
    await page.fill('textarea[name="description"], textarea[placeholder*="description" i]', 'Testing persistence');

    const submitButton = page.locator('button[type="submit"], button:has-text("Create"), button:has-text("Submit")').first();
    await submitButton.click();

    await expect(page.locator('role=dialog')).not.toBeVisible({ timeout: 5000 });
    await expect(page.locator(`text=${characterName}`)).toBeVisible();

    // Reload the page
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Verify character still exists
    await expect(page.locator(`text=${characterName}`)).toBeVisible({ timeout: 5000 });
  });

  test('should display character details correctly', async ({ page }) => {
    // Create a character with specific details
    const createButton = page.locator('button:has-text("New Operative"), button:has-text("Create Character")').first();
    await createButton.click();

    await expect(page.locator('role=dialog')).toBeVisible();

    const testData = {
      name: 'Detail Test Character',
      faction: 'Alpha Faction',
      role: 'Specialist',
      description: 'Testing detail display functionality',
    };

    await page.fill('input[name="name"], input[placeholder*="name" i]', testData.name);
    await page.fill('input[name="faction"], input[placeholder*="faction" i]', testData.faction);
    await page.fill('input[name="role"], input[placeholder*="role" i]', testData.role);
    await page.fill('textarea[name="description"], textarea[placeholder*="description" i]', testData.description);

    const submitButton = page.locator('button[type="submit"], button:has-text("Create"), button:has-text("Submit")').first();
    await submitButton.click();

    await expect(page.locator('role=dialog')).not.toBeVisible({ timeout: 5000 });

    // Click on the character to view details
    await page.locator(`text=${testData.name}`).click();

    // Verify all details are displayed correctly
    await expect(page.locator(`text=${testData.faction}`)).toBeVisible();
    await expect(page.locator(`text=${testData.role}`)).toBeVisible();
    await expect(page.locator(`text=${testData.description}`)).toBeVisible();
  });

  test('should handle network errors gracefully', async ({ page, context }) => {
    // Simulate offline mode
    await context.setOffline(true);

    // Try to create a character
    const createButton = page.locator('button:has-text("New Operative"), button:has-text("Create Character")').first();
    await createButton.click();

    await expect(page.locator('role=dialog')).toBeVisible();

    await page.fill('input[name="name"], input[placeholder*="name" i]', 'Offline Test Character');
    await page.fill('input[name="faction"], input[placeholder*="faction" i]', 'Test Faction');
    await page.fill('input[name="role"], input[placeholder*="role" i]', 'Test Role');

    const submitButton = page.locator('button[type="submit"], button:has-text("Create"), button:has-text("Submit")').first();
    await submitButton.click();

    // Verify error message is shown
    const errorMessage = page.locator('text=/network error/i, text=/unable to connect/i, text=/connection failed/i').first();
    await expect(errorMessage).toBeVisible({ timeout: 5000 });

    // Re-enable network
    await context.setOffline(false);
  });
});

test.describe('Character List Display', () => {
  test('should show fallback characters when API fails', async ({ page, context }) => {
    // Block API requests
    await context.route('**/api/characters*', route => route.abort());

    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Should show fallback/demo characters
    const characterCards = page.locator('[data-testid="character-card"], .character-card');
    await expect(characterCards.first()).toBeVisible({ timeout: 5000 });
  });

  test('should display empty state when no characters exist', async ({ page, context }) => {
    // Mock empty response
    await context.route('**/api/characters*', route =>
      route.fulfill({
        status: 200,
        body: JSON.stringify([]),
        headers: { 'Content-Type': 'application/json' }
      })
    );

    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Should show empty state message
    const emptyMessage = page.locator('text=/no characters/i, text=/create your first/i, text=/get started/i').first();
    await expect(emptyMessage).toBeVisible({ timeout: 5000 });
  });
});
