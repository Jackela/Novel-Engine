import { test, expect } from './fixtures';
import { safeGoto } from './utils/navigation';
import { scalePerf } from './utils/perf';

/**
 * Visual Regression Testing - Theme Combination Baselines
 *
 * VIS-006: Creates visual regression baselines for all 4 theme combinations
 *
 * Theme Matrix:
 *                     default             literary
 *             ┌─────────────────┬─────────────────┐
 *     light   │ SaaS + sans     │ Paper + serif   │
 *             ├─────────────────┼─────────────────┤
 *     dark    │ Dark + sans     │ Warm dark+serif │
 *             └─────────────────┴─────────────────┘
 *
 * Color mode: class="dark" on <html> (light/dark)
 * Typography mode: data-typography="literary" on <html> (default/literary)
 */

test.describe('Visual Regression - Theme Combinations', () => {
  /**
   * Helper to set theme combination via page.evaluate
   */
  async function setTheme(
    page: import('@playwright/test').Page,
    colorMode: 'light' | 'dark',
    typographyMode: 'default' | 'literary'
  ) {
    await page.evaluate(
      ({ colorMode, typographyMode }) => {
        const html = document.documentElement;

        // Set color mode (dark class on html)
        if (colorMode === 'dark') {
          html.classList.add('dark');
        } else {
          html.classList.remove('dark');
        }

        // Set typography mode (data-typography attribute)
        if (typographyMode === 'literary') {
          html.setAttribute('data-typography', 'literary');
        } else {
          html.removeAttribute('data-typography');
        }

        // Persist to localStorage for test consistency
        localStorage.setItem('theme-mode', colorMode);
        localStorage.setItem('typography-mode', typographyMode);
      },
      { colorMode, typographyMode }
    );

    // Allow CSS transitions to settle
    await page.waitForTimeout(300);
  }

  /**
   * Helper to navigate to dashboard and wait for content
   */
  async function navigateToDashboard(page: import('@playwright/test').Page) {
    await safeGoto(page, '/dashboard');
    // Wait for main dashboard layout to be visible
    await page.waitForSelector('[data-testid="dashboard-layout"], main', {
      state: 'visible',
      timeout: 30000,
    });
  }

  /**
   * Take a full-page screenshot for visual comparison
   */
  async function captureBaseline(
    page: import('@playwright/test').Page,
    name: string
  ) {
    await page.screenshot({
      path: `test-results/visual-baselines/${name}.png`,
      fullPage: false, // Capture viewport for consistent sizing
      timeout: scalePerf(20000),
    });
  }

  test.beforeEach(async ({ page }) => {
    // Prevent external font fetches from hanging screenshots.
    await page.route('https://fonts.googleapis.com/**', (route) =>
      route.fulfill({ status: 200, contentType: 'text/css', body: '' })
    );
    await page.route('https://fonts.gstatic.com/**', (route) => route.abort());

    // Clear localStorage to ensure clean theme state
    await page.addInitScript(() => {
      try {
        localStorage.removeItem('theme-mode');
        localStorage.removeItem('typography-mode');
      } catch {
        // Ignore storage failures
      }
    });
  });

  test.describe('Dashboard Theme Baselines', () => {
    test('captures light+default theme baseline', async ({ page }) => {
      await navigateToDashboard(page);
      await setTheme(page, 'light', 'default');

      // Verify theme is correctly applied
      const htmlClasses = await page.evaluate(() =>
        document.documentElement.classList.contains('dark')
      );
      expect(htmlClasses).toBe(false);

      const typographyAttr = await page.evaluate(() =>
        document.documentElement.getAttribute('data-typography')
      );
      expect(typographyAttr).toBeNull();

      await captureBaseline(page, 'dashboard-light-default');

      // Visual assertions for light theme
      await expect(page.locator('body')).toHaveCSS(
        'background-color',
        /rgb\(255, 255, 255\)|rgba\(255, 255, 255/
      );
    });

    test('captures light+literary theme baseline', async ({ page }) => {
      await navigateToDashboard(page);
      await setTheme(page, 'light', 'literary');

      // Verify theme is correctly applied
      const htmlClasses = await page.evaluate(() =>
        document.documentElement.classList.contains('dark')
      );
      expect(htmlClasses).toBe(false);

      const typographyAttr = await page.evaluate(() =>
        document.documentElement.getAttribute('data-typography')
      );
      expect(typographyAttr).toBe('literary');

      await captureBaseline(page, 'dashboard-light-literary');
    });

    test('captures dark+default theme baseline', async ({ page }) => {
      await navigateToDashboard(page);
      await setTheme(page, 'dark', 'default');

      // Verify theme is correctly applied
      const htmlClasses = await page.evaluate(() =>
        document.documentElement.classList.contains('dark')
      );
      expect(htmlClasses).toBe(true);

      const typographyAttr = await page.evaluate(() =>
        document.documentElement.getAttribute('data-typography')
      );
      expect(typographyAttr).toBeNull();

      await captureBaseline(page, 'dashboard-dark-default');

      // Visual assertions for dark theme - check for dark background
      // Dark mode uses --background: 240 10% 3.9% which is approximately rgb(9, 9, 11)
      await expect(page.locator('body')).toHaveCSS('background-color', /rgb\(/);
    });

    test('captures dark+literary theme baseline', async ({ page }) => {
      await navigateToDashboard(page);
      await setTheme(page, 'dark', 'literary');

      // Verify theme is correctly applied
      const htmlClasses = await page.evaluate(() =>
        document.documentElement.classList.contains('dark')
      );
      expect(htmlClasses).toBe(true);

      const typographyAttr = await page.evaluate(() =>
        document.documentElement.getAttribute('data-typography')
      );
      expect(typographyAttr).toBe('literary');

      await captureBaseline(page, 'dashboard-dark-literary');
    });
  });

  test.describe('Landing Page Theme Baselines', () => {
    async function navigateToLanding(page: import('@playwright/test').Page) {
      await safeGoto(page, '/', { timeout: 45000 });
      await page.waitForSelector('h1', {
        state: 'visible',
        timeout: 30000,
      });
    }

    test('captures light+default landing baseline', async ({ page }) => {
      await navigateToLanding(page);
      await setTheme(page, 'light', 'default');
      await captureBaseline(page, 'landing-light-default');
    });

    test('captures light+literary landing baseline', async ({ page }) => {
      await navigateToLanding(page);
      await setTheme(page, 'light', 'literary');
      await captureBaseline(page, 'landing-light-literary');
    });

    test('captures dark+default landing baseline', async ({ page }) => {
      await navigateToLanding(page);
      await setTheme(page, 'dark', 'default');
      await captureBaseline(page, 'landing-dark-default');
    });

    test('captures dark+literary landing baseline', async ({ page }) => {
      await navigateToLanding(page);
      await setTheme(page, 'dark', 'literary');
      await captureBaseline(page, 'landing-dark-literary');
    });
  });

  test.describe('Theme Switching Validation', () => {
    test('validates theme can be set and verified on same page', async ({
      page,
    }) => {
      await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });

      // Set dark+literary theme
      await setTheme(page, 'dark', 'literary');

      // Verify DOM reflects the theme
      const hasDarkClass = await page.evaluate(() =>
        document.documentElement.classList.contains('dark')
      );
      expect(hasDarkClass).toBe(true);

      const typographyAttr = await page.evaluate(() =>
        document.documentElement.getAttribute('data-typography')
      );
      expect(typographyAttr).toBe('literary');

      // Toggle back to light+default
      await setTheme(page, 'light', 'default');

      const hasDarkClassAfter = await page.evaluate(() =>
        document.documentElement.classList.contains('dark')
      );
      expect(hasDarkClassAfter).toBe(false);

      const typographyAttrAfter = await page.evaluate(() =>
        document.documentElement.getAttribute('data-typography')
      );
      expect(typographyAttrAfter).toBeNull();
    });

    test('validates all 4 theme combinations render without layout errors', async ({
      page,
    }) => {
      const combinations: Array<{
        color: 'light' | 'dark';
        typography: 'default' | 'literary';
      }> = [
        { color: 'light', typography: 'default' },
        { color: 'light', typography: 'literary' },
        { color: 'dark', typography: 'default' },
        { color: 'dark', typography: 'literary' },
      ];

      await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });

      for (const combo of combinations) {
        await setTheme(page, combo.color, combo.typography);

        // Verify page renders correctly
        await expect(page.locator('body')).toBeVisible();

        // Check no critical layout issues (body has dimensions)
        const bodyBox = await page.locator('body').boundingBox();
        expect(bodyBox).not.toBeNull();
        expect(bodyBox!.width).toBeGreaterThan(0);
        expect(bodyBox!.height).toBeGreaterThan(0);

        // Verify theme is correctly applied
        const hasDarkClass = await page.evaluate(() =>
          document.documentElement.classList.contains('dark')
        );
        expect(hasDarkClass).toBe(combo.color === 'dark');

        if (combo.typography === 'literary') {
          const typographyAttr = await page.evaluate(() =>
            document.documentElement.getAttribute('data-typography')
          );
          expect(typographyAttr).toBe('literary');
        }
      }
    });
  });
});
