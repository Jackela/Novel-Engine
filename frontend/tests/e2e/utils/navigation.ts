import type { LoadState, Page } from '@playwright/test';

type SafeGotoOptions = {
  timeout?: number;
  waitUntil?: LoadState;
};

const DEFAULT_TIMEOUT_MS = 45_000;

export async function safeGoto(
  page: Page,
  url: string,
  options: SafeGotoOptions = {}
) {
  const timeout = options.timeout ?? DEFAULT_TIMEOUT_MS;
  const waitUntil = options.waitUntil ?? 'domcontentloaded';

  try {
    await page.goto(url, { waitUntil, timeout });
  } catch (error) {
    await page.goto(url, { waitUntil: 'commit', timeout });
  }

  if (waitUntil === 'domcontentloaded') {
    await page.waitForLoadState('domcontentloaded', { timeout }).catch(() => {});
  }
}
