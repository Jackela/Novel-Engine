import { test as base, expect as baseExpect } from '@playwright/test';
import { mockGuestSessionApi } from './utils/auth';
import { mockDashboardApi, mockDecisionApi, mockEventSource } from './utils/apiMocks';

export const test = base.extend({
  page: async ({ page }, use) => {
    await page.context().setOffline(false).catch(() => {});
    await mockEventSource(page);
    await mockGuestSessionApi(page);
    await mockDashboardApi(page);
    await mockDecisionApi(page);
    try {
      await use(page);
    } finally {
      await page.context().setOffline(false).catch(() => {});
    }
  },
});

export const expect = baseExpect;
