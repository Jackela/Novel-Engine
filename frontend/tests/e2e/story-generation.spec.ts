import { test, expect } from './fixtures';

/**
 * NAR-001: BDD Spec - The Writer's Flow
 *
 * This test defines the behavior of story generation BEFORE implementation.
 * It serves as the requirements document for the streaming narrative feature.
 *
 * Status: RED (Expected to fail until NAR-002 and NAR-003 are implemented)
 */
test.describe('Story Generation - The Writer\'s Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Mock the narrative streaming endpoint
    await page.route('**/api/narratives/stream', async (route) => {
      const request = route.request();
      const postData = request.postDataJSON() as Record<string, unknown> | null;

      // Store request for validation
      await page.evaluate((data) => {
        (window as unknown as { __lastNarrativeRequest?: unknown }).__lastNarrativeRequest = data;
      }, postData);

      // Simulate SSE streaming response
      const chunks = [
        'In the depths of the ancient forest, ',
        'where shadows danced with moonlight, ',
        'a figure emerged from the mist. ',
        'Her name was whispered among the trees—',
        'Elara, the last keeper of forgotten memories.',
      ];

      // Build SSE response body
      let sseBody = '';
      for (const chunk of chunks) {
        sseBody += `data: ${JSON.stringify({ type: 'chunk', content: chunk })}\n\n`;
      }
      sseBody += `data: ${JSON.stringify({ type: 'done', content: '' })}\n\n`;

      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: sseBody,
      });
    });
  });

  test('Scenario 1: User clicks "New Chapter" -> "Generating..." state appears', async ({
    page,
  }) => {
    // ========================================
    // GIVEN: User is on the Story Editor page
    // ========================================
    await test.step('GIVEN: User navigates to the Story Editor page', async () => {
      await page.goto('/stories/editor', { waitUntil: 'domcontentloaded' });
    });

    // ========================================
    // WHEN: User clicks the "New Chapter" button
    // ========================================
    await test.step('WHEN: User clicks the "New Chapter" button', async () => {
      const newChapterButton = page.getByRole('button', { name: /new chapter/i });
      await expect(newChapterButton).toBeVisible({ timeout: 5000 });
      await newChapterButton.click();
    });

    // ========================================
    // THEN: "Generating..." state appears
    // ========================================
    await test.step('THEN: A "Generating..." indicator appears in the editor', async () => {
      // The editor should show a loading/generating state
      const generatingIndicator = page.locator('[data-testid="generating-indicator"]');
      await expect(generatingIndicator).toBeVisible({ timeout: 3000 });
      await expect(generatingIndicator).toContainText(/generating/i);
    });
  });

  test('Scenario 2: SSE stream delivers text incrementally to the editor', async ({ page }) => {
    // ========================================
    // GIVEN: User is on the Story Editor page with streaming mock
    // ========================================
    await test.step('GIVEN: User navigates to the Story Editor page', async () => {
      await page.goto('/stories/editor', { waitUntil: 'domcontentloaded' });
    });

    // ========================================
    // WHEN: User triggers story generation
    // ========================================
    await test.step('WHEN: User clicks "New Chapter" to trigger generation', async () => {
      const newChapterButton = page.getByRole('button', { name: /new chapter/i });
      await expect(newChapterButton).toBeVisible({ timeout: 5000 });
      await newChapterButton.click();
    });

    // ========================================
    // THEN: Text appears incrementally in the editor
    // ========================================
    await test.step('THEN: Text appears incrementally in the editor area', async () => {
      const editor = page.locator('[data-testid="narrative-editor"]');
      await expect(editor).toBeVisible({ timeout: 5000 });

      // Wait for streaming to complete and verify final content
      await expect(editor).toContainText('In the depths of the ancient forest', { timeout: 10000 });
      await expect(editor).toContainText('Elara, the last keeper of forgotten memories', {
        timeout: 10000,
      });
    });

    await test.step('THEN: The generating indicator disappears after completion', async () => {
      const generatingIndicator = page.locator('[data-testid="generating-indicator"]');
      await expect(generatingIndicator).not.toBeVisible({ timeout: 10000 });
    });
  });

  test('Scenario 3: World Context is sent in the generation payload', async ({ page }) => {
    // ========================================
    // GIVEN: User is on the Story Editor with World Context loaded
    // ========================================
    await test.step('GIVEN: User navigates to the Story Editor page', async () => {
      await page.goto('/stories/editor', { waitUntil: 'domcontentloaded' });
    });

    // Set up request interception to capture the payload
    let capturedPayload: Record<string, unknown> | null = null;
    await page.route('**/api/narratives/stream', async (route) => {
      const request = route.request();
      capturedPayload = request.postDataJSON() as Record<string, unknown>;

      // Fulfill with minimal SSE response
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: `data: ${JSON.stringify({ type: 'chunk', content: 'Test content.' })}\n\ndata: ${JSON.stringify({ type: 'done', content: '' })}\n\n`,
      });
    });

    // ========================================
    // WHEN: User triggers story generation
    // ========================================
    await test.step('WHEN: User clicks "New Chapter" to trigger generation', async () => {
      const newChapterButton = page.getByRole('button', { name: /new chapter/i });
      await expect(newChapterButton).toBeVisible({ timeout: 5000 });
      await newChapterButton.click();

      // Wait for request to be made
      await page.waitForTimeout(1000);
    });

    // ========================================
    // THEN: The request payload includes World Context
    // ========================================
    await test.step('THEN: The API request includes world_context in the payload', async () => {
      expect(capturedPayload).not.toBeNull();
      expect(capturedPayload).toHaveProperty('world_context');

      // World context should contain relevant entities
      const worldContext = capturedPayload?.world_context as Record<string, unknown> | undefined;
      expect(worldContext).toBeDefined();

      // Validate structure of world context
      // It should contain characters, locations, or other world entities
      expect(
        worldContext &&
          (Object.prototype.hasOwnProperty.call(worldContext, 'characters') ||
            Object.prototype.hasOwnProperty.call(worldContext, 'locations') ||
            Object.prototype.hasOwnProperty.call(worldContext, 'entities'))
      ).toBe(true);
    });
  });

  test('Scenario 4: Error handling - API failure shows error state', async ({ page }) => {
    // Override mock to return error
    await page.route('**/api/narratives/stream', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Narrative generation service unavailable' }),
      });
    });

    // ========================================
    // GIVEN: User is on the Story Editor page
    // ========================================
    await test.step('GIVEN: User navigates to the Story Editor page', async () => {
      await page.goto('/stories/editor', { waitUntil: 'domcontentloaded' });
    });

    // ========================================
    // WHEN: User triggers story generation and API fails
    // ========================================
    await test.step('WHEN: User clicks "New Chapter" and API returns error', async () => {
      const newChapterButton = page.getByRole('button', { name: /new chapter/i });
      await expect(newChapterButton).toBeVisible({ timeout: 5000 });
      await newChapterButton.click();
    });

    // ========================================
    // THEN: Error state is displayed to user
    // ========================================
    await test.step('THEN: An error message is displayed to the user', async () => {
      const errorIndicator = page.locator('[data-testid="generation-error"]');
      await expect(errorIndicator).toBeVisible({ timeout: 5000 });
      await expect(errorIndicator).toContainText(/error|failed|unavailable/i);
    });

    await test.step('THEN: The "New Chapter" button is re-enabled for retry', async () => {
      const newChapterButton = page.getByRole('button', { name: /new chapter/i });
      await expect(newChapterButton).toBeEnabled({ timeout: 5000 });
    });
  });

  test('Scenario 5: User can cancel ongoing generation', async ({ page }) => {
    // Set up a slow streaming response
    await page.route('**/api/narratives/stream', async (route) => {
      // This will be aborted before completion
      await new Promise((resolve) => setTimeout(resolve, 5000));
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: `data: ${JSON.stringify({ type: 'chunk', content: 'Content' })}\n\n`,
      });
    });

    // ========================================
    // GIVEN: User is on the Story Editor page
    // ========================================
    await test.step('GIVEN: User navigates to the Story Editor page', async () => {
      await page.goto('/stories/editor', { waitUntil: 'domcontentloaded' });
    });

    // ========================================
    // WHEN: User starts and then cancels generation
    // ========================================
    await test.step('WHEN: User clicks "New Chapter" to start generation', async () => {
      const newChapterButton = page.getByRole('button', { name: /new chapter/i });
      await expect(newChapterButton).toBeVisible({ timeout: 5000 });
      await newChapterButton.click();
    });

    await test.step('WHEN: User clicks "Cancel" to stop generation', async () => {
      const cancelButton = page.getByRole('button', { name: /cancel|stop/i });
      await expect(cancelButton).toBeVisible({ timeout: 3000 });
      await cancelButton.click();
    });

    // ========================================
    // THEN: Generation stops and UI returns to idle state
    // ========================================
    await test.step('THEN: The generating indicator disappears', async () => {
      const generatingIndicator = page.locator('[data-testid="generating-indicator"]');
      await expect(generatingIndicator).not.toBeVisible({ timeout: 3000 });
    });

    await test.step('THEN: The "New Chapter" button is re-enabled', async () => {
      const newChapterButton = page.getByRole('button', { name: /new chapter/i });
      await expect(newChapterButton).toBeEnabled({ timeout: 3000 });
    });
  });
});
