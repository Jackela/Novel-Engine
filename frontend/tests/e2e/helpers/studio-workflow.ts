import { expect, type Page } from '@playwright/test';

export type StudioView = 'workspace' | 'playback';

export interface SeedDraftOptions {
  title: string;
  premise: string;
  targetChapters?: number;
  themes?: string;
}

export interface ConsoleGuardOptions {
  extraAllowList?: RegExp[];
}

const defaultConsoleAllowList = [/Download the React DevTools/i];

export function uniqueTitle(prefix: string): string {
  return `${prefix} ${Math.random().toString(36).slice(2, 8)}`;
}

export async function expectStudioRoute(
  page: Page,
  view: StudioView = 'workspace',
): Promise<void> {
  await expect(page).toHaveURL(
    view === 'playback' ? /\/studio\?(.+&)?view=playback/ : /\/studio(\?.*)?$/,
  );
  await expect(page.getByTestId('studio-workbench-page')).toBeVisible();
  await expect(page.getByTestId('workspace-surface')).toBeVisible();
  await expect(page.getByTestId('playback-desk')).toBeVisible();
}

export async function expectWorkflowState(
  page: Page,
  expected: string,
): Promise<void> {
  await expect(page.getByTestId('studio-workflow-state')).toContainText(expected, {
    timeout: 20_000,
  });
}

export async function selectMockProvider(page: Page): Promise<void> {
  const providerSelect = page.getByTestId('studio-provider-select');
  await expect(providerSelect).toBeVisible();
  await providerSelect.selectOption('mock');
  await expect(providerSelect).toHaveValue('mock');
}

export async function signIn(page: Page): Promise<void> {
  await page.goto('/auth/login', { waitUntil: 'domcontentloaded' });
  await page.getByTestId('auth-login-email').fill('operator@novel.engine');
  await page.getByTestId('auth-login-password').fill('demo-password');
  await page.getByTestId('auth-login-submit').click();
  await expectStudioRoute(page);
}

export async function launchGuest(page: Page): Promise<void> {
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  const landingPage = page.getByTestId('auth-home-page');
  await expect(landingPage).toBeVisible();
  await page.getByTestId('auth-home-launch-guest').click();
  await expectStudioRoute(page);
}

export async function seedDraftStory(
  page: Page,
  options: SeedDraftOptions,
): Promise<void> {
  await page.getByTestId('studio-title-input').fill(options.title);
  await page.getByTestId('studio-premise-input').fill(options.premise);
  await page
    .getByTestId('studio-target-chapters-input')
    .fill(String(options.targetChapters ?? 3));
  await page
    .getByTestId('studio-themes-input')
    .fill(options.themes ?? 'serial tension, debt, memory');
  await page.getByTestId('studio-create-draft').click();

  await expect(page.getByTestId('studio-active-title')).toHaveText(options.title);
}

export function attachConsoleGuard(
  page: Page,
  options: ConsoleGuardOptions = {},
): () => Promise<void> {
  const unexpected: string[] = [];
  const allowList = [
    ...defaultConsoleAllowList,
    ...(options.extraAllowList ?? []),
  ];

  page.on('console', (message) => {
    if (message.type() !== 'error' && message.type() !== 'warning') {
      return;
    }
    const text = message.text();
    if (allowList.some((pattern) => pattern.test(text))) {
      return;
    }
    unexpected.push(`[console:${message.type()}] ${text}`);
  });

  page.on('pageerror', (error) => {
    const text = error.message ?? String(error);
    if (allowList.some((pattern) => pattern.test(text))) {
      return;
    }
    unexpected.push(`[pageerror] ${text}`);
  });

  return async () => {
    expect(unexpected, unexpected.join('\n')).toEqual([]);
  };
}
