/**
 * Timeline E2E Tests (SIM-007)
 *
 * Tests for the WorldTimeline component including:
 * - Component rendering
 * - Filter functionality
 * - Empty state display
 * - Error handling
 * - Accessibility features
 *
 * @tags @timeline @world @simulation
 */

import type { Page } from '@playwright/test';
import { test, expect } from './fixtures';
import { activateGuestSession } from './utils/auth';
import { safeGoto } from './utils/navigation';

// Mock events API responses
async function mockEventsApiEmpty(page: Page) {
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

async function mockEventsApiSuccess(page: Page) {
  await page.route('**/api/world/*/events*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        events: [
          {
            id: 'event-1',
            name: 'The Great Battle of Eldoria',
            description:
              'A pivotal conflict between the Kingdom of Eldoria and the Northern Alliance that reshaped the political landscape of the realm. The battle lasted for three days and resulted in significant casualties on both sides.',
            event_type: 'battle',
            significance: 'major',
            outcome: 'positive',
            date_description: 'Year 1042, Month 3, Day 15',
            duration_description: '3 days',
            location_ids: ['loc-1'],
            faction_ids: ['faction-1', 'faction-2'],
            key_figures: ['King Aldric', 'General Theron'],
            causes: ['Territorial dispute', 'Trade route control'],
            consequences: ['Treaty of Eldoria', 'Border redefinition'],
            preceding_event_ids: [],
            following_event_ids: [],
            related_event_ids: [],
            is_secret: false,
            sources: ['Royal Archives'],
            narrative_importance: 85,
            impact_scope: 'regional',
            affected_faction_ids: ['faction-1', 'faction-2'],
            affected_location_ids: ['loc-1'],
            structured_date: {
              year: 1042,
              month: 3,
              day: 15,
              era_name: 'Third Age',
            },
            created_at: '2026-02-16T10:00:00Z',
            updated_at: '2026-02-16T10:00:00Z',
          },
          {
            id: 'event-2',
            name: 'Discovery of the Crystal Caves',
            description: 'Miners discovered ancient caves filled with magical crystals.',
            event_type: 'discovery',
            significance: 'moderate',
            outcome: 'positive',
            date_description: 'Year 1042, Month 2, Day 8',
            duration_description: null,
            location_ids: ['loc-2'],
            faction_ids: ['faction-3'],
            key_figures: ['Miner Gareth'],
            causes: [],
            consequences: ['New trade opportunities'],
            preceding_event_ids: [],
            following_event_ids: [],
            related_event_ids: [],
            is_secret: false,
            sources: ['Mining Guild Records'],
            narrative_importance: 50,
            impact_scope: 'local',
            affected_faction_ids: ['faction-3'],
            affected_location_ids: ['loc-2'],
            structured_date: {
              year: 1042,
              month: 2,
              day: 8,
              era_name: 'Third Age',
            },
            created_at: '2026-02-15T14:00:00Z',
            updated_at: '2026-02-15T14:00:00Z',
          },
          {
            id: 'event-3',
            name: 'Global Trade Agreement',
            description:
              'A comprehensive trade agreement signed by all major factions, establishing new trade routes and economic cooperation across the entire realm.',
            event_type: 'trade',
            significance: 'world_changing',
            outcome: 'positive',
            date_description: 'Year 1042, Month 1, Day 1',
            duration_description: '1 day',
            location_ids: ['loc-3'],
            faction_ids: ['faction-1', 'faction-2', 'faction-3'],
            key_figures: ['Chancellor Mira', 'Merchant Lord Vex'],
            causes: ['Economic instability'],
            consequences: ['Prosperity era'],
            preceding_event_ids: [],
            following_event_ids: [],
            related_event_ids: [],
            is_secret: false,
            sources: ['Trade Archives'],
            narrative_importance: 95,
            impact_scope: 'global',
            affected_faction_ids: [],
            affected_location_ids: [],
            structured_date: {
              year: 1042,
              month: 1,
              day: 1,
              era_name: 'Third Age',
            },
            created_at: '2026-02-14T09:00:00Z',
            updated_at: '2026-02-14T09:00:00Z',
          },
        ],
        total_count: 3,
        page: 1,
        page_size: 20,
        total_pages: 1,
      }),
    });
  });
}

