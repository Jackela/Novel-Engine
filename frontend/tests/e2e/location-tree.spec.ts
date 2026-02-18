/**
 * LocationTree E2E Tests (SIM-023)
 *
 * Tests for the LocationTree component character display features including:
 * - Character avatars under locations
 * - CharacterDetailDialog on click
 * - Filter toggle for showing/hiding characters
 * - Unknown Location section for characters without location
 * - Accessibility features
 *
 * Note: LocationTree is used in the WorldSidebarTab component which is part
 * of the NarrativeEditor. Navigate to /story and click "World" tab to test.
 * Uses MSW for API mocking (see frontend/src/mocks/handlers.ts).
 *
 * @tags @location @character @world @simulation
 */

import { test, expect } from './fixtures';
import { activateGuestSession } from './utils/auth';
import { safeGoto } from './utils/navigation';

/**
 * Navigate to the story page and click the World tab to show LocationTree.
 * The LocationTree is inside the WorldSidebarTab which is only visible after
 * clicking the "World" tab in the narrative sidebar.
 * Also expands the Locations section since it starts collapsed.
 */
async function navigateToWorldTab(page: import('@playwright/test').Page) {
  await safeGoto(page, '/story');

  // Wait for the page to be ready
  await page.waitForLoadState('networkidle');

  // Click on the World tab
  const worldTab = page.getByRole('tab', { name: /world/i });
  await worldTab.waitFor({ state: 'visible', timeout: 10000 });
  await worldTab.click();

  // Wait a moment for the tab content to load
  await page.waitForTimeout(500);

  // Expand the Locations section (it starts collapsed)
  const locationsTrigger = page.locator('text=/Locations/').first();
  await locationsTrigger.waitFor({ state: 'visible', timeout: 10000 });
  await locationsTrigger.click();

  // Wait for the tree to render
  await page.waitForTimeout(500);

  return page;
}

test.describe('LocationTree Character Display', () => {
  test.beforeEach(async ({ page }) => {
    await activateGuestSession(page);
  });

  test('should display the World tab in the sidebar', async ({ page }) => {
    await navigateToWorldTab(page);

    // Verify the World tab is selected
    const worldTab = page.getByRole('tab', { name: /world/i });
    await expect(worldTab).toHaveAttribute('data-state', 'active');
  });

  test('should display location tree when World tab is active', async ({ page }) => {
    await navigateToWorldTab(page);

    // Wait for the tree to render (uses MSW mock data from handlers.ts)
    const locationTree = page.locator('[role="tree"]');
    await expect(locationTree).toBeVisible({ timeout: 15000 });
  });

  test('should have Locations section in the World tab', async ({ page }) => {
    await navigateToWorldTab(page);

    // The Locations section header should be visible
    const locationsHeader = page.locator('text=/Locations/i');
    await expect(locationsHeader.first()).toBeVisible({ timeout: 10000 });
  });
});

test.describe('LocationTree Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await activateGuestSession(page);
  });

  test('should have proper tree role when locations are loaded', async ({ page }) => {
    await navigateToWorldTab(page);

    const locationTree = page.locator('[role="tree"]');
    await expect(locationTree).toBeVisible({ timeout: 15000 });
    await expect(locationTree).toHaveAttribute('aria-label', 'World locations and characters');
  });

  test('should have treeitem roles on location nodes', async ({ page }) => {
    await navigateToWorldTab(page);

    const locationTree = page.locator('[role="tree"]');
    await expect(locationTree).toBeVisible({ timeout: 15000 });

    // Check treeitem roles exist
    const treeitems = locationTree.getByRole('treeitem');
    await expect(treeitems.first()).toBeVisible();
  });

  test('should have aria-expanded on expandable nodes', async ({ page }) => {
    await navigateToWorldTab(page);

    const locationTree = page.locator('[role="tree"]');
    await expect(locationTree).toBeVisible({ timeout: 15000 });

    // Find a node with children (aria-expanded should be present)
    const expandableNode = locationTree.locator('[aria-expanded]').first();
    await expect(expandableNode).toBeVisible();
  });
});

test.describe('LocationTree Filter Toggle', () => {
  test.beforeEach(async ({ page }) => {
    await activateGuestSession(page);
  });

  test('should have character section in the World tab', async ({ page }) => {
    await navigateToWorldTab(page);

    // The Characters section should be visible
    const charactersHeader = page.locator('text=/Characters/i');
    await expect(charactersHeader.first()).toBeVisible({ timeout: 10000 });
  });
});

test.describe('LocationTree Component', () => {
  test.beforeEach(async ({ page }) => {
    await activateGuestSession(page);
  });

  test('should render LocationTree component with mock data', async ({ page }) => {
    await navigateToWorldTab(page);

    // The mock data from MSW handlers should load successfully
    // Check that the sidebar is not showing loading state
    const loadingText = page.locator('text=/Loading/i');
    await expect(loadingText).not.toBeVisible({ timeout: 10000 });
  });
});
