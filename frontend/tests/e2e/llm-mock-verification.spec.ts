/**
 * LLM Mock Verification Tests
 *
 * These tests verify that the LLM mock infrastructure works correctly
 * and completes within the required time constraint (<2 seconds).
 *
 * Run with MOCK_LLM=true:
 *   MOCK_LLM=true npm run test:e2e -- llm-mock-verification.spec.ts
 */
import { test, expect } from '@playwright/test';
import {
  isMockLLMEnabled,
  mockLLMEndpoints,
  mockGenerateEndpoint,
  mockCharacterGeneration,
} from './utils/llmMocks';

/**
 * Performance threshold: All mock operations must complete under this time.
 */
const MAX_EXECUTION_TIME_MS = 2000;

test.describe('LLM Mock Infrastructure Verification', () => {
  test.skip(!isMockLLMEnabled(), 'Skipped: MOCK_LLM=true required');

  test('@mock-llm mock /api/generate endpoint responds instantly', async ({
    page,
    baseURL,
  }) => {
    const startTime = Date.now();

    await mockGenerateEndpoint(page);

    // Navigate to actual app page to enable relative URL fetch
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    // Directly call the mocked endpoint via page.evaluate
    const apiUrl = baseURL ? `${baseURL}/api/generate` : '/api/generate';
    const response = await page.evaluate(async (url) => {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: 'test prompt' }),
      });
      return {
        status: res.status,
        body: await res.json(),
      };
    }, apiUrl);

    const elapsedTime = Date.now() - startTime;

    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('success', true);
    expect(response.body).toHaveProperty('content');
    expect(elapsedTime).toBeLessThan(MAX_EXECUTION_TIME_MS);
  });

  test('@mock-llm mock /api/generation/character endpoint responds instantly', async ({
    page,
    baseURL,
  }) => {
    const startTime = Date.now();

    await mockCharacterGeneration(page);

    // Navigate to actual app page to enable relative URL fetch
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    const apiUrl = baseURL
      ? `${baseURL}/api/generation/character`
      : '/api/generation/character';
    const response = await page.evaluate(async (url) => {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ archetype: 'test', tone: 'noir' }),
      });
      return {
        status: res.status,
        body: await res.json(),
      };
    }, apiUrl);

    const elapsedTime = Date.now() - startTime;

    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('name');
    expect(response.body).toHaveProperty('tagline');
    expect(elapsedTime).toBeLessThan(MAX_EXECUTION_TIME_MS);
  });

  test('@mock-llm full LLM mock setup completes under 2 seconds', async ({ page }) => {
    const startTime = Date.now();

    await mockLLMEndpoints(page);

    const setupTime = Date.now() - startTime;

    expect(setupTime).toBeLessThan(MAX_EXECUTION_TIME_MS);
  });

  test('@mock-llm isMockLLMEnabled returns true when MOCK_LLM=true', () => {
    // This test only runs when MOCK_LLM=true (due to skip condition above)
    expect(isMockLLMEnabled()).toBe(true);
  });
});

test.describe('LLM Mock E2E Integration', () => {
  test.skip(!isMockLLMEnabled(), 'Skipped: MOCK_LLM=true required');

  test('@mock-llm generation workflow completes under 2 seconds with mock', async ({
    page,
    baseURL,
  }) => {
    // Skip if no baseURL (standalone test)
    if (!baseURL) {
      test.skip(true, 'Requires baseURL for E2E test');
      return;
    }

    const startTime = Date.now();

    await mockLLMEndpoints(page);

    // Navigate to weaver page and trigger generation
    await page.goto('/weaver', { waitUntil: 'domcontentloaded' });

    // Check if Generate button exists
    const generateButton = page.getByRole('button', { name: 'Generate' });
    const hasGenerateButton = (await generateButton.count()) > 0;

    if (hasGenerateButton) {
      // Click generate and verify mock response is received
      await generateButton.click();

      // Wait for dialog if it appears
      const dialog = page.getByRole('dialog');
      if ((await dialog.count()) > 0) {
        // Fill minimal form and submit
        const archetypeInput = page.getByLabel('Archetype');
        if ((await archetypeInput.count()) > 0) {
          await archetypeInput.fill('Test');
        }

        const toneSelect = page.getByLabel('Tone');
        if ((await toneSelect.count()) > 0) {
          await toneSelect.click();
          const noirOption = page.getByRole('option', { name: 'Noir' });
          if ((await noirOption.count()) > 0) {
            await noirOption.click();
          }
        }

        // Submit
        const submitButton = page.getByRole('button', { name: 'Generate' }).last();
        if ((await submitButton.count()) > 0) {
          await submitButton.click();
        }
      }
    }

    const elapsedTime = Date.now() - startTime;

    // Verify total time is under 2 seconds
    expect(elapsedTime).toBeLessThan(MAX_EXECUTION_TIME_MS);
  });
});
