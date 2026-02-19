/**
 * Simulation Dashboard E2E Tests (SIM-031)
 *
 * Tests for the SimulationDashboard component including:
 * - Full simulation flow
 * - Preview and commit operations
 * - Snapshot creation and restoration
 * - Accessibility features
 *
 * @tags @simulation @dashboard @e2e
 */

import type { Page } from '@playwright/test';
import { test, expect } from './fixtures';
import { activateGuestSession } from './utils/auth';
import { safeGoto } from './utils/navigation';

// Mock simulation API responses
async function mockSimulationApi(page: Page) {
  // Mock preview simulation
  await page.route('**/api/world/*/simulate/preview', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        tick_id: 'preview-tick-1',
        world_id: 'default-world',
        calendar_before: {
          year: 1,
          month: 1,
          day: 1,
          era_name: 'First Age',
          formatted_date: 'Year 1, Month 1, Day 1 - First Age',
        },
        calendar_after: {
          year: 1,
          month: 1,
          day: 8,
          era_name: 'First Age',
          formatted_date: 'Year 1, Month 1, Day 8 - First Age',
        },
        days_advanced: 7,
        events_generated: [],
        resource_changes: {},
        diplomacy_changes: [],
        created_at: new Date().toISOString(),
      }),
    });
  });

  // Mock commit simulation
  await page.route('**/api/world/*/simulate/commit', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        tick_id: 'commit-tick-1',
        world_id: 'default-world',
        calendar_before: {
          year: 1,
          month: 1,
          day: 1,
          era_name: 'First Age',
          formatted_date: 'Year 1, Month 1, Day 1 - First Age',
        },
        calendar_after: {
          year: 1,
          month: 1,
          day: 2,
          era_name: 'First Age',
          formatted_date: 'Year 1, Month 1, Day 2 - First Age',
        },
        days_advanced: 1,
        events_generated: ['event-1'],
        resource_changes: {},
        diplomacy_changes: [],
        created_at: new Date().toISOString(),
      }),
    });
  });

  // Mock simulation history
  await page.route('**/api/world/*/simulate/history*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ticks: [
          {
            tick_id: 'tick-1',
            days_advanced: 1,
            events_count: 1,
            created_at: new Date().toISOString(),
          },
        ],
        total: 1,
      }),
    });
  });
}

// Mock snapshot API responses
async function mockSnapshotApi(page: Page) {
  // Mock list snapshots
  await page.route('**/api/world/*/snapshots*', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          snapshots: [
            {
              snapshot_id: 'snapshot-1',
              tick_number: 1,
              description: 'Tick 1',
              created_at: new Date().toISOString(),
            },
          ],
          total: 1,
        }),
      });
    } else if (route.request().method() === 'POST') {
      // Create snapshot
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          snapshot_id: 'snapshot-new',
          world_id: 'default-world',
          calendar: {
            year: 1,
            month: 1,
            day: 1,
            era_name: 'First Age',
            formatted: 'Year 1, Month 1, Day 1 - First Age',
          },
          tick_number: 1,
          description: 'Tick 1',
          created_at: new Date().toISOString(),
          size_bytes: 100,
        }),
      });
    }
  });

  // Mock restore snapshot
  await page.route('**/api/world/*/snapshots/*/restore', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        snapshot_id: 'snapshot-1',
        world_id: 'default-world',
        restored: true,
        message: 'Snapshot restored successfully',
      }),
    });
  });
}

// Mock calendar API
async function mockCalendarApiSuccess(page: Page) {
  await page.route('**/api/calendar/*', async (route) => {
    const method = route.request().method();
    if (method === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          year: 1,
          month: 1,
          day: 1,
          era_name: 'First Age',
          formatted_date: 'Year 1, Month 1, Day 1 - First Age',
          days_per_month: 30,
          months_per_year: 12,
        }),
      });
    } else {
      await route.continue();
    }
  });
}

// Mock events API
async function mockEventsApi(page: Page) {
  await page.route('**/api/world/*/events*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        events: [],
        total_count: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      }),
    });
  });
}

// Mock rumors API
async function mockRumorsApi(page: Page) {
  await page.route('**/api/world/*/rumors*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        rumors: [],
        total: 0,
      }),
    });
  });
}

