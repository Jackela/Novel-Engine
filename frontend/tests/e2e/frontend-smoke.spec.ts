import { expect, test } from '@playwright/test';

import {
  expectStudioRoute,
  launchGuest,
  seedDraftStory,
  signIn,
  uniqueTitle,
} from './helpers/studio-workflow';

test.describe('frontend smoke', () => {
  test.describe.configure({ mode: 'serial' });

  test('guest session can create and publish a story', async ({ page }) => {
    await launchGuest(page);
    await expect(page.getByTestId('workspace-badge')).toContainText('guest-');
    await expect(page.getByTestId('guided-next-action')).toBeVisible();

    const storyTitle = uniqueTitle('Smoke Test Story');
    await seedDraftStory(page, {
      title: storyTitle,
      premise: 'A courier discovers a map that rewrites the borders of a flooded kingdom.',
      themes: 'survival, memory, river politics',
    });
    await expect(page.getByTestId('studio-workflow-state')).toContainText(
      'Created draft manuscript',
    );

    await page.getByTestId('studio-generate-blueprint').click();
    await page.getByTestId('studio-generate-outline').click();
    await page.getByTestId('studio-draft-chapters').click();
    await expect(page.getByTestId('studio-chapter-list')).toContainText('Chapter 1');

    await page.getByTestId('studio-review').click();
    await expect(page.getByTestId('studio-review-score')).toHaveText(/^\d+$/);
    await page.getByTestId('studio-revise').click();
    await page.getByTestId('studio-export').click();
    await page.getByTestId('studio-publish').click();

    await expect(page.getByTestId('studio-active-title')).toHaveText(storyTitle);
    await expect(page.getByTestId('studio-workflow-state')).toContainText('Published story');
    await expect(page.getByTestId('publish-verdict')).toContainText('zero warning ready');
  });

  test('login reaches the workshop and can run the full pipeline', async ({ page }) => {
    await signIn(page);
    await page.getByTestId('studio-title-input').fill(uniqueTitle('Pipeline Story'));
    await page.getByTestId('studio-premise-input').fill(
      'A city archives every vow and begins erasing them one by one.',
    );
    await page.getByTestId('studio-target-chapters-input').fill('3');
    await page.getByTestId('studio-run-pipeline').click();

    await expect(page.getByTestId('studio-workflow-state')).toContainText('Completed pipeline');
    await expect(page.getByTestId('studio-review-score')).toHaveText(/^\d+$/);
    await expect(page.getByTestId('workspace-badge')).toHaveText('user-operator');
    await expect(page.getByTestId('zero-warning-badge')).toContainText('zero warning');
  });

  test('rerunning the current story writes a playback deep link that survives refresh', async ({
    page,
  }) => {
    await signIn(page);

    await page.getByTestId('studio-title-input').fill(uniqueTitle('Playback Story'));
    await page.getByTestId('studio-premise-input').fill(
      'A debt archivist must restore erased vows before the city forgets its rulers.',
    );
    await page.getByTestId('studio-target-chapters-input').fill('3');
    await page.getByTestId('studio-run-pipeline').click();

    await page.getByTestId('studio-current-publish-toggle').check();
    await expect(page.getByTestId('studio-run-current-pipeline')).toHaveText(
      'Run current pipeline and publish',
    );
    await page.getByTestId('studio-current-publish-toggle').uncheck();
    await page.getByTestId('studio-run-current-pipeline').click();

    await expect(page.getByTestId('studio-run-history')).toBeVisible();
    await expect(page.getByTestId('studio-run-playback')).toBeVisible();
    const deepLink = page.url();
    expect(deepLink).toContain('/studio?');
    expect(deepLink).toContain('view=playback');
    expect(deepLink).toContain('run=');

    await page.reload();
    await expectStudioRoute(page, 'playback');
    await expect(page.getByTestId('studio-run-playback')).toBeVisible();
    await expect(page).toHaveURL(deepLink);
    await expect(page.getByTestId('playback-stage-timeline')).toBeVisible();
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

  test('multiple manuscripts can be created and switched while keeping the story id in the URL', async ({
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

    await expect(page.getByTestId('studio-library-summary')).toContainText('2 manuscript');
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

    await expect(page.getByTestId('workspace-badge')).toHaveText('user-operator');
    await expect(page.getByTestId('session-switcher')).toBeVisible();
    await page.getByRole('button', { name: /guest workspace/i }).click();

    await expectStudioRoute(page);
    await expect(page.getByTestId('workspace-badge')).toHaveText(guestWorkspace ?? '');
  });

  test('direct story access restores a guest session from the session catalog', async ({
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
