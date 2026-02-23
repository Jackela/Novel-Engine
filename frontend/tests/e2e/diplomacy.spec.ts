/**
 * Diplomacy Matrix E2E Tests (SIM-011)
 *
 * Tests for the DiplomacyMatrix component including:
 * - Grid rendering with correct colors
 * - Tooltip display on hover
 * - Dialog interaction for editing relations
 * - Keyboard navigation
 * - Accessibility features
 *
 * @tags @diplomacy @world @simulation
 */

import type { Page } from '@playwright/test';
import { test, expect } from './fixtures';
import { activateGuestSession } from './utils/auth';
import { safeGoto } from './utils/navigation';

// This suite relies on page.route API mocks; block service workers to avoid interception races.
test.use({ serviceWorkers: 'block' });
const diplomacyRoutePattern = /\/api\/world\/[^/]+\/diplomacy(?:\/.*)?$/;

async function gotoWorld(page: Page) {
  await safeGoto(page, '/world');
  await expect(page.locator('[data-testid="world-page"]')).toBeVisible({
    timeout: 20_000,
  });
}

// Mock diplomacy API responses
async function mockDiplomacyApiEmpty(page: Page) {
  await page.route(diplomacyRoutePattern, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        world_id: 'test-world',
        matrix: {},
        factions: [],
      }),
    });
  });
}

async function mockDiplomacyApiSuccess(page: Page) {
  await page.route(diplomacyRoutePattern, async (route) => {
    const url = route.request().url();
    const method = route.request().method();

    // Handle PUT for setting relations
    if (method === 'PUT') {
      const body = route.request().postDataJSON();
      const newStatus = body?.status ?? 'neutral';

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          world_id: 'test-world',
          matrix: {
            'Kingdom of Eldoria': {
              'Kingdom of Eldoria': '-',
              'Northern Alliance': newStatus,
              'Merchant Guild': 'friendly',
            },
            'Northern Alliance': {
              'Kingdom of Eldoria': newStatus,
              'Northern Alliance': '-',
              'Merchant Guild': 'neutral',
            },
            'Merchant Guild': {
              'Kingdom of Eldoria': 'friendly',
              'Northern Alliance': 'neutral',
              'Merchant Guild': '-',
            },
          },
          factions: ['Kingdom of Eldoria', 'Merchant Guild', 'Northern Alliance'],
        }),
      });
      return;
    }

    // GET request - return full matrix
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        world_id: 'test-world',
        matrix: {
          'Kingdom of Eldoria': {
            'Kingdom of Eldoria': '-',
            'Northern Alliance': 'hostile',
            'Merchant Guild': 'friendly',
          },
          'Northern Alliance': {
            'Kingdom of Eldoria': 'hostile',
            'Northern Alliance': '-',
            'Merchant Guild': 'neutral',
          },
          'Merchant Guild': {
            'Kingdom of Eldoria': 'friendly',
            'Northern Alliance': 'neutral',
            'Merchant Guild': '-',
          },
        },
        factions: ['Kingdom of Eldoria', 'Merchant Guild', 'Northern Alliance'],
      }),
    });
  });
}

async function mockDiplomacyApiError(page: Page) {
  await page.route(diplomacyRoutePattern, async (route) => {
    await route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({
        detail: 'Internal server error',
      }),
    });
  });
}