async function mockEventsApiFiltered(page: Page) {
  await page.route('**/api/world/*/events*', async (route) => {
    const url = route.request().url();
    const params = new URL(url).searchParams;

    // Return filtered results based on query params
    if (params.get('event_type') === 'battle') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          events: [
            {
              id: 'event-1',
              name: 'The Great Battle of Eldoria',
              description: 'A pivotal conflict between the Kingdom of Eldoria.',
              event_type: 'battle',
              significance: 'major',
              outcome: 'positive',
              date_description: 'Year 1042, Month 3, Day 15',
              duration_description: '3 days',
              location_ids: ['loc-1'],
              faction_ids: ['faction-1', 'faction-2'],
              key_figures: ['King Aldric', 'General Theron'],
              causes: [],
              consequences: [],
              preceding_event_ids: [],
              following_event_ids: [],
              related_event_ids: [],
              is_secret: false,
              sources: [],
              narrative_importance: 85,
              impact_scope: 'regional',
              affected_faction_ids: [],
              affected_location_ids: [],
              structured_date: null,
              created_at: '2026-02-16T10:00:00Z',
              updated_at: '2026-02-16T10:00:00Z',
            },
          ],
          total_count: 1,
          page: 1,
          page_size: 20,
          total_pages: 1,
        }),
      });
    } else if (params.get('impact_scope') === 'global') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          events: [
            {
              id: 'event-3',
              name: 'Global Trade Agreement',
              description: 'A comprehensive trade agreement.',
              event_type: 'trade',
              significance: 'world_changing',
              outcome: 'positive',
              date_description: 'Year 1042, Month 1, Day 1',
              duration_description: null,
              location_ids: [],
              faction_ids: [],
              key_figures: [],
              causes: [],
              consequences: [],
              preceding_event_ids: [],
              following_event_ids: [],
              related_event_ids: [],
              is_secret: false,
              sources: [],
              narrative_importance: 95,
              impact_scope: 'global',
              affected_faction_ids: [],
              affected_location_ids: [],
              structured_date: null,
              created_at: '2026-02-14T09:00:00Z',
              updated_at: '2026-02-14T09:00:00Z',
            },
          ],
          total_count: 1,
          page: 1,
          page_size: 20,
          total_pages: 1,
        }),
      });
    } else {
      // Default: return all events
      await mockEventsApiSuccess(page);
      await route.continue();
    }
  });
}

async function mockEventsApiError(page: Page) {
  await page.route('**/api/world/*/events*', async (route) => {
    await route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({
        detail: 'Internal server error',
      }),
    });
  });
}

