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

/**
 * Creates a mock SSE response body with narrative content.
 * Simulates the server streaming text chunks.
 */
function createMockNarrativeSSE(): string {
  const chunks = [
    '## The Beginning\n\n',
    'The ancient library stretched endlessly before Elena, ',
    'its towering shelves heavy with forgotten knowledge. ',
    'She ran her fingers along the dusty spines, ',
    'searching for the tome that would change everything.\n\n',
    '*The shadows whispered secrets...*\n',
  ];

  let sseBody = '';
  for (const chunk of chunks) {
    sseBody += `data: ${JSON.stringify({ type: 'chunk', content: chunk })}\n\n`;
  }
  // Add completion event with metadata
  sseBody += `data: ${JSON.stringify({
    type: 'done',
    content: '',
    metadata: {
      total_chunks: chunks.length,
      total_characters: chunks.join('').length,
      generation_time_ms: 1200,
      model_used: 'mock-llm-v1',
    },
  })}\n\n`;

  return sseBody;
}

test.describe('Narrative Generation - Ghostwriter Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Prepare guest session for authentication bypass
    await prepareGuestSession(page);

    // Mock the narrative streaming endpoint
    await page.route('**/api/narratives/stream', async (route) => {
      // Small delay to simulate network latency
      await new Promise((resolve) => setTimeout(resolve, 100));

      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        headers: {
          'Cache-Control': 'no-cache',
          Connection: 'keep-alive',
        },
        body: createMockNarrativeSSE(),
      });
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
    // Override mock with a slower response to test Cancel button
    await page.route(
      '**/api/narratives/stream',
      async (route) => {
        // Longer delay to ensure we can observe Cancel button
        await new Promise((resolve) => setTimeout(resolve, 2000));

        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          body: createMockNarrativeSSE(),
        });
      },
      { times: 1 }
    );

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
    // ========================================
    // GIVEN: API will return an error
    // ========================================
    await test.step('GIVEN: API mock configured to return error', async () => {
      await page.route(
        '**/api/narratives/stream',
        async (route) => {
          await route.fulfill({
            status: 500,
            contentType: 'application/json',
            body: JSON.stringify({ detail: 'Generation service unavailable' }),
          });
        },
        { times: 1 }
      );
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
