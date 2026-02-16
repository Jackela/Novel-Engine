/**
 * Calendar E2E Tests (SIM-004)
 *
 * Tests for the CalendarDisplay component including:
 * - Component rendering
 * - Button interactions
 * - Error state display
 * - Accessibility features
 *
 * @tags @calendar @world @simulation
 */

import type { Page } from '@playwright/test';
import { test, expect } from './fixtures';
import { activateGuestSession } from './utils/auth';
import { safeGoto } from './utils/navigation';

// Mock calendar API responses
async function mockCalendarApi(page: Page) {
  // Mock GET calendar - return 404 initially to test error state
  await page.route('**/api/calendar/*', async (route) => {
    if (route.request().method() === 'GET') {
      // Return 404 for initial test - world needs to be created first
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: "World 'default-world' not found" }),
      });
    }
  });
}

async function mockCalendarApiSuccess(page: Page) {
  await page.route('**/api/calendar/*', async (route) => {
    const method = route.request().method();
    const url = route.request().url();

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
    } else if (method === 'POST' && url.includes('/advance')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          year: 1,
          month: 1,
          day: 8,
          era_name: 'First Age',
          formatted_date: 'Year 1, Month 1, Day 8 - First Age',
          days_per_month: 30,
          months_per_year: 12,
        }),
      });
    }
  });
}

test.describe('Calendar Display Component', () => {
  test.beforeEach(async ({ page }) => {
    await activateGuestSession(page);
  });

  test('should display error state when world not found', async ({ page }) => {
    await mockCalendarApi(page);
    await safeGoto(page, '/world');

    // Wait for calendar component to render with error state
    const calendarCard = page.locator('[data-testid="calendar-display"]');
    await expect(calendarCard).toBeVisible();
    await expect(calendarCard).toHaveAttribute('data-state', 'error');

    // Should show error message
    await expect(calendarCard.getByText(/Failed to load calendar/i)).toBeVisible();

    // Should have retry button
    await expect(calendarCard.getByRole('button', { name: /retry/i })).toBeVisible();
  });

  test('should display loading state initially', async ({ page }) => {
    // Delay the response to see loading state
    await page.route('**/api/calendar/*', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 500));
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
    });

    await activateGuestSession(page);
    await safeGoto(page, '/world');

    // Should show loading skeleton briefly
    const calendarCard = page.locator('[data-testid="calendar-display"]');
    await expect(calendarCard).toBeVisible();

    // Eventually shows success state
    await expect(calendarCard).toHaveAttribute('data-state', 'success', { timeout: 5000 });
  });

  test('should display calendar with advance buttons', async ({ page }) => {
    await mockCalendarApiSuccess(page);
    await safeGoto(page, '/world');

    // Wait for calendar component to render
    const calendarCard = page.locator('[data-testid="calendar-display"]');
    await expect(calendarCard).toBeVisible();
    await expect(calendarCard).toHaveAttribute('data-state', 'success');

    // Should show formatted date
    await expect(calendarCard.getByText(/Year 1, Month 1, Day 1/i)).toBeVisible();

    // Should show era name in description
    await expect(calendarCard.getByText('First Age')).toBeVisible();

    // Should have three advance buttons
    await expect(calendarCard.getByRole('button', { name: /advance time by 1 day/i })).toBeVisible();
    await expect(calendarCard.getByRole('button', { name: /advance time by 7 days/i })).toBeVisible();
    await expect(calendarCard.getByRole('button', { name: /advance time by 30 days/i })).toBeVisible();
  });

  test('should advance calendar when button clicked', async ({ page }) => {
    await mockCalendarApiSuccess(page);
    await safeGoto(page, '/world');

    const calendarCard = page.locator('[data-testid="calendar-display"]');
    await expect(calendarCard).toBeVisible();

    // Click 7 days advance button
    const advanceButton = calendarCard.getByRole('button', { name: /advance time by 7 days/i });
    await advanceButton.click();

    // Should show updated date (mock returns day 8)
    await expect(calendarCard.getByText(/Year 1, Month 1, Day 8/i)).toBeVisible({
      timeout: 3000,
    });
  });

  test('should disable buttons while advancing', async ({ page }) => {
    let requestCount = 0;
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
      } else if (method === 'POST') {
        requestCount++;
        // Delay response to test loading state
        await new Promise((resolve) => setTimeout(resolve, 500));
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            year: 1,
            month: 1,
            day: 2,
            era_name: 'First Age',
            formatted_date: 'Year 1, Month 1, Day 2 - First Age',
            days_per_month: 30,
            months_per_year: 12,
          }),
        });
      }
    });

    await activateGuestSession(page);
    await safeGoto(page, '/world');

    const calendarCard = page.locator('[data-testid="calendar-display"]');
    await expect(calendarCard).toBeVisible();

    const advanceButton = calendarCard.getByRole('button', { name: /advance time by 1 day/i });

    // Click and immediately check if buttons are disabled
    await advanceButton.click();

    // Buttons should be disabled during request
    await expect(advanceButton).toBeDisabled();

    // Wait for request to complete
    await expect(calendarCard.getByText(/Day 2/i)).toBeVisible({ timeout: 3000 });

    // Button should be enabled again
    await expect(advanceButton).toBeEnabled();
  });

  test('should retry on error', async ({ page }) => {
    let requestCount = 0;

    await page.route('**/api/calendar/*', async (route) => {
      requestCount++;

      // First request fails
      if (requestCount === 1) {
        await route.fulfill({
          status: 404,
          contentType: 'application/json',
          body: JSON.stringify({ detail: "World 'default-world' not found" }),
        });
      } else {
        // Second request succeeds
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
      }
    });

    await activateGuestSession(page);
    await safeGoto(page, '/world');

    const calendarCard = page.locator('[data-testid="calendar-display"]');
    await expect(calendarCard).toHaveAttribute('data-state', 'error');

    // Click retry button
    const retryButton = calendarCard.getByRole('button', { name: /retry/i });
    await retryButton.click();

    // Should show success state after retry
    await expect(calendarCard).toHaveAttribute('data-state', 'success', { timeout: 3000 });
  });
});

