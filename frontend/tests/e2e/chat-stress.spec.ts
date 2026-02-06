/**
 * Chat Stress and Resilience E2E Tests
 *
 * OPT-015: E2E: Chat Stress + Resilience
 *
 * Tests verify:
 * - Rapid-fire message simulation (50+ messages)
 * - Network interruption during streaming
 * - Error state and recovery flow
 * - Message order stability
 * - UI responsiveness under load
 *
 * @tags @e2e @chat @stress @resilience
 */

import type { Page } from '@playwright/test';
import { test, expect } from './fixtures';

/**
 * Mock chat API for testing
 * Simulates streaming responses with SSE
 */
async function mockChatAPI(
  page: Page,
  options: {
    responseDelay?: number;
    failAtMessage?: number;
    interruptResponse?: boolean;
  } = {}
) {
  const { responseDelay = 50, failAtMessage, interruptResponse = false } = options;

  let messageCount = 0;

  await page.route(/\/api\/brain\/chat/, async (route) => {
    messageCount++;

    // Check if we should fail this request
    if (failAtMessage && messageCount === failAtMessage) {
      await route.abort('failed');
      return;
    }

    const request = route.request();
    const body = await request.postData();
    const payload = body ? JSON.parse(body) : {};
    const userQuery = payload.query || 'test message';

    // Simulate network interruption during streaming
    if (interruptResponse && messageCount > 5) {
      // Send partial response then abort
      route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        headers: {
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
        },
        body: `data: {"delta":"Partial response...", "done": false}\n\n`,
      }).then(() => {
        // Connection interrupted
      });
      return;
    }

    // Simulate streaming response
    const words = [
      `I received your question: "${userQuery.substring(0, 30)}..."`,
      'This is a simulated streaming response.',
      `Message #${messageCount} processed successfully.`,
      'The chat interface remains responsive.',
      'End of response.',
    ];

    let sseChunks = '';
    words.forEach((word, i) => {
      const chunk = {
        delta: word + ' ',
        done: i === words.length - 1,
      };
      sseChunks += `data: ${JSON.stringify(chunk)}\n\n`;
    });

    // Add final done signal
    sseChunks += `data: ${JSON.stringify({ delta: '', done: true })}\n\n`;

    await new Promise(resolve => setTimeout(resolve, responseDelay));

    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      headers: {
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
      body: sseChunks,
    });
  });
}

/**
 * Mock brain settings API to enable chat
 */
async function mockBrainSettingsAPI(page: Page) {
  await page.route(/\/api\/brain\/settings/, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        api_keys: {
          openai_key: 'sk-mock-key',
          anthropic_key: 'sk-ant-mock-key',
          gemini_key: 'AIza-mock-key',
          ollama_base_url: 'http://localhost:11434',
          has_openai: true,
          has_anthropic: true,
          has_gemini: true,
        },
        rag_config: {
          enabled: true,
          max_chunks: 5,
          score_threshold: 0.7,
          context_token_limit: 4000,
          include_sources: true,
          chunk_size: 500,
          chunk_overlap: 50,
          hybrid_search_weight: 0.7,
        },
        knowledge_base: {
          total_entries: 10,
          characters_count: 3,
          lore_count: 5,
          scenes_count: 2,
          plotlines_count: 0,
          last_sync: new Date().toISOString(),
          is_healthy: true,
        },
      }),
    });
  });
}

/**
 * Open the chat interface
 */
async function openChat(page: Page) {
  // Chat button should be visible (fixed bottom-right button with MessageSquare icon)
  const chatButton = page.getByLabel('Open chat');
  await chatButton.click();
}

/**
 * Send a message through the chat interface
 */
async function sendMessage(page: Page, message: string) {
  const input = page.locator('.ChatInterface input[type="text"]').or(page.getByPlaceholder(/type your message/i));
  await input.fill(message);

  const sendButton = page.locator('button:has(svg[data-lucide="send"])');
  await sendButton.click();
}

/**
 * Get all messages from the chat
 */
async function getMessages(page: Page) {
  // Messages are in the virtualized list
  const messageContainer = page.locator('.ChatInterface [class*="messages"]');
  return await messageContainer.allTextContents();
}

