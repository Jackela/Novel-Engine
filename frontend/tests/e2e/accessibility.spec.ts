/**
 * E2E Accessibility Test (T073)
 * 
 * Tests keyboard-only user journey through the application
 * Verifies that all interactive elements are reachable and operable via keyboard
 * 
 * User Story: As a keyboard-only user, I can navigate from CharacterSelection to Dashboard
 * using only keyboard (no mouse required)
 */

import { test, expect } from './fixtures';
import type { Locator, Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { DashboardPage } from './pages/DashboardPage';

const ACCESSIBILITY_IGNORED_RULES = ['color-contrast', 'list', 'scrollable-region-focusable'];

const focusViaTab = async (page: Page, locator: Locator, maxPresses = 40) => {
  await locator.waitFor({ state: 'visible' });
  for (let i = 0; i < maxPresses; i++) {
    const isFocused = await locator.evaluate((el) => el === document.activeElement).catch(() => false);
    if (isFocused) return;
    await page.keyboard.press('Tab');
  }
  throw new Error('Unable to reach locator via keyboard navigation');
};

const activateDemoCtaWithKeyboard = async (page: Page) => {
  const dashboardPage = new DashboardPage(page);
  await dashboardPage.setupDefaultMocks();
  const skipLink = page.getByText('Skip to main content');
  await skipLink.waitFor({ state: 'visible' });
  await page.evaluate(() => {
    try {
      document.body.focus();
    } catch {
      // ignore focus errors
    }
  });
  await page.keyboard.press('Tab');
  await expect(skipLink).toBeFocused();
  await page.keyboard.press('Enter');

  const ctaButton = page.locator('[data-testid="cta-launch"]');
  await ctaButton.waitFor({ state: 'visible' });
  await page.keyboard.press('Tab');
  await expect(ctaButton).toBeFocused();
  await page.keyboard.press('Enter');

  await dashboardPage.waitForDashboardLoad();
  return dashboardPage;
};

test.describe('Keyboard-Only User Journey', () => {
  test.beforeEach(async ({ page }) => {
    const navigate = async () => {
      await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 45000 });
    };
    try {
      await navigate();
    } catch {
      await page.waitForTimeout(2000);
      await navigate();
    }
  });

  /**
   * Test 1: Complete keyboard navigation through CharacterSelection
   */
  test('Skip link jumps to CTA region', async ({ page }) => {
    await page.evaluate(() => {
      try {
        document.body.focus();
      } catch {
        // ignore focus errors
      }
    });
    await page.keyboard.press('Tab');
    const skipLink = page.getByText('Skip to main content');
    await expect(skipLink).toBeFocused();
    await page.keyboard.press('Enter');

    const mainContent = page.locator('#main-content');
    await expect(mainContent).toBeVisible();
    await expect(page.locator('[data-testid="cta-launch"]')).toBeVisible();
  });

  /**
   * Test 2: Arrow key navigation in character grid
   */
  test('Quick Actions support keyboard navigation', async ({ page }) => {
    const dashboardPage = await activateDemoCtaWithKeyboard(page);

    const playButton = dashboardPage.playButton.first();
    await focusViaTab(page, playButton);
    await expect(playButton).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(dashboardPage.liveIndicator).toBeVisible();

    const pauseButton = dashboardPage.pauseButton.first();
    await focusViaTab(page, pauseButton);
    await expect(pauseButton).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(
      dashboardPage.turnPipelineStatus.locator('[data-testid="pipeline-run-state"]'),
    ).toHaveText(/Paused|Idle/i);
  });

  /**
   * Test 3: No accessibility violations on CharacterSelection
   */
  test('should have no accessibility violations on landing page', async ({ page }) => {
    const accessibilityScanResults = await new AxeBuilder({ page })
      .disableRules(ACCESSIBILITY_IGNORED_RULES)
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  /**
   * Test 4: No accessibility violations on Dashboard
   */
  test('should have no accessibility violations on Dashboard', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);
    await dashboardPage.navigateToDashboard({ mockAPIs: true });

    const accessibilityScanResults = await new AxeBuilder({ page })
      .disableRules(ACCESSIBILITY_IGNORED_RULES)
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  /**
   * Test 5: Focus indicators are visible
   */
  test('should show visible focus indicators', async ({ page }) => {
    const dashboardPage = await activateDemoCtaWithKeyboard(page);
    const playButton = dashboardPage.playButton.first();
    await focusViaTab(page, playButton);
    await expect(playButton).toBeFocused();

    const outlineStyle = await playButton.evaluate((el) => {
      const styles = window.getComputedStyle(el);
      return {
        outline: styles.outline,
        outlineWidth: styles.outlineWidth,
        outlineStyle: styles.outlineStyle,
        boxShadow: styles.boxShadow,
      };
    });

    const hasFocusIndicator =
      (outlineStyle.outlineWidth !== '0px' && outlineStyle.outlineStyle !== 'none') ||
      outlineStyle.boxShadow !== 'none';

    expect(hasFocusIndicator).toBe(true);
  });

  /**
   * Test 6: Screen reader announcements work correctly
   */
  test('should announce connection state updates to screen readers', async ({ page }) => {
    const dashboardPage = await activateDemoCtaWithKeyboard(page);
    await focusViaTab(page, dashboardPage.playButton.first());

    const indicator = page.locator('[data-testid="pipeline-live-indicator"]');
    await expect(indicator).toHaveAttribute('aria-live', 'polite');
    const initialLabel = await indicator.textContent();
    await page.keyboard.press('Enter');
    await expect(indicator).not.toHaveText(initialLabel || '');
  });
});
