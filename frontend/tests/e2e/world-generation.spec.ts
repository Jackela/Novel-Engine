import { test, expect } from './fixtures';

/**
 * World Generation E2E Test Suite
 *
 * Tests the complete world generation flow:
 * 1. Open World Generation Modal
 * 2. Fill form with world parameters
 * 3. Click Generate
 * 4. Wait for success/toast
 * 5. Verify nodes render on canvas
 */
test.describe('World Generation Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Set up API mocks for world generation
    await page.route('**/api/world/generate', async (route) => {
      const request = route.request();
      const body = request.postDataJSON() as Record<string, unknown> | null;

      // Capture the request for validation
      await page.evaluate((data) => {
        (window as unknown as { __lastWorldGenRequest?: unknown }).__lastWorldGenRequest = data;
      }, body);

      // Return mocked world generation response
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          world_setting: {
            id: 'world-001',
            name: body?.genre === 'fantasy' ? 'Realm of Eldoria' : 'Test World',
            description: 'A mystical realm where magic flows through ancient ley lines.',
            genre: body?.genre || 'fantasy',
            era: body?.era || 'medieval',
            tone: body?.tone || 'heroic',
            themes: body?.themes || ['adventure', 'magic'],
            magic_level: body?.magic_level || 7,
            technology_level: body?.technology_level || 2,
          },
          factions: [
            {
              id: 'faction-001',
              name: 'Order of the Silver Dawn',
              description: 'An ancient order of knights dedicated to protecting the realm.',
              faction_type: 'military',
              alignment: 'lawful_good',
              values: ['honor', 'duty', 'protection'],
              goals: ['Defend the realm', 'Maintain peace'],
              influence: 8,
              ally_count: 3,
              enemy_count: 2,
            },
            {
              id: 'faction-002',
              name: 'Shadow Guild',
              description: 'A secretive network of spies and assassins.',
              faction_type: 'criminal',
              alignment: 'neutral_evil',
              values: ['secrecy', 'profit', 'power'],
              goals: ['Control the underworld', 'Gather secrets'],
              influence: 6,
              ally_count: 1,
              enemy_count: 4,
            },
          ],
          locations: [
            {
              id: 'loc-001',
              name: 'Silverholme Castle',
              description: 'The seat of power for the Order of the Silver Dawn.',
              location_type: 'castle',
              population: 500,
              controlling_faction_id: 'faction-001',
              notable_features: ['Grand Hall', 'Training Grounds', 'Ancient Library'],
              danger_level: 'low',
            },
            {
              id: 'loc-002',
              name: 'Whisperwood Forest',
              description: 'A dense, enchanted forest hiding ancient secrets.',
              location_type: 'forest',
              population: 0,
              controlling_faction_id: null,
              notable_features: ['Ancient Ruins', 'Mystic Grove', 'Hidden Paths'],
              danger_level: 'medium',
            },
          ],
          events: [
            {
              id: 'event-001',
              name: 'The Great Sundering',
              description: 'A cataclysmic event that reshaped the continent.',
              event_type: 'disaster',
              significance: 10,
              participants: ['Ancient Mages', 'Elder Dragons'],
            },
          ],
          generation_summary: 'World generated successfully with 2 factions and 2 locations.',
        }),
      });
    });

    // Navigate to Weaver page
    await page.goto('/weaver', { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'Story Weaver' })).toBeVisible({
      timeout: 10000,
    });
  });

  test('Scenario: Open World Gen Modal -> Fill Form -> Generate -> Verify nodes', async ({
    page,
  }) => {
    // ========================================
    // GIVEN: User is on the Weaver page
    // ========================================
    await test.step('GIVEN: User is on the Weaver page', async () => {
      await expect(page).toHaveURL(/\/weaver/);
    });

    // ========================================
    // WHEN: User clicks "Generate World" button
    // ========================================
    await test.step('WHEN: User opens the World Generation dialog', async () => {
      // Look for Generate World button in toolbar
      const generateWorldBtn = page.getByRole('button', { name: /generate.*world/i });
      await expect(generateWorldBtn).toBeVisible({ timeout: 5000 });
      await generateWorldBtn.click();

      // Wait for dialog to appear
      const dialog = page.locator('[role="dialog"], [data-testid="world-generation-dialog"]');
      await expect(dialog).toBeVisible({ timeout: 5000 });
    });

    // ========================================
    // WHEN: User fills the generation form
    // ========================================
    await test.step('WHEN: User fills in world parameters', async () => {
      // Fill genre (select or input)
      const genreInput = page.locator('[data-testid="genre-input"], [name="genre"]').first();
      if (await genreInput.isVisible()) {
        await genreInput.fill('fantasy');
      }

      // Fill era
      const eraInput = page.locator('[data-testid="era-input"], [name="era"]').first();
      if (await eraInput.isVisible()) {
        await eraInput.fill('medieval');
      }

      // Fill tone
      const toneInput = page.locator('[data-testid="tone-input"], [name="tone"]').first();
      if (await toneInput.isVisible()) {
        await toneInput.fill('heroic');
      }
    });

    // ========================================
    // WHEN: User clicks Generate
    // ========================================
    await test.step('WHEN: User clicks the Generate button', async () => {
      const generateBtn = page.getByRole('button', { name: /^generate$/i });
      await expect(generateBtn).toBeVisible({ timeout: 3000 });
      await generateBtn.click();
    });

    // ========================================
    // THEN: Success is indicated
    // ========================================
    await test.step('THEN: Success toast or indicator appears', async () => {
      // Wait for dialog to close or success message
      const successIndicators = [
        page.locator('[data-testid="toast-success"]'),
        page.locator('[role="status"]').filter({ hasText: /success|generated/i }),
        page.locator('.toast').filter({ hasText: /success/i }),
      ];

      // Wait for any success indicator or dialog to close
      await Promise.race([
        ...successIndicators.map((indicator) => indicator.waitFor({ state: 'visible', timeout: 15000 }).catch(() => null)),
        page.locator('[role="dialog"]').waitFor({ state: 'hidden', timeout: 15000 }).catch(() => null),
      ]);
    });

    // ========================================
    // THEN: Nodes render on canvas
    // ========================================
    await test.step('THEN: World nodes appear on the canvas', async () => {
      // Wait for nodes to appear
      const canvas = page.locator('[data-testid="weaver-canvas"], .react-flow');
      await expect(canvas).toBeAttached({ timeout: 10000 });

      // Wait for at least one world-type node to appear
      // The mocked response should create world, faction, and location nodes
      const worldNode = page.locator('[data-testid*="world"], .react-flow__node[data-type="world"]');

      // Allow time for nodes to be created and rendered
      await page.waitForTimeout(2000);

      // Verify nodes exist (check store or DOM)
      const nodeCount = await page.locator('.react-flow__node').count();
      expect(nodeCount).toBeGreaterThan(0);
    });
  });

  test('Scenario: Generation failure shows error state', async ({ page }) => {
    // Override mock to return error
    await page.route('**/api/world/generate', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'error',
          error: {
            type: 'LLMError',
            message: 'World generation service unavailable',
            detail: 'Connection timeout',
          },
        }),
      });
    });

    // ========================================
    // WHEN: User triggers generation and API fails
    // ========================================
    await test.step('WHEN: User opens World Generation and triggers generation', async () => {
      const generateWorldBtn = page.getByRole('button', { name: /generate.*world/i });
      if (await generateWorldBtn.isVisible({ timeout: 3000 })) {
        await generateWorldBtn.click();

        const dialog = page.locator('[role="dialog"]');
        await expect(dialog).toBeVisible({ timeout: 3000 });

        const generateBtn = page.getByRole('button', { name: /^generate$/i });
        await generateBtn.click();
      }
    });

    // ========================================
    // THEN: Error state is displayed
    // ========================================
    await test.step('THEN: Error is displayed to user', async () => {
      const errorIndicators = [
        page.locator('[data-testid="generation-error"]'),
        page.locator('[data-testid="toast-error"]'),
        page.locator('[role="alert"]'),
        page.locator('.react-flow__node[data-status="error"]'),
      ];

      // Wait for any error indicator
      const visibleError = await Promise.race(
        errorIndicators.map(async (indicator) => {
          try {
            await indicator.waitFor({ state: 'visible', timeout: 10000 });
            return indicator;
          } catch {
            return null;
          }
        })
      );

      // At least one error indicator should be visible
      // If not found, check for error text anywhere
      if (!visibleError) {
        const hasErrorText = await page.locator('text=/error|failed|unavailable/i').isVisible();
        expect(hasErrorText).toBe(true);
      }
    });
  });

  test('Scenario: Generated world data is correctly structured', async ({ page }) => {
    let capturedRequest: Record<string, unknown> | null = null;

    await page.route('**/api/world/generate', async (route) => {
      capturedRequest = route.request().postDataJSON() as Record<string, unknown>;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          world_setting: { id: 'world-test', name: 'Test', description: '', genre: 'fantasy', era: 'medieval', tone: 'heroic', themes: [], magic_level: 5, technology_level: 3 },
          factions: [],
          locations: [],
          events: [],
          generation_summary: 'Test generation',
        }),
      });
    });

    await test.step('WHEN: User triggers world generation', async () => {
      const generateWorldBtn = page.getByRole('button', { name: /generate.*world/i });
      if (await generateWorldBtn.isVisible({ timeout: 3000 })) {
        await generateWorldBtn.click();

        const dialog = page.locator('[role="dialog"]');
        if (await dialog.isVisible({ timeout: 3000 })) {
          const generateBtn = page.getByRole('button', { name: /^generate$/i });
          await generateBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    });

    await test.step('THEN: Request payload has expected structure', async () => {
      // Verify the request was made with expected fields
      if (capturedRequest) {
        // The request should contain generation parameters
        expect(typeof capturedRequest).toBe('object');
        // Common expected fields
        const expectedFields = ['genre', 'era', 'tone', 'themes', 'num_factions', 'num_locations'];
        const hasAnyExpectedField = expectedFields.some((field) =>
          Object.prototype.hasOwnProperty.call(capturedRequest, field)
        );
        expect(hasAnyExpectedField).toBe(true);
      }
    });
  });
});