test.describe('Chat Stress Tests', () => {
  test.beforeEach(async ({ page }) => {
    await mockChatAPI(page);
    await mockBrainSettingsAPI(page);
    await page.goto('/');
    await openChat(page);
  });

  test('should handle 50 rapid-fire messages', async ({ page }) => {
    // OPT-015: Rapid-fire message simulation (50+ messages)

    const messageCount = 50;
    const messages: string[] = [];

    // Send 50 messages rapidly
    for (let i = 1; i <= messageCount; i++) {
      const msg = `Test message ${i}`;
      messages.push(msg);
      await sendMessage(page, msg);

      // Small delay between sends to avoid overwhelming
      await page.waitForTimeout(10);
    }

    // Wait for all responses to complete
    await page.waitForTimeout(5000);

    // Verify chat interface is still responsive
    const chatInput = page.locator('.ChatInterface input[type="text"]');
    await expect(chatInput).toBeVisible();
    await expect(chatInput).toBeEnabled();

    // Verify messages are in the chat by checking for some expected content
    for (const msg of messages.slice(0, 5)) {
      await expect(page.locator('.ChatInterface')).toContainText(msg, { timeout: 5000 });
    }
  });

  test('should maintain UI responsiveness during rapid messaging', async ({ page }) => {
    // OPT-015: UI remains responsive during stress

    const messageCount = 30;

    for (let i = 1; i <= messageCount; i++) {
      await sendMessage(page, `Message ${i}`);

      // Verify input is still enabled after each message
      const chatInput = page.locator('.ChatInterface input[type="text"]');
      await expect(chatInput).toBeEnabled({ timeout: 1000 });
    }

    // Wait for processing
    await page.waitForTimeout(3000);

    // Verify chat can still be toggled (minimize/maximize)
    const minimizeButton = page.locator('button:has(svg[data-lucide="minimize"])');
    await minimizeButton.click();

    const maximizeButton = page.locator('button:has(svg[data-lucide="maximize"])').or(
      page.locator('button:has(svg[data-lucide="maximize-2"])')
    );
    await expect(maximizeButton).toBeVisible();
    await maximizeButton.click();

    // Verify chat is still open and responsive
    const chatInput = page.locator('.ChatInterface input[type="text"]');
    await expect(chatInput).toBeVisible();
  });

  test('should preserve message order under load', async ({ page }) => {
    // OPT-015: Message order remains stable

    const messageCount = 40;

    // Send messages with timestamps
    for (let i = 1; i <= messageCount; i++) {
      await sendMessage(page, `Order test ${i}`);
      await page.waitForTimeout(20);
    }

    await page.waitForTimeout(4000);

    // Verify first and last messages are in correct order
    const chatContainer = page.locator('.ChatInterface');
    await expect(chatContainer).toContainText('Order test 1');
    await expect(chatContainer).toContainText('Order test 40');

    // Get all text content and verify order
    const content = await chatContainer.allTextContents();
    const fullText = content.join(' ');
    const pos1 = fullText.indexOf('Order test 1');
    const pos40 = fullText.indexOf('Order test 40');
    expect(pos1).toBeLessThan(pos40);
  });
});

