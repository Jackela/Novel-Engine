/**
 * E2E Accessibility Test (T073)
 * 
 * Tests keyboard-only user journey through the application
 * Verifies that all interactive elements are reachable and operable via keyboard
 * 
 * User Story: As a keyboard-only user, I can navigate from CharacterSelection to Dashboard
 * using only keyboard (no mouse required)
 */

import { test, expect } from '@playwright/test';

test.describe('Keyboard-Only User Journey', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    const demoButton = page.getByRole('button', { name: /view demo/i });
    if (await demoButton.count()) {
      await demoButton.click();
    }
    await page.waitForSelector('[data-testid="dashboard-layout"]');
  });

  /**
   * Test 1: Complete keyboard navigation through CharacterSelection
   */
  test('should allow keyboard navigation to Quick Actions and main content', async ({ page }) => {
    const skipLink = page.getByText('Skip to main content');
    await skipLink.focus();
    await expect(skipLink).toBeFocused();
    await page.keyboard.press('Enter');
    
    const mainContent = page.locator('#main-content, [role="main"], main').first();
    await expect(mainContent).toBeVisible();
    
    // Tab until play button is focused
    let guard = 0;
    while (guard < 25) {
      const active = await page.evaluate(() => document.activeElement?.getAttribute('data-testid'));
      if (active === 'quick-action-play') break;
      await page.keyboard.press('Tab');
      guard++;
    }
    const playButton = page.getByTestId('quick-action-play');
    await expect(playButton).toBeFocused();
  });

  /**
   * Test 2: Arrow key navigation in character grid
   */
  test('should activate quick actions via keyboard', async ({ page }) => {
    await page.focus('[data-testid="quick-action-play"]');
    await page.keyboard.press('Enter');
    await page.focus('[data-testid="quick-action-stop"]');
    await page.keyboard.press(' ');
    await page.focus('[data-testid="quick-action-refresh"]');
    await page.keyboard.press('Enter');
  });

  /**
   * Test 3: No accessibility violations on CharacterSelection
   */
  test('should expose accessible names for quick actions', async ({ page }) => {
    const playButton = page.getByTestId('quick-action-play');
    const refreshButton = page.getByTestId('quick-action-refresh');
    await expect(playButton).toHaveAttribute('aria-label', /start|pause|resume/i);
    await expect(refreshButton).toHaveAttribute('aria-label', /refresh/i);
  });

  /**
   * Test 5: Focus indicators are visible
   */
  test('should show visible focus indicators', async ({ page }) => {
    // Tab to first interactive element
    const playButton = page.getByTestId('quick-action-play');
    await playButton.focus();
    await expect(playButton).toBeFocused();
    
    // Check focus indicator is visible (outline or custom styling)
    const outlineStyle = await playButton.evaluate(el => {
      const styles = window.getComputedStyle(el);
      return {
        outline: styles.outline,
        outlineWidth: styles.outlineWidth,
        outlineStyle: styles.outlineStyle,
        boxShadow: styles.boxShadow,
      };
    });
    
    // Should have some form of visual focus indicator
    const hasFocusIndicator = 
      (outlineStyle.outlineWidth !== '0px' && outlineStyle.outlineStyle !== 'none') ||
      outlineStyle.boxShadow !== 'none';
    
    expect(hasFocusIndicator).toBe(true);
  });

  /**
   * Test 6: Screen reader announcements work correctly
   */
  test('should announce selection changes to screen readers', async ({ page }) => {
    await page.evaluate(() => {
      (window as any).__announcements = [];
      const observer = new MutationObserver((mutations) => {
        mutations.forEach(mutation => {
          const target = mutation.target as HTMLElement;
          if (target.getAttribute('aria-live')) {
            (window as any).__announcements.push(target.textContent);
          }
        });
      });
      observer.observe(document.body, { subtree: true, childList: true, characterData: true });
    });
    
    const playButton = page.getByTestId('quick-action-play');
    const pauseButton = page.getByTestId('quick-action-pause');

    await playButton.focus();
    await page.keyboard.press('Enter');
    await expect(pauseButton).toBeEnabled();
    await pauseButton.focus();
    await page.keyboard.press('Enter');
    await page.waitForTimeout(500);
    
    const announcements = await page.evaluate(() => (window as any).__announcements || []);
    expect(announcements.length).toBeGreaterThan(0);
  });
});
