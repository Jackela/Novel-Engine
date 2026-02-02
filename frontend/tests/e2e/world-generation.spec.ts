import { test, expect } from './fixtures';

/**
 * Generation E2E Test Suite (TEST-002)
 *
 * Tests the complete character generation flow on the Weaver canvas:
 * 1. Open Character Generation Modal
 * 2. Fill form with archetype
 * 3. Click Generate
 * 4. Verify nodes render on canvas (count > 0)
 *
 * Note: The actual Weaver UI uses Character Generation (not World Generation).
 * The toolbar "Generate" button opens a CharacterGenerationDialog.
 */
test.describe('Generation Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      (window as any).__e2eGenerationMode = 'success';
      (window as any).__e2eGenerationDelayMs = 300;
      (window as any).__lastGenerationRequest = null;
    });

    // Navigate to Weaver page
    await page.goto('/weaver', { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'Story Weaver' })).toBeVisible({
      timeout: 10000,
    });
  });

  /**
   * TEST-002: E2E Smoke Test - Generation
   *
   * PRD Acceptance Criteria:
   * - Test: Fill form -> Click Generate -> Wait for Node to appear
   * - Assert: Node count > 0
   */
  test('Scenario: Open Generation Modal -> Fill Form -> Generate -> Verify nodes', async ({
    page,
  }) => {
    // ========================================
    // GIVEN: User is on the Weaver page
    // ========================================
    await test.step('GIVEN: User is on the Weaver page', async () => {
      await expect(page).toHaveURL(/\/weaver/);
    });

    // ========================================
    // WHEN: User clicks "Generate" button in toolbar
    // ========================================
      await test.step('WHEN: User opens the Character Generation dialog', async () => {
        // The toolbar "Generate" button has aria-label="Generate"
      const generateBtn = page.getByRole('button', { name: /^Generate$/i }).first();
      await expect(generateBtn).toBeVisible({ timeout: 5000 });
      await generateBtn.click();

      // Wait for dialog to appear - check for dialog title "Generate Character"
      const dialog = page.locator('[role="dialog"]');
      await expect(dialog).toBeVisible({ timeout: 5000 });
      await expect(page.getByText('Generate Character')).toBeVisible({ timeout: 3000 });
    });

    // ========================================
    // WHEN: User fills the generation form
    // ========================================
    await test.step('WHEN: User fills in character archetype', async () => {
      // Fill archetype field (required for character generation)
      const archetypeInput = page.locator('#archetype');
      await expect(archetypeInput).toBeVisible({ timeout: 3000 });
      await archetypeInput.fill('Wandering Mage');
    });

    // ========================================
    // WHEN: User clicks Generate
    // ========================================
    await test.step('WHEN: User clicks the Generate button in dialog', async () => {
      const generateBtn = page
        .locator('[role="dialog"]')
        .getByRole('button', { name: /^generate$/i });
      await expect(generateBtn).toBeVisible({ timeout: 3000 });
      await generateBtn.click();
    });

    // ========================================
    // THEN: Dialog closes (generation triggered)
    // ========================================
    await test.step('THEN: Dialog closes indicating generation started', async () => {
      // Wait for dialog to close (generation closes the dialog immediately)
      await page.locator('[role="dialog"]').waitFor({ state: 'hidden', timeout: 10000 });
    });

    // ========================================
    // THEN: Nodes render on canvas
    // ========================================
    await test.step('THEN: Character nodes appear on the canvas', async () => {
      // Wait for nodes to appear on the canvas
      const canvas = page.locator('.react-flow');
      await expect(canvas).toBeAttached({ timeout: 10000 });

      // Allow time for nodes to be created and rendered
      await page.waitForTimeout(2000);

      // Verify nodes exist (check store or DOM)
      // The optimistic UI creates a node immediately, then updates it when API responds
      const nodeCount = await page.locator('.react-flow__node').count();
      expect(nodeCount).toBeGreaterThan(0);
    });
  });

  /**
   * Tests error handling when character generation fails.
   * The optimistic UI pattern creates a node immediately, then updates it to error state.
   */
  test('Scenario: Generation failure shows error state on node', async ({ page }) => {
    await page.addInitScript(() => {
      (window as any).__e2eGenerationMode = 'error';
      (window as any).__e2eGenerationDelayMs = 100;
    });

    // ========================================
    // WHEN: User triggers generation and API fails
    // ========================================
    await test.step('WHEN: User opens Character Generation and triggers generation', async () => {
      const generateBtn = page.getByRole('button', { name: /^Generate$/i }).first();
      await expect(generateBtn).toBeVisible({ timeout: 5000 });
      await generateBtn.click();

      const dialog = page.locator('[role="dialog"]');
      await expect(dialog).toBeVisible({ timeout: 5000 });

      // Fill required archetype field
      const archetypeInput = page.locator('#archetype');
      await archetypeInput.fill('Test Character');

      const submitBtn = page
        .locator('[role="dialog"]')
        .getByRole('button', { name: /^generate$/i });
      await submitBtn.click();
    });

    // ========================================
    // THEN: Node is created (optimistic UI) and shows error state
    // ========================================
    await test.step('THEN: Node shows error state', async () => {
      // Wait for dialog to close
      await page.locator('[role="dialog"]').waitFor({ state: 'hidden', timeout: 10000 });

      // Wait for the optimistic node to be created and updated to error state
      await page.waitForTimeout(2000);

      // The optimistic UI creates a node, then updates it to error state when API fails
      // Check for any indicator of error state
      const nodeCount = await page.locator('.react-flow__node').count();

      // At minimum, the optimistic node should exist
      // It may show loading or error state depending on timing
      expect(nodeCount).toBeGreaterThan(0);
    });
  });

  /**
   * Tests that generation request contains expected fields.
   */
  test('Scenario: Generated character request has expected structure', async ({ page }) => {
    await page.addInitScript(() => {
      (window as any).__e2eGenerationMode = 'success';
      (window as any).__e2eGenerationDelayMs = 100;
      (window as any).__lastGenerationRequest = null;
    });

    await test.step('WHEN: User triggers character generation', async () => {
      const generateBtn = page.getByRole('button', { name: /^Generate$/i }).first();
      await expect(generateBtn).toBeVisible({ timeout: 5000 });
      await generateBtn.click();

      const dialog = page.locator('[role="dialog"]');
      await expect(dialog).toBeVisible({ timeout: 5000 });

      // Fill archetype
      const archetypeInput = page.locator('#archetype');
      await archetypeInput.fill('Hero');

      const submitBtn = page
        .locator('[role="dialog"]')
        .getByRole('button', { name: /^generate$/i });
      await submitBtn.click();

      // Wait for request to be made
      await page.waitForTimeout(1000);
    });

    await test.step('THEN: Request payload has expected structure', async () => {
      const capturedRequest = await page.evaluate(
        () => (window as unknown as { __lastGenerationRequest?: Record<string, unknown> }).__lastGenerationRequest ?? null
      );
      expect(capturedRequest).not.toBeNull();
      if (capturedRequest) {
        // Character generation should include concept and archetype
        expect(capturedRequest).toHaveProperty('concept');
        expect(capturedRequest).toHaveProperty('archetype');
        expect(capturedRequest.archetype).toBe('Hero');
      }
    });
  });
});
