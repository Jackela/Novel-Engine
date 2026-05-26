import { expect, test } from '@playwright/test';

import {
  expectStudioRoute,
  expectWorkflowState,
  launchGuest,
  seedDraftStory,
  selectMockProvider,
  signIn,
  uniqueTitle,
} from './helpers/studio-workflow';

test.describe('frontend smoke', () => {
  test.describe.configure({ mode: 'serial' });

  test('guest session can create, run, review, and export a workspace', async ({
    page,
  }) => {
    await launchGuest(page);
    await expect(page.getByTestId('workspace-badge')).toContainText('guest-');

    const storyTitle = uniqueTitle('Smoke Test Story');
    await seedDraftStory(page, {
      title: storyTitle,
      premise: 'A courier discovers a map that rewrites the borders of a flooded kingdom.',
      themes: 'survival, memory, river politics',
    });
    await selectMockProvider(page);

    await page.getByTestId('studio-run').click();
    await expectWorkflowState(page, 'run completed');
    await expect(page.getByTestId('studio-chapter-list')).toContainText('chapter-001.md');
    await expect(page.getByTestId('publish-verdict')).toContainText('export allowed');

    await page.getByTestId('studio-review').click();
    await expectWorkflowState(page, 'review completed');
    await page.getByTestId('studio-export').click();
    await expectWorkflowState(page, 'export completed');
    await expect(page.getByTestId('studio-active-title')).toHaveText(storyTitle);
  });

  test('login reaches the workshop and can run target chapters', async ({ page }) => {
    await signIn(page);
    await seedDraftStory(page, {
      title: uniqueTitle('Signed Story'),
      premise: 'A city archives every vow and begins erasing them one by one.',
    });
    await selectMockProvider(page);
    await page.getByTestId('studio-run').click();

    await expectWorkflowState(page, 'run completed');
    await expect(page.getByTestId('workspace-badge')).toContainText('user-');
    await expect(page.getByTestId('export-gate-badge')).toContainText('export allowed');
  });

  test('workspace job deep links survive refresh', async ({ page }) => {
    await signIn(page);
    await seedDraftStory(page, {
      title: uniqueTitle('Playback Story'),
      premise: 'A debt archivist must restore erased vows before the city forgets its rulers.',
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
    await expect(page.getByTestId('studio-run-playback')).toBeVisible();
    await expect(page).toHaveURL(deepLink);
  });

  test('login page reports invalid credentials and can still launch a guest workspace', async ({
    page,
  }) => {
    await page.goto('/auth/login');
    await page.getByTestId('auth-login-password').fill('wrong-password');
    await page.getByTestId('auth-login-submit').click();

    await expect(page).toHaveURL(/\/auth\/login$/);
    await expect(page.getByText('Invalid credentials')).toBeVisible();
    await page.getByTestId('auth-login-back-home').click();
    await expect(page.getByTestId('auth-home-page')).toBeVisible();
    await page.getByTestId('auth-home-go-login').click();
    await page.getByTestId('auth-login-guest').click();
    await expectStudioRoute(page);
    await expect(page.getByTestId('workspace-badge')).toContainText('guest-');
  });

  test('guest workspace can return to landing and resume from the saved session catalog', async ({
    page,
  }) => {
    await launchGuest(page);

    const workspaceId = await page.getByTestId('workspace-badge').textContent();
    await page.getByTestId('studio-back-to-landing').click();
    await expect(page.getByTestId('auth-home-page')).toBeVisible();
    await expect(page.getByTestId('auth-home-session-catalog')).toBeVisible();
    await page.getByTestId(`auth-home-resume-session-guest:${workspaceId}`).click();

    await expectStudioRoute(page);
    await expect(page.getByTestId('workspace-badge')).toHaveText(workspaceId ?? '');
  });

  test('multiple workspaces can be created and switched while keeping the URL addressable', async ({
    page,
  }) => {
    await launchGuest(page);

    const firstTitle = uniqueTitle('Library Story One');
    await seedDraftStory(page, {
      title: firstTitle,
      premise: 'A river judge inherits a city where every bridge keeps a secret ledger.',
    });
    const firstUrl = page.url();

    const secondTitle = uniqueTitle('Library Story Two');
    await seedDraftStory(page, {
      title: secondTitle,
      premise: 'A lighthouse courier must deliver letters to ships that no longer exist.',
    });

    await expect(page.getByTestId('studio-library-summary')).toContainText('2 workspace');
    await expect(page.getByTestId('studio-active-title')).toHaveText(secondTitle);
    const secondUrl = page.url();

    await page
      .getByTestId('studio-list')
      .getByRole('button', { name: new RegExp(firstTitle, 'i') })
      .click();
    await expect(page.getByTestId('studio-active-title')).toHaveText(firstTitle);
    await expect(page).not.toHaveURL(secondUrl);

    await page
      .getByTestId('studio-list')
      .getByRole('button', { name: new RegExp(secondTitle, 'i') })
      .click();
    await expect(page.getByTestId('studio-active-title')).toHaveText(secondTitle);
    await expect(page).not.toHaveURL(firstUrl);
  });

  test('guest and user sessions coexist and can be switched from the guided shell', async ({
    page,
  }) => {
    await launchGuest(page);
    const guestWorkspace = await page.getByTestId('workspace-badge').textContent();

    await page.getByTestId('studio-back-to-landing').click();
    await page.getByTestId('auth-home-go-login').click();
    await page.getByTestId('auth-login-email').fill('operator@novel.engine');
    await page.getByTestId('auth-login-password').fill('demo-password');
    await page.getByTestId('auth-login-submit').click();

    await expect(page.getByTestId('workspace-badge')).toContainText('user-');
    await expect(page.getByTestId('session-switcher')).toBeVisible();
    await page.getByRole('button', { name: /guest workspace/i }).click();

    await expectStudioRoute(page);
    await expect(page.getByTestId('workspace-badge')).toHaveText(guestWorkspace ?? '');
  });

  test('direct studio access restores a guest session from the session catalog', async ({
    page,
  }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem(
        'novel-engine-session-catalog',
        JSON.stringify({
          version: 2,
          activeSessionId: 'guest:guest-direct-test',
          sessions: [
            {
              id: 'guest:guest-direct-test',
              kind: 'guest',
              workspaceId: 'guest-direct-test',
              lastView: 'workspace',
            },
          ],
        }),
      );
    });

    await page.goto('/studio?view=workspace');
    await expectStudioRoute(page);
    await expect(page.getByTestId('workspace-badge')).toContainText('guest-direct-test');
    await expect(page.getByTestId('studio-create-form')).toBeVisible();
    await expect(page.getByTestId('studio-session-panel')).toContainText(
      'guest-direct-test',
    );
  });
});