test.describe('WorldTimeline Component', () => {
  test.beforeEach(async ({ page }) => {
    await activateGuestSession(page);
  });

  test('should display empty state when no events exist', async ({ page }) => {
    await mockEventsApiEmpty(page);
    await safeGoto(page, '/world');

    const timeline = page.locator('[data-testid="world-timeline"]');
    await expect(timeline).toBeVisible();
    await expect(timeline).toHaveAttribute('data-state', 'empty');

    // Should show empty message
    await expect(timeline.getByText(/No events yet/i)).toBeVisible();
    await expect(
      timeline.getByText(/Events will appear as the simulation progresses/i)
    ).toBeVisible();
  });

  test('should display loading state initially', async ({ page }) => {
    // Delay the response to see loading state
    await page.route('**/api/world/*/events*', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 500));
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

    await activateGuestSession(page);
    await safeGoto(page, '/world');

    const timeline = page.locator('[data-testid="world-timeline"]');
    await expect(timeline).toBeVisible();

    // Should eventually show empty state
    await expect(timeline).toHaveAttribute('data-state', 'empty', {
      timeout: 5000,
    });
  });

  test('should display events with correct badges', async ({ page }) => {
    await mockEventsApiSuccess(page);
    await safeGoto(page, '/world');

    const timeline = page.locator('[data-testid="world-timeline"]');
    await expect(timeline).toBeVisible();
    await expect(timeline).toHaveAttribute('data-state', 'success');

    // Should show event count
    await expect(timeline.getByText('3 events')).toBeVisible();

    // Should show event names
    await expect(
      timeline.getByText('The Great Battle of Eldoria')
    ).toBeVisible();
    await expect(timeline.getByText('Discovery of the Crystal Caves')).toBeVisible();
    await expect(timeline.getByText('Global Trade Agreement')).toBeVisible();

    // Should show event type badges
    await expect(timeline.getByRole('article').getByText('battle')).toBeVisible();
    await expect(timeline.getByRole('article').getByText('discovery')).toBeVisible();
    await expect(timeline.getByRole('article').getByText('trade')).toBeVisible();

    // Should show impact scope badges
    await expect(
      timeline.getByRole('article').getByText('regional')
    ).toBeVisible();
    await expect(timeline.getByRole('article').getByText('local')).toBeVisible();
    await expect(timeline.getByRole('article').getByText('global')).toBeVisible();
  });

  test('should expand long descriptions', async ({ page }) => {
    await mockEventsApiSuccess(page);
    await safeGoto(page, '/world');

    const timeline = page.locator('[data-testid="world-timeline"]');
    await expect(timeline).toBeVisible();

    // Find the battle event card (has long description)
    const battleEvent = timeline.getByRole('article').filter({
      hasText: 'The Great Battle of Eldoria',
    });

    // Should show "Show more" button for long descriptions
    const showMoreButton = battleEvent.getByRole('button', { name: /show more/i });
    await expect(showMoreButton).toBeVisible();

    // Click to expand
    await showMoreButton.click();

    // Should now show "Show less" button
    await expect(battleEvent.getByRole('button', { name: /show less/i })).toBeVisible();
  });

  test('should filter by event type', async ({ page }) => {
    await mockEventsApiFiltered(page);
    await safeGoto(page, '/world');

    const timeline = page.locator('[data-testid="world-timeline"]');
    await expect(timeline).toBeVisible();

    // Open event type dropdown
    const typeFilter = timeline.locator('#event-type-filter');
    await typeFilter.click();

    // Select "battle" filter
    await page.getByRole('option', { name: 'Battle' }).click();

    // Should show only battle events
    await expect(
      timeline.getByText('The Great Battle of Eldoria')
    ).toBeVisible({ timeout: 3000 });

    // Other events should not be visible
    await expect(
      timeline.getByText('Discovery of the Crystal Caves')
    ).not.toBeVisible();
  });

  test('should filter by impact scope', async ({ page }) => {
    await mockEventsApiFiltered(page);
    await safeGoto(page, '/world');

    const timeline = page.locator('[data-testid="world-timeline"]');
    await expect(timeline).toBeVisible();

    // Open impact scope dropdown
    const scopeFilter = timeline.locator('#impact-scope-filter');
    await scopeFilter.click();

    // Select "global" filter
    await page.getByRole('option', { name: 'Global' }).click();

    // Should show only global events
    await expect(
      timeline.getByText('Global Trade Agreement')
    ).toBeVisible({ timeout: 3000 });

    // Count should update
    await expect(timeline.getByText('1 event')).toBeVisible();
  });

  test('should clear filters', async ({ page }) => {
    await mockEventsApiSuccess(page);
    await safeGoto(page, '/world');

    const timeline = page.locator('[data-testid="world-timeline"]');
    await expect(timeline).toBeVisible();

    // Apply a filter first
    const typeFilter = timeline.locator('#event-type-filter');
    await typeFilter.click();
    await page.getByRole('option', { name: 'Battle' }).click();

    // Wait for filter to apply
    await page.waitForTimeout(500);

    // Clear button should appear
    const clearButton = timeline.getByRole('button', { name: /clear/i });
    await expect(clearButton).toBeVisible();

    // Click clear
    await clearButton.click();

    // All events should be visible again
    await expect(timeline.getByText('3 events')).toBeVisible({
      timeout: 3000,
    });
  });

  test('should display error state with retry', async ({ page }) => {
    let requestCount = 0;

    await page.route('**/api/world/*/events*', async (route) => {
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
            events: [],
            total_count: 0,
            page: 1,
            page_size: 20,
            total_pages: 0,
          }),
        });
      }
    });

    await activateGuestSession(page);
    await safeGoto(page, '/world');

    const timeline = page.locator('[data-testid="world-timeline"]');
    await expect(timeline).toBeVisible();
    await expect(timeline).toHaveAttribute('data-state', 'error');

    // Should show error message
    await expect(timeline.getByText(/Failed to load events/i)).toBeVisible();

    // Click retry
    const retryButton = timeline.getByRole('button', { name: /retry/i });
    await retryButton.click();

    // Should show success/empty state after retry
    await expect(timeline).toHaveAttribute('data-state', 'empty', {
      timeout: 3000,
    });
  });
});