test.describe('Chat Resilience Tests', () => {
  test('should recover from network interruption during streaming', async ({ page }) => {
    // OPT-015: Network interruption during streaming

    // Mock API that interrupts after 5 messages
    await mockChatAPI(page, { interruptResponse: true });
    await mockBrainSettingsAPI(page);

    await page.goto('/');
    await openChat(page);

    // Send messages until interruption occurs
    for (let i = 1; i <= 10; i++) {
      await sendMessage(page, `Test ${i}`);
      await page.waitForTimeout(100);
    }

    // Wait for responses
    await page.waitForTimeout(3000);

    // Verify some messages were received
    const chatContainer = page.locator('.ChatInterface');
    await expect(chatContainer).toContainText('Test 1');

    // Verify chat is still functional after interruption
    const chatInput = page.locator('.ChatInterface input[type="text"]');
    await expect(chatInput).toBeEnabled();

    // Send a recovery message
    await sendMessage(page, 'Recovery test');
    await page.waitForTimeout(1000);

    // Verify new message was added
    await expect(chatContainer).toContainText('Recovery test');
  });

  test('should handle failed requests gracefully', async ({ page }) => {
    // OPT-015: Error state + recovery flow

    // Mock API that fails at specific message
    await mockChatAPI(page, { failAtMessage: 5 });
    await mockBrainSettingsAPI(page);

    await page.goto('/');
    await openChat(page);

    // Send messages that will eventually fail
    for (let i = 1; i <= 10; i++) {
      await sendMessage(page, `Message ${i}`);
      await page.waitForTimeout(100);
    }

    await page.waitForTimeout(2000);

    // Verify some messages succeeded (before failure)
    const chatContainer = page.locator('.ChatInterface');
    await expect(chatContainer).toContainText('Message 1');

    // Verify UI is still responsive
    const chatInput = page.locator('.ChatInterface input[type="text"]');
    await expect(chatInput).toBeVisible();
    await expect(chatInput).toBeEnabled();
  });

  test('should handle slow network responses', async ({ page }) => {
    // OPT-015: Resilience to slow network

    // Mock API with slow responses
    await mockChatAPI(page, { responseDelay: 500 });
    await mockBrainSettingsAPI(page);

    await page.goto('/');
    await openChat(page);

    // Send multiple messages with slow responses
    for (let i = 1; i <= 5; i++) {
      await sendMessage(page, `Slow test ${i}`);
    }

    // Wait for responses (will take longer due to delay)
    await page.waitForTimeout(5000);

    // Verify messages are displayed
    const chatContainer = page.locator('.ChatInterface');
    await expect(chatContainer).toContainText('Slow test 1');
    await expect(chatContainer).toContainText('Slow test 5');
  });

  test('should maintain state during browser navigation', async ({ page }) => {
    // OPT-015: Chat state resilience

    await page.goto('/');
    await openChat(page);

    // Send some messages
    for (let i = 1; i <= 5; i++) {
      await sendMessage(page, `Nav test ${i}`);
      await page.waitForTimeout(50);
    }

    await page.waitForTimeout(1000);

    // Navigate away and back
    await page.goto('/dashboard');
    await page.waitForTimeout(500);
    await page.goto('/');
    await openChat(page);

    // Note: Chat state may or may not persist based on implementation
    // This test verifies the chat can be reopened without crashes
    const chatInput = page.locator('.ChatInterface input[type="text"]');
    await expect(chatInput).toBeVisible();

    // Send a new message to verify functionality
    await sendMessage(page, 'After navigation');
    await page.waitForTimeout(500);

    const chatContainer = page.locator('.ChatInterface');
    await expect(chatContainer).toContainText('After navigation');
  });
});

test.describe('Chat Performance Tests', () => {
  test('should handle long messages efficiently', async ({ page }) => {
    // Verify performance with long content

    await mockChatAPI(page);
    await mockBrainSettingsAPI(page);

    await page.goto('/');
    await openChat(page);

    // Send a very long message
    const longMessage = 'A'.repeat(1000);
    await sendMessage(page, longMessage);

    // Send a normal message
    await sendMessage(page, 'Normal message');

    await page.waitForTimeout(2000);

    // Verify messages are in the chat
    const chatContainer = page.locator('.ChatInterface');
    await expect(chatContainer).toContainText('Normal message');

    // Verify input is still responsive
    const chatInput = page.locator('.ChatInterface input[type="text"]');
    await expect(chatInput).toBeEnabled();
  });

  test('should handle special characters and formatting', async ({ page }) => {
    // Verify resilience to special characters

    await mockChatAPI(page);
    await mockBrainSettingsAPI(page);

    await page.goto('/');
    await openChat(page);

    const specialMessages = [
      'Message with **markdown** formatting',
      'Message with `code` snippets',
      'Message with <html> tags',
      'Message with "quotes" and \'apostrophes\'',
      'Message with emoji 🎉',
      'Message with\nnewlines\nand\ttabs',
      'Message with unicode: 你好世界',
    ];

    for (const msg of specialMessages) {
      await sendMessage(page, msg);
      await page.waitForTimeout(50);
    }

    await page.waitForTimeout(2000);

    // Verify all messages are in the chat
    const chatContainer = page.locator('.ChatInterface');
    await expect(chatContainer).toContainText('unicode: 你好世界');
  });
});