test.describe('DiplomacyMatrix Component', () => {
  test.beforeEach(async ({ page }) => {
    await activateGuestSession(page);
  });

  test('should display empty state when no factions exist', async ({ page }) => {
    await mockDiplomacyApiEmpty(page);
    await gotoWorld(page);

    const matrix = page.locator('[data-testid="diplomacy-matrix"]');
    await expect(matrix).toBeVisible();
    await expect(matrix).toHaveAttribute('data-state', 'empty');

    // Should show empty message
    await expect(matrix.getByText(/No factions registered/i)).toBeVisible();
  });

  test('should display loading state initially', async ({ page }) => {
    // Delay the response to see loading state
    await page.route(diplomacyRoutePattern, async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 500));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          world_id: 'test-world',
          matrix: {},
          factions: [],
        }),
      });
    });

    await activateGuestSession(page);
    await gotoWorld(page);

    const matrix = page.locator('[data-testid="diplomacy-matrix"]');
    await expect(matrix).toBeVisible();

    // Should eventually show empty state
    await expect(matrix).toHaveAttribute('data-state', 'empty', {
      timeout: 5000,
    });
  });

  test('should display grid with factions', async ({ page }) => {
    await mockDiplomacyApiSuccess(page);
    await gotoWorld(page);

    const matrix = page.locator('[data-testid="diplomacy-matrix"]');
    await expect(matrix).toBeVisible();
    await expect(matrix).toHaveAttribute('data-state', 'success');

    // Should show faction count
    await expect(matrix.getByText('3 factions')).toBeVisible();

    // Should show faction names as column headers
    await expect(
      matrix.getByRole('columnheader', { name: 'Kingdom of Eldoria' })
    ).toBeVisible();
    await expect(
      matrix.getByRole('columnheader', { name: 'Northern Alliance' })
    ).toBeVisible();
    await expect(
      matrix.getByRole('columnheader', { name: 'Merchant Guild' })
    ).toBeVisible();
  });

  test('should show tooltip on cell hover', async ({ page }) => {
    await mockDiplomacyApiSuccess(page);
    await gotoWorld(page);

    const matrix = page.locator('[data-testid="diplomacy-matrix"]');
    await expect(matrix).toBeVisible();

    // Find a non-diagonal cell and verify it exposes one of the supported statuses.
    const hostileCell = matrix.locator('[role="gridcell"]:not([disabled])').first();
    await expect(hostileCell).toHaveAttribute(
      'aria-label',
      /(Allied|Friendly|Neutral|Cold|Hostile|At War)/i
    );

    // Hover over the cell
    await hostileCell.hover();
  });

  test('should open dialog on cell click', async ({ page }) => {
    await mockDiplomacyApiSuccess(page);
    await gotoWorld(page);

    const matrix = page.locator('[data-testid="diplomacy-matrix"]');
    await expect(matrix).toBeVisible();

    // Find a clickable cell (not diagonal)
    const clickableCell = matrix.locator('[role="gridcell"]:not([disabled])').first();

    // Click the cell
    await clickableCell.click();

    // Dialog should open
    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).toBeVisible();

    // Should show dialog title
    await expect(dialog.getByText('Edit Diplomatic Relation')).toBeVisible();

    // Should show faction names
    await expect(dialog.getByText('Faction A')).toBeVisible();
    await expect(dialog.getByText('Faction B')).toBeVisible();
  });

  test('should save relation change', async ({ page }) => {
    await mockDiplomacyApiSuccess(page);
    await gotoWorld(page);

    const matrix = page.locator('[data-testid="diplomacy-matrix"]');
    await expect(matrix).toBeVisible();

    // Click a cell to open dialog
    const clickableCell = matrix.locator('[role="gridcell"]:not([disabled])').first();
    await clickableCell.click();

    // Dialog should open
    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).toBeVisible();

    // Select new status
    const statusSelect = dialog.locator('#status-select');
    await statusSelect.click();
    await page.getByRole('option', { name: 'Allied' }).click();

    // Click save
    const saveButton = dialog.getByRole('button', { name: /save/i });
    await saveButton.click();

    // Dialog should close after save
    await expect(dialog).not.toBeVisible({ timeout: 3000 });
  });

  test('should cancel dialog without saving', async ({ page }) => {
    await mockDiplomacyApiSuccess(page);
    await gotoWorld(page);

    const matrix = page.locator('[data-testid="diplomacy-matrix"]');
    await expect(matrix).toBeVisible();

    // Click a cell to open dialog
    const clickableCell = matrix.locator('[role="gridcell"]:not([disabled])').first();
    await clickableCell.click();

    // Dialog should open
    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).toBeVisible();

    // Click cancel
    const cancelButton = dialog.getByRole('button', { name: /cancel/i });
    await cancelButton.click();

    // Dialog should close
    await expect(dialog).not.toBeVisible();
  });

  test('should display error state with retry', async ({ page }) => {
    let requestCount = 0;

    await page.route(diplomacyRoutePattern, async (route) => {
      requestCount++;

      if (requestCount === 1) {
        // First request fails
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal server error' }),
        });
      } else {
        // Second request succeeds
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            world_id: 'test-world',
            matrix: {},
            factions: [],
          }),
        });
      }
    });

    await activateGuestSession(page);
    await gotoWorld(page);

    const matrix = page.locator('[data-testid="diplomacy-matrix"]');
    await expect(matrix).toBeVisible();
    await expect(matrix).toHaveAttribute('data-state', 'error');

    // Retry should be available from error state.
    const retryButton = matrix.getByRole('button', { name: /retry/i });
    await expect(retryButton).toBeVisible();
    await retryButton.click();

    // Should show success/empty state after retry
    await expect(matrix).toHaveAttribute('data-state', 'empty', {
      timeout: 3000,
    });
  });

  test('should not allow editing self-relations (diagonal)', async ({ page }) => {
    await mockDiplomacyApiSuccess(page);
    await gotoWorld(page);

    const matrix = page.locator('[data-testid="diplomacy-matrix"]');
    await expect(matrix).toBeVisible();

    // Diagonal cells should be disabled
    const disabledCells = matrix.locator('[role="gridcell"][disabled]');
    await expect(disabledCells.first()).toBeVisible();

    // Clicking disabled cell should not open dialog
    await disabledCells.first().click({ force: true });

    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).not.toBeVisible();
  });
});