test.describe('WorldTimeline Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await activateGuestSession(page);
    await mockEventsApiSuccess(page);
  });

  test('should have feed role with aria-label', async ({ page }) => {
    await safeGoto(page, '/world');

    const timeline = page.locator('[data-testid="world-timeline"]');
    await expect(timeline).toBeVisible();

    // Check for feed role
    const feed = timeline.locator('[role="feed"]');
    await expect(feed).toBeVisible();
    await expect(feed).toHaveAttribute('aria-label', 'Historical events timeline');
  });

  test('should have article role for each event', async ({ page }) => {
    await safeGoto(page, '/world');

    const timeline = page.locator('[data-testid="world-timeline"]');
    await expect(timeline).toBeVisible();

    // Each event should be an article
    const articles = timeline.getByRole('article');
    await expect(articles).toHaveCount(3);

    // Each article should have aria-labelledby
    const firstArticle = articles.first();
    await expect(firstArticle).toHaveAttribute('aria-labelledby');
  });

  test('should have accessible filter dropdowns', async ({ page }) => {
    await safeGoto(page, '/world');

    const timeline = page.locator('[data-testid="world-timeline"]');
    await expect(timeline).toBeVisible();

    // Type filter should have label
    const typeFilter = timeline.locator('#event-type-filter');
    await expect(typeFilter).toBeVisible();
    await expect(typeFilter).toHaveAttribute('aria-label', /filter by event type/i);

    // Scope filter should have label
    const scopeFilter = timeline.locator('#impact-scope-filter');
    await expect(scopeFilter).toBeVisible();
    await expect(scopeFilter).toHaveAttribute('aria-label', /filter by impact scope/i);
  });

  test('should be keyboard navigable', async ({ page }) => {
    await safeGoto(page, '/world');

    const timeline = page.locator('[data-testid="world-timeline"]');
    await expect(timeline).toBeVisible();

    // Tab to filters
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // Should be able to interact with filter dropdowns
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();

    // Should be able to expand description with keyboard
    const showMoreButton = timeline.getByRole('button', { name: /show more/i }).first();
    await showMoreButton.focus();
    await page.keyboard.press('Enter');

    // Should toggle to "Show less"
    await expect(
      timeline.getByRole('button', { name: /show less/i }).first()
    ).toBeVisible();
  });

  test('should have accessible impact scope badge', async ({ page }) => {
    await safeGoto(page, '/world');

    const timeline = page.locator('[data-testid="world-timeline"]');
    await expect(timeline).toBeVisible();

    // Impact scope badges should have aria-label
    const globalBadge = timeline.getByRole('article').getByText('global');
    await expect(globalBadge).toBeVisible();
    await expect(globalBadge).toHaveAttribute('aria-label', /impact: global/i);
  });
});
