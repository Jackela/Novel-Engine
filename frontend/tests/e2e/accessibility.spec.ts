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
import AxeBuilder from '@axe-core/playwright';

test.describe('Keyboard-Only User Journey', () => {
  test.beforeEach(async ({ page }) => {
    // Start at Character Selection
    await page.goto('/');
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
  });

  /**
   * Test 1: Complete keyboard navigation through CharacterSelection
   */
  test('should navigate CharacterSelection using only keyboard', async ({ page }) => {
    // Skip link should be first focusable element
    await page.keyboard.press('Tab');
    const skipLink = page.getByText('Skip to main content');
    await expect(skipLink).toBeFocused();
    
    // Press Enter on skip link
    await page.keyboard.press('Enter');
    
    // Should jump to main content
    const mainContent = page.locator('#main-content, [role="main"], main').first();
    await expect(mainContent).toBeVisible();
    
    // Tab to first character card
    await page.keyboard.press('Tab');
    const firstCard = page.getByRole('button', { name: /select character/i }).first();
    await expect(firstCard).toBeFocused();
    
    // Select character with Enter key
    await page.keyboard.press('Enter');
    await expect(firstCard).toHaveAttribute('aria-pressed', 'true');
    
    // Navigate to next card with arrow keys
    await page.keyboard.press('ArrowRight');
    const secondCard = page.getByRole('button', { name: /select character/i }).nth(1);
    await expect(secondCard).toBeFocused();
    
    // Select second character with Space key
    await page.keyboard.press(' ');
    await expect(secondCard).toHaveAttribute('aria-pressed', 'true');
    
    // Tab to confirm button
    let tabCount = 0;
    while (tabCount < 20) { // Prevent infinite loop
      await page.keyboard.press('Tab');
      tabCount++;
      
      const confirmButton = page.getByRole('button', { name: /confirm/i });
      if (await confirmButton.isVisible()) {
        const isFocused = await confirmButton.evaluate(el => el === document.activeElement);
        if (isFocused) break;
      }
    }
    
    const confirmButton = page.getByRole('button', { name: /confirm/i });
    await expect(confirmButton).toBeFocused();
    await expect(confirmButton).toBeEnabled();
  });

  /**
   * Test 2: Arrow key navigation in character grid
   */
  test('should support arrow key navigation in grid', async ({ page }) => {
    // Focus first card
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab'); // Skip skip-link
    
    const firstCard = page.getByRole('button', { name: /select character/i }).first();
    await expect(firstCard).toBeFocused();
    
    // Right arrow should move to next card
    await page.keyboard.press('ArrowRight');
    const secondCard = page.getByRole('button', { name: /select character/i }).nth(1);
    await expect(secondCard).toBeFocused();
    
    // Down arrow should move down a row (assuming 3-column grid)
    await page.keyboard.press('ArrowDown');
    const cardBelowSecond = page.getByRole('button', { name: /select character/i }).nth(4);
    await expect(cardBelowSecond).toBeFocused();
    
    // Up arrow should move back up
    await page.keyboard.press('ArrowUp');
    await expect(secondCard).toBeFocused();
    
    // Left arrow should move back
    await page.keyboard.press('ArrowLeft');
    await expect(firstCard).toBeFocused();
  });

  /**
   * Test 3: No accessibility violations on CharacterSelection
   */
  test('should have no accessibility violations on CharacterSelection', async ({ page }) => {
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  /**
   * Test 4: No accessibility violations on Dashboard
   */
  test('should have no accessibility violations on Dashboard', async ({ page }) => {
    // Navigate to dashboard
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  /**
   * Test 5: Focus indicators are visible
   */
  test('should show visible focus indicators', async ({ page }) => {
    // Tab to first interactive element
    await page.keyboard.press('Tab');
    
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();
    
    // Check focus indicator is visible (outline or custom styling)
    const outlineStyle = await focusedElement.evaluate(el => {
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
    // Enable screen reader simulation
    await page.evaluate(() => {
      // Track aria-live announcements
      (window as any).announcements = [];
      
      const observer = new MutationObserver((mutations) => {
        mutations.forEach(mutation => {
          const target = mutation.target as HTMLElement;
          if (target.getAttribute('aria-live')) {
            (window as any).announcements.push(target.textContent);
          }
        });
      });
      
      observer.observe(document.body, {
        childList: true,
        subtree: true,
        characterData: true,
      });
    });
    
    // Select a character
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Enter');
    
    // Wait for announcement
    await page.waitForTimeout(500);
    
    // Check announcements were made
    const announcements = await page.evaluate(() => (window as any).announcements);
    expect(announcements.length).toBeGreaterThan(0);
  });
});