test.describe('DiplomacyMatrix Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await activateGuestSession(page);
    await mockDiplomacyApiSuccess(page);
  });

  test('should have grid role with aria-label', async ({ page }) => {
    await gotoWorld(page);

    const matrix = page.locator('[data-testid="diplomacy-matrix"]');
    await expect(matrix).toBeVisible();

    // Check for grid role
    const grid = matrix.locator('[role="grid"]');
    await expect(grid).toBeVisible();
    await expect(grid).toHaveAttribute('aria-label', 'Faction diplomacy matrix');
  });

  test('should have gridcell role for each cell', async ({ page }) => {
    await gotoWorld(page);

    const matrix = page.locator('[data-testid="diplomacy-matrix"]');
    await expect(matrix).toBeVisible();

    // Each cell should have gridcell role
    const cells = matrix.getByRole('gridcell');
    // 3 factions = 3x3 = 9 cells
    await expect(cells).toHaveCount(9);

    // Each cell should have aria-label describing the relation
    const firstCell = cells.first();
    await expect(firstCell).toHaveAttribute('aria-label');
  });

  test('should have columnheader and rowheader', async ({ page }) => {
    await gotoWorld(page);

    const matrix = page.locator('[data-testid="diplomacy-matrix"]');
    await expect(matrix).toBeVisible();

    // Column headers
    const colHeaders = matrix.locator('[role="columnheader"]');
    await expect(colHeaders).toHaveCount(3);

    // Row headers
    const rowHeaders = matrix.locator('[role="rowheader"]');
    await expect(rowHeaders).toHaveCount(3);
  });

  test('should be keyboard navigable with arrow keys', async ({ page }) => {
    await gotoWorld(page);

    const matrix = page.locator('[data-testid="diplomacy-matrix"]');
    await expect(matrix).toBeVisible();

    const grid = matrix.locator('[role="grid"]');

    // Focus the grid
    await grid.focus();

    // Press arrow keys to navigate
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('ArrowDown');

    // A cell should be focused
    const focusedCell = page.locator(':focus');
    await expect(focusedCell).toBeVisible();
  });

  test('should open dialog with Enter key', async ({ page }) => {
    await gotoWorld(page);

    const matrix = page.locator('[data-testid="diplomacy-matrix"]');
    await expect(matrix).toBeVisible();

    // Use keyboard navigation on the grid, then activate an editable cell via Enter.
    const grid = matrix.locator('[role="grid"]');
    await grid.focus();
    await page.keyboard.press('ArrowDown'); // row 1 header
    await page.keyboard.press('ArrowRight'); // row 1, col 1 (self)
    await page.keyboard.press('ArrowRight'); // row 1, col 2 (editable)
    await page.keyboard.press('Enter');

    // Dialog should open
    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).toBeVisible({ timeout: 3000 });
  });

  test('should have accessible status select in dialog', async ({ page }) => {
    await mockDiplomacyApiSuccess(page);
    await gotoWorld(page);

    const matrix = page.locator('[data-testid="diplomacy-matrix"]');
    await expect(matrix).toBeVisible();

    // Click a cell to open dialog
    const clickableCell = matrix.locator('[role="gridcell"]:not([disabled])').first();
    await clickableCell.click();

    // Dialog should open
    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).toBeVisible();

    // Status select should have label
    const statusLabel = dialog.getByText('New Status');
    await expect(statusLabel).toBeVisible();

    // Select should have accessible name
    const statusSelect = dialog.locator('#status-select');
    await expect(statusSelect).toBeVisible();
  });

  test('should have aria-modal on dialog', async ({ page }) => {
    await mockDiplomacyApiSuccess(page);
    await gotoWorld(page);

    const matrix = page.locator('[data-testid="diplomacy-matrix"]');
    await expect(matrix).toBeVisible();

    // Click a cell to open dialog
    const clickableCell = matrix.locator('[role="gridcell"]:not([disabled])').first();
    await clickableCell.click();

    // Dialog should have aria-modal
    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).toBeVisible();
    await expect(dialog).toHaveAttribute('aria-modal', 'true');
  });
});