test.describe('Calendar Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await activateGuestSession(page);
    await mockCalendarApiSuccess(page);
  });

  test('should have accessible advance buttons with aria-labels', async ({ page }) => {
    await safeGoto(page, '/world');

    const calendarCard = page.locator('[data-testid="calendar-display"]');
    await expect(calendarCard).toBeVisible();

    // Check aria-labels on buttons
    const oneDayButton = calendarCard.getByRole('button', { name: /advance time by 1 day/i });
    const sevenDaysButton = calendarCard.getByRole('button', { name: /advance time by 7 days/i });
    const thirtyDaysButton = calendarCard.getByRole('button', { name: /advance time by 30 days/i });

    await expect(oneDayButton).toHaveAttribute('aria-label', 'Advance time by 1 day');
    await expect(sevenDaysButton).toHaveAttribute('aria-label', 'Advance time by 7 days');
    await expect(thirtyDaysButton).toHaveAttribute('aria-label', 'Advance time by 30 days');
  });

  test('should have aria-live region for date changes', async ({ page }) => {
    await safeGoto(page, '/world');

    const calendarCard = page.locator('[data-testid="calendar-display"]');
    await expect(calendarCard).toBeVisible();

    // Check for aria-live on the date display
    const dateDisplay = calendarCard.locator('[aria-live="polite"]').first();
    await expect(dateDisplay).toBeVisible();

    // There should be a screen reader only announcement area
    const srAnnouncement = calendarCard.locator('.sr-only[aria-live="polite"]');
    await expect(srAnnouncement).toBeAttached();
  });

  test('should be keyboard navigable', async ({ page }) => {
    await safeGoto(page, '/world');

    const calendarCard = page.locator('[data-testid="calendar-display"]');
    await expect(calendarCard).toBeVisible();

    // Tab through the buttons
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // Should be focused on a button within the calendar
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();

    // Should be able to activate with Enter
    const oneDayButton = calendarCard.getByRole('button', { name: /advance time by 1 day/i });
    await oneDayButton.focus();
    await page.keyboard.press('Enter');

    // Calendar should update
    await expect(calendarCard.getByText(/Day 2/i)).toBeVisible({ timeout: 3000 });
  });
});
