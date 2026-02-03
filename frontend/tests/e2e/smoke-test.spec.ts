/**
 * Smoke Test - Route Verification
 *
 * Verifies all main routes are accessible and don't return 404.
 * This is the first line of defense against broken routing.
 *
 * @tags @smoke @routes
 */

import { test, expect } from './fixtures';
import { activateGuestSession } from './utils/auth';

test.describe('Route Smoke Tests', () => {
  test.describe('@smoke Public Routes', () => {
    test('@smoke landing page (/) should load without 404', async ({ page }) => {
      await page.goto('/', { waitUntil: 'domcontentloaded' });

      // Should not contain 404 text
      const content = await page.textContent('body');
      expect(content).not.toContain('404');
      expect(content).not.toContain('Not Found');

      // Should have the landing page content
      await expect(page.getByText('Novel Engine')).toBeVisible();
    });

    test('@smoke login page (/login) should load without 404', async ({ page }) => {
      await page.goto('/login', { waitUntil: 'domcontentloaded' });

      const content = await page.textContent('body');
      expect(content).not.toContain('404');
      expect(content).not.toContain('Not Found');
    });

    test('@smoke weaver page (/weaver) should load without 404', async ({ page }) => {
      await page.goto('/weaver', { waitUntil: 'domcontentloaded' });

      const content = await page.textContent('body');
      expect(content).not.toContain('404');
      expect(content).not.toContain('Not Found');

      // Weaver page should have Story Weaver heading
      await expect(page.getByRole('heading', { name: 'Story Weaver' })).toBeVisible();
    });
  });

  test.describe('@smoke Protected Routes (with auth bypass)', () => {
    test.beforeEach(async ({ page }) => {
      await activateGuestSession(page);
    });

    test('@smoke dashboard (/dashboard) should load without 404', async ({ page }) => {
      await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });

      const content = await page.textContent('body');
      expect(content).not.toContain('404');
      expect(content).not.toContain('Not Found');

      // Dashboard should have Dashboard heading
      await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
    });

    test('@smoke characters page (/characters) should load without 404', async ({ page }) => {
      await page.goto('/characters', { waitUntil: 'domcontentloaded' });

      const content = await page.textContent('body');
      expect(content).not.toContain('404');
      expect(content).not.toContain('Not Found');
    });

    test('@smoke campaigns page (/campaigns) should load without 404', async ({ page }) => {
      await page.goto('/campaigns', { waitUntil: 'domcontentloaded' });

      const content = await page.textContent('body');
      expect(content).not.toContain('404');
      expect(content).not.toContain('Not Found');
    });

    test('@smoke stories page (/stories) should load without 404', async ({ page }) => {
      await page.goto('/stories', { waitUntil: 'domcontentloaded' });

      const content = await page.textContent('body');
      expect(content).not.toContain('404');
      expect(content).not.toContain('Not Found');

      // Stories page should have Story Library heading
      await expect(page.getByRole('heading', { name: 'Story Library' })).toBeVisible();
    });

    test('@smoke story editor page (/stories/editor) should load without 404', async ({
      page,
    }) => {
      await page.goto('/stories/editor', { waitUntil: 'domcontentloaded' });

      const content = await page.textContent('body');
      expect(content).not.toContain('404');
      expect(content).not.toContain('Not Found');
    });
  });

  test.describe('@smoke Navigation Links', () => {
    test.beforeEach(async ({ page }) => {
      await activateGuestSession(page);
    });

    test('@smoke sidebar navigation links should all be functional', async ({ page }) => {
      await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });

      // Wait for sidebar to be visible
      const sidebar = page.locator('[data-testid="sidebar-navigation"]');
      await expect(sidebar).toBeAttached({ timeout: 5000 });

      // Check all navigation links exist and are clickable
      const navLinks = [
        { name: 'Dashboard', path: '/dashboard' },
        { name: 'Characters', path: '/characters' },
        { name: 'Campaigns', path: '/campaigns' },
        { name: 'Stories', path: '/stories' },
        { name: 'Weaver', path: '/weaver' },
      ];

      for (const { name, path } of navLinks) {
        const link = sidebar.locator(`a[href="${path}"]`);
        await expect(link).toBeAttached();
        // Verify link text contains the name
        await expect(link).toContainText(name);
      }
    });
  });
});
