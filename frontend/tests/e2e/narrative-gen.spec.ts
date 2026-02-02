/**
 * E2E Test: The Ghostwriter Test (NAR-012)
 *
 * Verifies the full narrative generation loop:
 * 1. Navigate to the story editor
 * 2. Click "New Chapter" to trigger generation
 * 3. Assert the editor content becomes non-empty after streaming completes
 */
import { test, expect } from './fixtures';
import { prepareGuestSession } from './utils/auth';

test.describe('Narrative Generation - Ghostwriter Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Prepare guest session for authentication bypass
    await prepareGuestSession(page);
    await page.addInitScript(() => {
      (window as any).__e2eNarrativeMode = 'success';
      (window as any).__e2eNarrativeDelayMs = 100;
    });
  });

  test('@narrative generates story content via New Chapter button', async ({ page }) => {
    // ========================================
    // GIVEN: User is on the story editor page
    // ========================================
    await test.step('GIVEN: User navigates to the story editor', async () => {
      await page.goto('/stories/editor', { waitUntil: 'domcontentloaded' });

      // Wait for page to fully load
      await expect(page.getByRole('heading', { name: 'Story Editor' })).toBeVisible({
        timeout: 10000,
      });
    });

    await test.step('GIVEN: Editor is in idle state with empty content', async () => {
      // Verify the narrative editor exists and shows idle message
      const narrativeEditor = page.locator('[data-testid="narrative-editor"]');
      await expect(narrativeEditor).toBeVisible();

      // Should show the idle prompt
      await expect(page.getByText('Click "New Chapter" to start generating')).toBeVisible();
    });

    // ========================================
    // WHEN: User clicks the New Chapter button
    // ========================================
    await test.step('WHEN: User clicks the New Chapter button', async () => {
      const newChapterButton = page.getByRole('button', { name: 'New Chapter' });
      await expect(newChapterButton).toBeVisible();
      await expect(newChapterButton).toBeEnabled();

      await newChapterButton.click();
    });

    await test.step('WHEN: Generation indicator appears during streaming', async () => {
      // The generating indicator should appear while streaming
      // Use .first() since there may be multiple indicators during different states
      const generatingIndicator = page.locator('[data-testid="generating-indicator"]').first();
      // Use a short timeout since mock returns quickly
      await expect(generatingIndicator).toBeVisible({ timeout: 2000 });
    });

    // ========================================
    // THEN: Editor content becomes non-empty
    // ========================================
    await test.step('THEN: Editor content is populated with generated text', async () => {
      // Wait for generation to complete (status changes to 'complete')
      // The generating indicator should disappear or show completion stats
      // Wait for content to appear instead of checking indicator (which may have multiple elements)
      const narrativeEditor = page.locator('[data-testid="narrative-editor"]');
      await expect(narrativeEditor).toBeVisible();

      // The content should include our mock story text
      await expect(narrativeEditor).toContainText('The Beginning', { timeout: 10000 });
      await expect(narrativeEditor).toContainText('ancient library');
      await expect(narrativeEditor).toContainText('Elena');
    });

    await test.step('THEN: Metadata shows generation stats', async () => {
      // After completion, metadata should be visible (chars and time)
      await expect(page.getByText(/chars/i)).toBeVisible({ timeout: 3000 });
    });

    await test.step('THEN: New Chapter button is re-enabled for next generation', async () => {
      const newChapterButton = page.getByRole('button', { name: 'New Chapter' });
      await expect(newChapterButton).toBeEnabled();
    });
  });

  test('@narrative shows generating indicator and Cancel button during stream', async ({
    page,
  }) => {
    await page.addInitScript(() => {
      (window as any).__e2eNarrativeMode = 'success';
      (window as any).__e2eNarrativeDelayMs = 2000;
    });

    // ========================================
    // GIVEN: User is on the story editor page
    // ========================================
    await test.step('GIVEN: User navigates to the story editor', async () => {
      await page.goto('/stories/editor', { waitUntil: 'domcontentloaded' });
      await expect(page.getByRole('heading', { name: 'Story Editor' })).toBeVisible({
        timeout: 10000,
      });
    });

    // ========================================
    // WHEN: User clicks New Chapter
    // ========================================
    await test.step('WHEN: User clicks New Chapter to start generation', async () => {
      await page.getByRole('button', { name: 'New Chapter' }).click();
    });

    // ========================================
    // THEN: Cancel button appears during streaming
    // ========================================
    await test.step('THEN: Cancel button is visible during generation', async () => {
      const cancelButton = page.getByRole('button', { name: 'Cancel' });
      await expect(cancelButton).toBeVisible({ timeout: 2000 });
    });

    await test.step('THEN: Generating indicator is visible', async () => {
      // Use .first() since there may be multiple indicators
      const generatingIndicator = page.locator('[data-testid="generating-indicator"]').first();
      await expect(generatingIndicator).toBeVisible();
    });
  });

  test('@narrative handles streaming error gracefully', async ({ page }) => {
    await page.addInitScript(() => {
      (window as any).__e2eNarrativeMode = 'error';
      (window as any).__e2eNarrativeDelayMs = 0;
    });

    await test.step('GIVEN: User navigates to the story editor', async () => {
      await page.goto('/stories/editor', { waitUntil: 'domcontentloaded' });
      await expect(page.getByRole('heading', { name: 'Story Editor' })).toBeVisible({
        timeout: 10000,
      });
    });

    // ========================================
    // WHEN: User clicks New Chapter
    // ========================================
    await test.step('WHEN: User clicks New Chapter', async () => {
      await page.getByRole('button', { name: 'New Chapter' }).click();
    });

    // ========================================
    // THEN: Error is displayed gracefully
    // ========================================
    await test.step('THEN: Error message is displayed', async () => {
      const errorCard = page.locator('[data-testid="generation-error"]');
      await expect(errorCard).toBeVisible({ timeout: 5000 });
      await expect(errorCard).toContainText('Error');
    });

    await test.step('THEN: Retry button is available', async () => {
      await expect(page.getByRole('button', { name: 'Retry' })).toBeVisible();
    });
  });
});