test.describe('Simulation Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await activateGuestSession(page);
    await mockSimulationApi(page);
    await mockSnapshotApi(page);
    await mockCalendarApiSuccess(page);
    await mockEventsApi(page);
    await mockRumorsApi(page);
  });

  test('should navigate to simulation dashboard', async ({ page }) => {
    await safeGoto(page, '/simulation');

    // Verify main dashboard elements are visible
    await expect(page.getByRole('main', { name: 'Simulation Dashboard' })).toBeVisible();
    await expect(page.getByTestId('simulation-controls')).toBeVisible();
    await expect(page.getByTestId('snapshot-controls')).toBeVisible();
  });

  test('should display calendar component', async ({ page }) => {
    await safeGoto(page, '/simulation');

    // Calendar display should be visible
    const calendarDisplay = page.getByTestId('calendar-display');
    await expect(calendarDisplay).toBeVisible();
    await expect(calendarDisplay).toHaveAttribute('data-state', 'success');
  });

  test('should show preview buttons', async ({ page }) => {
    await safeGoto(page, '/simulation');

    const simulationControls = page.getByTestId('simulation-controls');

    // Preview buttons should be visible
    await expect(simulationControls.getByRole('button', { name: /preview 1 day/i })).toBeVisible();
    await expect(simulationControls.getByRole('button', { name: /preview 7 days/i })).toBeVisible();
    await expect(simulationControls.getByRole('button', { name: /preview 30 days/i })).toBeVisible();
  });

  test('should show commit buttons', async ({ page }) => {
    await safeGoto(page, '/simulation');

    const simulationControls = page.getByTestId('simulation-controls');

    // Commit buttons should be visible
    await expect(simulationControls.getByRole('button', { name: /commit 1 day/i })).toBeVisible();
    await expect(simulationControls.getByRole('button', { name: /commit 7 days/i })).toBeVisible();
    await expect(simulationControls.getByRole('button', { name: /commit 30 days/i })).toBeVisible();
  });

  test('should execute preview simulation', async ({ page }) => {
    await safeGoto(page, '/simulation');

    // Click preview 7 days button
    const previewButton = page.getByRole('button', { name: /preview 7 days/i });
    await previewButton.click();

    // Wait for result to appear
    const lastTickResult = page.getByTestId('last-tick-result');
    await expect(lastTickResult).toBeVisible({ timeout: 5000 });

    // Verify the result shows 7 days
    await expect(lastTickResult.getByText('7')).toBeVisible();
  });

  test('should execute commit simulation', async ({ page }) => {
    await safeGoto(page, '/simulation');

    // Click commit 1 day button
    const commitButton = page.getByRole('button', { name: /commit 1 day/i });
    await commitButton.click();

    // Wait for result to appear
    const lastTickResult = page.getByTestId('last-tick-result');
    await expect(lastTickResult).toBeVisible({ timeout: 5000 });

    // Verify the result shows 1 day
    await expect(lastTickResult.getByText('1')).toBeVisible();
  });

  test('should create snapshot', async ({ page }) => {
    await safeGoto(page, '/simulation');

    // Click create snapshot button
    const createSnapshotButton = page.getByRole('button', { name: /create snapshot/i });
    await createSnapshotButton.click();

    // Should show success message (via status update)
    // The snapshot should be created
    await page.waitForTimeout(1000); // Wait for async operation
  });

  test('should display snapshot restore dropdown', async ({ page }) => {
    await safeGoto(page, '/simulation');

    const snapshotControls = page.getByTestId('snapshot-controls');

    // Restore dropdown should be visible
    const restoreTrigger = snapshotControls.getByRole('combobox', { name: /select snapshot/i });
    await expect(restoreTrigger).toBeVisible();
  });

  test('should display events timeline', async ({ page }) => {
    await safeGoto(page, '/simulation');

    // Timeline should be visible (WorldTimeline component)
    // Since there are no events, it should show empty state
    await expect(page.getByText(/no events yet/i)).toBeVisible();
  });

  test('should toggle rumors display', async ({ page }) => {
    await safeGoto(page, '/simulation');

    // Find rumors section
    const rumorsButton = page.getByRole('button', { name: /rumors/i });
    await expect(rumorsButton).toBeVisible();

    // Click to collapse
    await rumorsButton.click();

    // Click to expand again
    await rumorsButton.click();
  });

  test('should display factions section', async ({ page }) => {
    await safeGoto(page, '/simulation');

    // Factions card should be visible
    await expect(page.getByRole('heading', { name: /factions/i })).toBeVisible();

    // Should have link to full matrix
    await expect(page.getByRole('link', { name: /view full matrix/i })).toBeVisible();
  });

  test('should have accessible simulation controls', async ({ page }) => {
    await safeGoto(page, '/simulation');

    // Verify aria labels on buttons
    const previewButton = page.getByRole('button', { name: /preview 1 day/i });
    await expect(previewButton).toHaveAttribute('aria-label', /preview 1 day/i);

    const commitButton = page.getByRole('button', { name: /commit 1 day/i });
    await expect(commitButton).toHaveAttribute('aria-label', /commit 1 day/i);

    const createSnapshotButton = page.getByRole('button', { name: /create snapshot/i });
    await expect(createSnapshotButton).toHaveAttribute('aria-label', /create snapshot/i);
  });

  test('should show sidebar navigation link', async ({ page }) => {
    await activateGuestSession(page);
    await safeGoto(page, '/dashboard');

    // Navigation should include Simulation
    const simulationNavLink = page.getByRole('link', { name: /simulation/i });
    await expect(simulationNavLink).toBeVisible();

    // Click to navigate
    await simulationNavLink.click();

    // Should be on simulation page
    await expect(page).toHaveURL(/.*\/simulation/);
  });
});
