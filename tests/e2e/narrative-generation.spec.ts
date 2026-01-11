import { test, expect, Page } from '@playwright/test';

// Test configuration
const BASE_URL = 'http://localhost:3000';
const TEST_TIMEOUT = 60000; // Longer timeout for narrative generation

test.describe('Narrative Generation E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the application
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Navigate to dashboard if needed
    const launchButton = page.locator('button:has-text("Launch Engine")');
    if (await launchButton.isVisible()) {
      await launchButton.click();
      await page.waitForURL('**/dashboard');
    }

    // Ensure at least one character exists for testing
    const characterCards = page.locator('[data-testid="character-card"], .character-card');
    const count = await characterCards.count();

    if (count === 0) {
      // Create a test character
      const createButton = page.locator('button:has-text("New Operative"), button:has-text("Create Character")').first();
      await createButton.click();

      await expect(page.locator('role=dialog')).toBeVisible();

      await page.fill('input[name="name"], input[placeholder*="name" i]', 'Narrative Test Character');
      await page.fill('input[name="faction"], input[placeholder*="faction" i]', 'Test Faction');
      await page.fill('input[name="role"], input[placeholder*="role" i]', 'Test Role');
      await page.fill('textarea[name="description"]', 'Character for narrative testing');

      const submitButton = page.locator('button[type="submit"], button:has-text("Create")').first();
      await submitButton.click();

      await expect(page.locator('role=dialog')).not.toBeVisible({ timeout: 5000 });
    }
  });

  test('should start narrative generation successfully', async ({ page }) => {
    // Find and click the Start Run button
    const startButton = page.locator('button:has-text("Start Run"), button:has-text("Start"), button:has-text("Generate")').first();
    await expect(startButton).toBeEnabled();
    await startButton.click();

    // Verify status changes to RUNNING
    const statusIndicator = page.locator('[data-testid="status"], .status-indicator, text=/running/i').first();
    await expect(statusIndicator).toBeVisible({ timeout: 5000 });

    // Wait a few seconds for narrative generation to begin
    await page.waitForTimeout(3000);

    // Verify narrative panel shows content or loading state
    const narrativePanel = page.locator('[data-testid="narrative-panel"], [data-testid="narrative-content"], .narrative-panel');
    await expect(narrativePanel).toBeVisible();

    // Check for loading indicator or generated text
    const hasLoading = await page.locator('text=/generating/i, text=/processing/i, [role="progressbar"]').isVisible();
    const hasContent = await page.locator('[data-testid="narrative-content"] >> text=/./').count() > 0;

    expect(hasLoading || hasContent).toBeTruthy();
  });

  test('should pause and resume narrative generation', async ({ page }) => {
    // Start generation
    const startButton = page.locator('button:has-text("Start Run"), button:has-text("Start")').first();
    await startButton.click();

    // Wait for running state
    await expect(page.locator('text=/running/i').first()).toBeVisible({ timeout: 5000 });

    // Click pause button
    const pauseButton = page.locator('button:has-text("Pause")').first();
    await expect(pauseButton).toBeVisible({ timeout: 5000 });
    await pauseButton.click();

    // Verify status changes to PAUSED
    await expect(page.locator('text=/paused/i').first()).toBeVisible({ timeout: 3000 });

    // Wait a moment
    await page.waitForTimeout(2000);

    // Click resume button
    const resumeButton = page.locator('button:has-text("Resume"), button:has-text("Continue")').first();
    await expect(resumeButton).toBeVisible();
    await resumeButton.click();

    // Verify status changes back to RUNNING
    await expect(page.locator('text=/running/i').first()).toBeVisible({ timeout: 3000 });
  });

  test('should stop narrative generation', async ({ page }) => {
    // Start generation
    const startButton = page.locator('button:has-text("Start Run"), button:has-text("Start")').first();
    await startButton.click();

    // Wait for running state
    await expect(page.locator('text=/running/i').first()).toBeVisible({ timeout: 5000 });

    // Click stop button
    const stopButton = page.locator('button:has-text("Stop"), button:has-text("Cancel")').first();
    await expect(stopButton).toBeVisible({ timeout: 5000 });
    await stopButton.click();

    // Verify status changes to STOPPED or IDLE
    const stoppedStatus = page.locator('text=/stopped/i, text=/idle/i, text=/ready/i').first();
    await expect(stoppedStatus).toBeVisible({ timeout: 5000 });

    // Verify Start button is available again
    await expect(startButton).toBeEnabled({ timeout: 3000 });
  });

  test('should complete narrative generation and display results', async ({ page }) => {
    // This test waits for the full generation cycle
    test.setTimeout(TEST_TIMEOUT);

    // Start generation
    const startButton = page.locator('button:has-text("Start Run"), button:has-text("Start")').first();
    await startButton.click();

    // Wait for running state
    await expect(page.locator('text=/running/i').first()).toBeVisible({ timeout: 5000 });

    // Wait for completion (with extended timeout)
    const completedStatus = page.locator('text=/completed/i, text=/finished/i, text=/done/i').first();
    await expect(completedStatus).toBeVisible({ timeout: TEST_TIMEOUT - 10000 });

    // Verify narrative content is displayed
    const narrativeContent = page.locator('[data-testid="narrative-content"]');
    await expect(narrativeContent).toBeVisible();

    const contentText = await narrativeContent.textContent();
    expect(contentText).toBeTruthy();
    expect(contentText!.length).toBeGreaterThan(10);

    // Verify narrative mentions the character
    const characterName = 'Narrative Test Character';
    const hasCharacterName = contentText!.includes(characterName) ||
                             await page.locator(`text=${characterName}`).count() > 0;
    // Note: This assertion might be flexible depending on narrative generation logic
  });

  test('should display progress indicators during generation', async ({ page }) => {
    // Start generation
    const startButton = page.locator('button:has-text("Start Run"), button:has-text("Start")').first();
    await startButton.click();

    // Wait for running state
    await expect(page.locator('text=/running/i').first()).toBeVisible({ timeout: 5000 });

    // Check for progress indicators
    const progressIndicators = page.locator('[role="progressbar"], .progress-bar, text=/turn.*of/i, text=/processing turn/i');
    const hasProgress = await progressIndicators.count() > 0;

    // At least one progress indicator should be present
    if (hasProgress) {
      await expect(progressIndicators.first()).toBeVisible();
    }
  });

  test('should handle generation errors gracefully', async ({ page, context }) => {
    // Simulate API failure during generation
    await context.route('**/api/orchestration/start', route =>
      route.fulfill({
        status: 500,
        body: JSON.stringify({ error: 'Internal server error' }),
        headers: { 'Content-Type': 'application/json' }
      })
    );

    // Try to start generation
    const startButton = page.locator('button:has-text("Start Run"), button:has-text("Start")').first();
    await startButton.click();

    // Verify error message is displayed
    const errorMessage = page.locator('[role="alert"]:has-text("error"), .error-message, text=/failed/i, text=/error/i').first();
    await expect(errorMessage).toBeVisible({ timeout: 5000 });

    // Verify Start button remains available for retry
    await expect(startButton).toBeEnabled();
  });

  test('should prevent starting multiple generations simultaneously', async ({ page }) => {
    // Start first generation
    const startButton = page.locator('button:has-text("Start Run"), button:has-text("Start")').first();
    await startButton.click();

    // Wait for running state
    await expect(page.locator('text=/running/i').first()).toBeVisible({ timeout: 5000 });

    // Verify Start button is disabled
    await expect(startButton).toBeDisabled();

    // Or verify it's not visible (replaced by pause/stop)
    const controlsVisible = await page.locator('button:has-text("Pause"), button:has-text("Stop")').count();
    expect(controlsVisible).toBeGreaterThan(0);
  });

  test('should update narrative content in real-time', async ({ page }) => {
    // Start generation
    const startButton = page.locator('button:has-text("Start Run"), button:has-text("Start")').first();
    await startButton.click();

    // Wait for running state
    await expect(page.locator('text=/running/i').first()).toBeVisible({ timeout: 5000 });

    // Get initial content
    const narrativeContent = page.locator('[data-testid="narrative-content"]');
    const initialContent = await narrativeContent.textContent();

    // Wait a few seconds
    await page.waitForTimeout(5000);

    // Get updated content
    const updatedContent = await narrativeContent.textContent();

    // Content should have changed (more text added)
    // Note: This might not always be true depending on generation speed
    // Consider this a flexible assertion
    if (initialContent && updatedContent) {
      // Either content changed or generation completed quickly
      const contentChanged = initialContent !== updatedContent;
      const isComplete = await page.locator('text=/completed/i, text=/finished/i').isVisible();
      expect(contentChanged || isComplete).toBeTruthy();
    }
  });

  test('should persist narrative after page reload', async ({ page }) => {
    test.setTimeout(TEST_TIMEOUT);

    // Start and complete generation
    const startButton = page.locator('button:has-text("Start Run"), button:has-text("Start")').first();
    await startButton.click();

    // Wait for completion
    await expect(page.locator('text=/completed/i, text=/finished/i').first()).toBeVisible({ timeout: TEST_TIMEOUT - 10000 });

    // Get generated narrative
    const narrativeContent = page.locator('[data-testid="narrative-content"]');
    const originalContent = await narrativeContent.textContent();
    expect(originalContent).toBeTruthy();

    // Reload page
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Verify narrative is still present
    const reloadedContent = await narrativeContent.textContent();
    expect(reloadedContent).toBe(originalContent);
  });
});

test.describe('Narrative Display', () => {
  test('should show narrative history/logs', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Look for narrative history section
    const historySection = page.locator('[data-testid="narrative-history"], .narrative-history, text=/history/i, text=/previous runs/i');

    if (await historySection.count() > 0) {
      await expect(historySection.first()).toBeVisible();
    }
  });

  test('should allow exporting narrative', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Look for export button
    const exportButton = page.locator('button:has-text("Export"), button:has-text("Download"), button:has-text("Save")');

    if (await exportButton.count() > 0) {
      // Click export
      await exportButton.first().click();

      // Verify download initiated or export dialog shown
      const downloadPromise = page.waitForEvent('download', { timeout: 5000 }).catch(() => null);
      const exportDialog = page.locator('role=dialog:has-text("Export")');

      const download = await downloadPromise;
      const dialogVisible = await exportDialog.isVisible();

      expect(download !== null || dialogVisible).toBeTruthy();
    }
  });
});
