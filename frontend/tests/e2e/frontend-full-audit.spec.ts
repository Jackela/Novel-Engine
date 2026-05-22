import { expect, test } from '@playwright/test';

import {
  attachConsoleGuard,
  expectStudioRoute,
  expectWorkflowState,
  launchGuest,
  seedDraftStory,
  selectMockProvider,
  signIn,
  uniqueTitle,
} from './helpers/studio-workflow';

test.describe('frontend full audit', () => {
  test.describe.configure({ mode: 'serial' });

  test('guest workflow covers workspace jobs and export verdict', async ({ page }) => {
    const assertConsoleClean = attachConsoleGuard(page);

    await launchGuest(page);
    await expect(page.getByTestId('workspace-badge')).toContainText('guest-');

    const title = uniqueTitle('Audit Guest Story');
    await seedDraftStory(page, {
      title,
      premise: 'A canal city records every promise and starts deleting them by district.',
      themes: 'debt, contracts, water law',
    });
    await selectMockProvider(page);

    await page.getByTestId('studio-run').click();
    await expectWorkflowState(page, 'run completed');
    await expect(page.getByTestId('studio-chapter-list')).toContainText('chapter-001.md');

    await page.getByTestId('studio-review').click();
    await expectWorkflowState(page, 'review completed');
    await page.getByTestId('studio-export').click();
    await expectWorkflowState(page, 'export completed');
    await expect(page.getByTestId('publish-verdict')).toContainText('export allowed');

    await assertConsoleClean();
  });

  test('signed-in and guest sessions can switch and resume via catalog', async ({ page }) => {
    const assertConsoleClean = attachConsoleGuard(page);

    await launchGuest(page);
    const guestWorkspace = (await page.getByTestId('workspace-badge').textContent())?.trim() ?? '';

    await page.getByTestId('studio-back-to-landing').click();
    await expect(page.getByTestId('auth-home-page')).toBeVisible();
    await expect(page.getByTestId('auth-home-session-catalog')).toBeVisible();
    await page.getByTestId('auth-home-go-login').click();

    await page.getByTestId('auth-login-email').fill('operator@novel.engine');
    await page.getByTestId('auth-login-password').fill('demo-password');
    await page.getByTestId('auth-login-submit').click();
    await expect(page.getByTestId('workspace-badge')).toContainText('user-');

    await expect(page.getByTestId('session-switcher')).toBeVisible();
    await page.getByRole('button', { name: /guest workspace/i }).click();
    await expectStudioRoute(page);
    await expect(page.getByTestId('workspace-badge')).toHaveText(guestWorkspace);

    await page.getByTestId('studio-back-to-landing').click();
    await page.getByTestId(`auth-home-resume-session-guest:${guestWorkspace}`).click();
    await expectStudioRoute(page);
    await expect(page.getByTestId('workspace-badge')).toHaveText(guestWorkspace);

    await assertConsoleClean();
  });

  test('Workspace playback deep links persist after refresh', async ({ page }) => {
    const assertConsoleClean = attachConsoleGuard(page);

    await signIn(page);
    await seedDraftStory(page, {
      title: uniqueTitle('Audit Playback Story'),
      premise: 'A debt court discovers its witness ledger has been rewritten by tomorrow.',
    });
    await selectMockProvider(page);
    await page.getByTestId('studio-run').click();

    await expect(page.getByTestId('studio-run-history')).toBeVisible();
    await expect(page.getByTestId('studio-run-playback')).toBeVisible();
    const deepLink = page.url();
    expect(deepLink).toContain('/studio?');
    expect(deepLink).toContain('view=playback');
    expect(deepLink).toContain('job=');

    await page.reload();
    await expectStudioRoute(page, 'playback');
    await expect(page).toHaveURL(deepLink);
    await expect(page.getByTestId('studio-run-playback')).toBeVisible();

    await assertConsoleClean();
  });

  test('form constraint failures surface clear state and recover after valid input', async ({
    page,
  }) => {
    const assertConsoleClean = attachConsoleGuard(page, {
      extraAllowList: [/status of 422/i],
    });

    await launchGuest(page);

    await page.getByTestId('studio-title-input').fill(uniqueTitle('Audit Validation Story'));
    await page.getByTestId('studio-premise-input').fill('too short');
    await page.getByTestId('studio-target-chapters-input').fill('3');
    await page.getByTestId('studio-create-draft').click();

    await expect(page.getByText('Request validation failed')).toBeVisible();

    const recoveredTitle = uniqueTitle('Audit Validation Recovery');
    await page.getByTestId('studio-title-input').fill(recoveredTitle);
    await page.getByTestId('studio-premise-input').fill(
      'An archivist must rewrite a city treaty before dawn to prevent a civil war.',
    );
    await page.getByTestId('studio-target-chapters-input').fill('3');
    await page.getByTestId('studio-create-draft').click();

    await expect(page.getByTestId('studio-active-title')).toHaveText(recoveredTitle);
    await expect(page.getByText('Request validation failed')).toHaveCount(0);

    await assertConsoleClean();
  });

  test('gateway and network failures are actionable and sanitized', async ({ page }) => {
    const assertConsoleClean = attachConsoleGuard(page, {
      extraAllowList: [/Failed to load resource/i, /ERR_FAILED/i],
    });

    await page.route('**/api/auth/login', async (route) => {
      if (route.request().method() !== 'POST') {
        await route.continue();
        return;
      }
      await route.fulfill({
        status: 503,
        contentType: 'text/html; charset=utf-8',
        body: '<html><body>upstream unavailable</body></html>',
      });
    });

    await page.goto('/auth/login');
    await page.getByTestId('auth-login-password').fill('demo-password');
    await page.getByTestId('auth-login-submit').click();

    await expect(page.getByTestId('auth-login-error')).toHaveText(
      'Service temporarily unavailable. Start the backend API and retry.',
    );
    await expect(page.getByTestId('auth-login-error')).not.toContainText('<html');

    await page.unroute('**/api/auth/login');

    await page.route('**/api/guest/session', async (route) => {
      if (route.request().method() !== 'POST') {
        await route.continue();
        return;
      }
      await route.abort('failed');
    });

    await page.getByTestId('auth-login-guest').click();
    await expect(page.getByTestId('auth-login-error')).toHaveText(
      'Service temporarily unavailable. Start the backend API and retry.',
    );
    await expect(page.getByTestId('auth-login-error')).not.toContainText('Failed to fetch');

    await assertConsoleClean();
  });
});
