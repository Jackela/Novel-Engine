import { test, expect } from '@playwright/test';
import { LandingPage } from './pages/LandingPage';

/**
 * Landing Page E2E Test Suite
 *
 * OpenSpec: complete-e2e-tdd-evolution
 * Spec: e2e-route-coverage/spec.md - Landing Page E2E Coverage
 *
 * Tests verify:
 * 1. Landing page renders with expected content
 * 2. Navigation to dashboard works
 * 3. Feature cards display correctly
 * 4. Responsive layout at different viewports
 */

test.describe('Landing Page E2E Tests', () => {
  let landingPage: LandingPage;

  test.beforeEach(async ({ page }) => {
    landingPage = new LandingPage(page);
    await landingPage.navigateToLanding();
  });

  test.describe('Scenario: Landing page renders with expected content', () => {
    /**
     * Given: The application is running
     * When: User navigates to `/`
     * Then: The page title "NARRATIVE ENGINE" is visible
     * And: The "Launch Engine" button is present
     * And: Three feature cards are displayed
     */
    test('@landing-smoke should display page title, CTA button, and feature cards', async () => {
      await test.step('Given: Application is running and user navigates to /', async () => {
        // Already navigated in beforeEach
        await expect(landingPage.mainTitle).toBeVisible();
      });

      await test.step('Then: The page title "NARRATIVE ENGINE" is visible', async () => {
        const titleText = await landingPage.getMainTitleText();
        // Title uses <br> between words, so textContent returns them concatenated
        const normalizedTitle = titleText.toUpperCase().replace(/\s+/g, '');
        expect(normalizedTitle).toContain('NARRATIVEENGINE');
      });

      await test.step('And: The "Launch Engine" button is present', async () => {
        await expect(landingPage.launchEngineButton).toBeVisible();
        await expect(landingPage.launchEngineButton).toBeEnabled();
      });

      await test.step('And: Three feature cards are displayed', async () => {
        const cardCount = await landingPage.getFeatureCardCount();
        expect(cardCount).toBe(3);
      });
    });

    test('should display version chip', async () => {
      await expect(landingPage.versionChip).toBeVisible();
      const versionText = await landingPage.getVersionText();
      expect(versionText).toBeTruthy();
    });

    test('should display all three feature cards with correct titles', async () => {
      await test.step('Live Orchestration card is visible', async () => {
        await expect(landingPage.liveOrchestrationCard).toBeVisible();
      });

      await test.step('Adaptive Analytics card is visible', async () => {
        await expect(landingPage.adaptiveAnalyticsCard).toBeVisible();
      });

      await test.step('Secure Environment card is visible', async () => {
        await expect(landingPage.secureEnvironmentCard).toBeVisible();
      });
    });
  });

  test.describe('Scenario: Landing page navigation works', () => {
    /**
     * Given: User is on the landing page
     * When: User clicks "Launch Engine" button
     * Then: User is navigated to `/dashboard`
     */
    test('should navigate to dashboard when clicking Launch Engine', async ({ page }) => {
      await test.step('Given: User is on the landing page', async () => {
        await expect(landingPage.mainTitle).toBeVisible();
      });

      await test.step('When: User clicks "Launch Engine" button', async () => {
        await landingPage.clickLaunchEngine();
      });

      await test.step('Then: User is navigated to /dashboard', async () => {
        await expect(page).toHaveURL(/.*\/dashboard/);
      });
    });
  });

  test.describe('Scenario: Landing page is responsive', () => {
    /**
     * Given: The application is running
     * When: Viewport is set to mobile size (375x667)
     * Then: Content stacks vertically
     * And: Button remains clickable
     */
    test('should adapt layout for mobile viewport (375x667)', async ({ page }) => {
      await test.step('When: Viewport is set to mobile size (375x667)', async () => {
        await page.setViewportSize({ width: 375, height: 667 });
        await page.waitForTimeout(500); // Allow layout reflow
      });

      await test.step('Then: Content stacks vertically and key elements visible', async () => {
        const layout = await landingPage.validateResponsiveLayout();
        expect(layout.titleVisible).toBe(true);
        expect(layout.buttonVisible).toBe(true);
        expect(layout.cardsVisible).toBe(true);
        expect(layout.layoutStacked).toBe(true);
      });

      await test.step('And: Button remains clickable', async () => {
        await expect(landingPage.launchEngineButton).toBeEnabled();
        // Verify button is clickable by checking it's not obscured
        const buttonBox = await landingPage.launchEngineButton.boundingBox();
        expect(buttonBox).not.toBeNull();
        expect(buttonBox!.width).toBeGreaterThan(0);
        expect(buttonBox!.height).toBeGreaterThan(0);
      });

      // Take screenshot for visual verification
      await landingPage.takeScreenshot('landing-mobile-375x667');
    });

    test('should adapt layout for tablet viewport (768x1024)', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.waitForTimeout(500);

      await expect(landingPage.mainTitle).toBeVisible();
      await expect(landingPage.launchEngineButton).toBeVisible();
      await expect(landingPage.launchEngineButton).toBeEnabled();

      const cardCount = await landingPage.getFeatureCardCount();
      expect(cardCount).toBe(3);

      await landingPage.takeScreenshot('landing-tablet-768x1024');
    });

    test('should display correctly on desktop viewport (1440x900)', async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.waitForTimeout(500);

      const layout = await landingPage.validateResponsiveLayout();
      expect(layout.titleVisible).toBe(true);
      expect(layout.buttonVisible).toBe(true);
      expect(layout.cardsVisible).toBe(true);
      expect(layout.layoutStacked).toBe(false); // Desktop should not be stacked

      await landingPage.takeScreenshot('landing-desktop-1440x900');
    });
  });

  test.describe('Accessibility', () => {
    test('should have proper heading hierarchy', async ({ page }) => {
      // Check that h1 exists and is unique
      const h1Count = await page.locator('h1').count();
      expect(h1Count).toBe(1);
    });

    test('should have accessible button', async () => {
      // Button should be focusable and have accessible name
      const button = landingPage.launchEngineButton;
      await expect(button).toBeVisible();

      const buttonText = await button.textContent();
      expect(buttonText?.toLowerCase()).toContain('launch');
    });
  });
});
