import { expect, test, type Page } from '@playwright/test';

function uniqueTitle(prefix: string) {
  return `${prefix} ${Math.random().toString(36).slice(2, 8)}`;
}

async function expectStoryRoute(page: Page, view: 'workspace' | 'playback' = 'workspace') {
  await expect(page).toHaveURL(
    view === 'playback' ? /\/story\?(.+&)?view=playback/ : /\/story(\?.*)?$/,
  );
  await expect(page.getByTestId('story-workbench-page')).toBeVisible();
  await expect(page.getByTestId('workspace-surface')).toBeVisible();
  await expect(page.getByTestId('playback-desk')).toBeVisible();
}

async function signIn(page: Page) {
  await page.goto('/login');
  await page.getByTestId('login-email').fill('operator@novel.engine');
  await page.getByTestId('login-password').fill('demo-password');
  await page.getByTestId('login-submit').click();
  await expectStoryRoute(page);
}

async function launchGuest(page: Page) {
  await page.goto('/');
  await expect(page.getByTestId('landing-page')).toBeVisible();
  await page.getByTestId('launch-guest').click();
  await expectStoryRoute(page);
}

async function seedDraftStory(
  page: Page,
  options: {
    title: string;
    premise: string;
    targetChapters?: number;
    themes?: string;
  },
) {
  await page.getByTestId('story-title-input').fill(options.title);
  await page.getByTestId('story-premise-input').fill(options.premise);
  await page
    .getByTestId('story-target-chapters-input')
    .fill(String(options.targetChapters ?? 3));
  await page
    .getByTestId('story-themes-input')
    .fill(options.themes ?? 'serial tension, debt, memory');
  await page.getByTestId('story-create-draft').click();

  await expect(page.getByTestId('story-active-title')).toHaveText(options.title);
  await expect(page.getByTestId('story-workflow-state')).toContainText(
    'Created draft manuscript',
  );
}

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

    await page.getByTestId('story-generate-blueprint').click();
    await page.getByTestId('story-generate-outline').click();
    await page.getByTestId('story-draft-chapters').click();
    await expect(page.getByTestId('story-chapter-list')).toContainText('Chapter 1');

    await page.getByTestId('story-review').click();
    await expect(page.getByTestId('story-review-score')).toHaveText(/^\d+$/);
    await page.getByTestId('story-revise').click();
    await page.getByTestId('story-export').click();
    await page.getByTestId('story-publish').click();

    await expect(page.getByTestId('story-active-title')).toHaveText(storyTitle);
    await expect(page.getByTestId('story-workflow-state')).toContainText('Published story');
    await expect(page.getByTestId('publish-verdict')).toContainText('zero warning ready');
  });

  test('login reaches the workshop and can run the full pipeline', async ({ page }) => {
    await signIn(page);
    await page.getByTestId('story-title-input').fill(uniqueTitle('Pipeline Story'));
    await page.getByTestId('story-premise-input').fill(
      'A city archives every vow and begins erasing them one by one.',
    );
    await page.getByTestId('story-target-chapters-input').fill('3');
    await page.getByTestId('story-run-pipeline').click();

    await expect(page.getByTestId('story-workflow-state')).toContainText('Completed pipeline');
    await expect(page.getByTestId('story-review-score')).toHaveText(/^\d+$/);
    await expect(page.getByTestId('workspace-badge')).toHaveText('user-operator');
    await expect(page.getByTestId('zero-warning-badge')).toContainText('zero warning');
  });

  test('rerunning the current story writes a playback deep link that survives refresh', async ({
    page,
  }) => {
    await signIn(page);

    await page.getByTestId('story-title-input').fill(uniqueTitle('Playback Story'));
    await page.getByTestId('story-premise-input').fill(
      'A debt archivist must restore erased vows before the city forgets its rulers.',
    );
    await page.getByTestId('story-target-chapters-input').fill('3');
    await page.getByTestId('story-run-pipeline').click();

    await page.getByTestId('story-current-publish-toggle').check();
    await expect(page.getByTestId('story-run-current-pipeline')).toHaveText(
      'Run current pipeline and publish',
    );
    await page.getByTestId('story-current-publish-toggle').uncheck();
    await page.getByTestId('story-run-current-pipeline').click();

    await expect(page.getByTestId('story-run-history')).toBeVisible();
    await expect(page.getByTestId('story-run-playback')).toBeVisible();
    const deepLink = page.url();
    expect(deepLink).toContain('/story?');
    expect(deepLink).toContain('view=playback');
    expect(deepLink).toContain('run=');

    await page.reload();
    await expectStoryRoute(page, 'playback');
    await expect(page.getByTestId('story-run-playback')).toBeVisible();
    await expect(page).toHaveURL(deepLink);
    await expect(page.getByTestId('playback-stage-timeline')).toBeVisible();
  });

  test('login page reports invalid credentials and can still launch a guest workspace', async ({
    page,
  }) => {
    await page.goto('/login');
    await page.getByTestId('login-password').fill('wrong-password');
    await page.getByTestId('login-submit').click();

    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByText('Invalid credentials')).toBeVisible();
    await page.getByTestId('login-back-to-landing').click();
    await expect(page.getByTestId('landing-page')).toBeVisible();
    await page.getByTestId('landing-sign-in').click();
    await page.getByRole('button', { name: 'Continue as guest writer' }).click();
    await expectStoryRoute(page);
    await expect(page.getByTestId('workspace-badge')).toContainText('guest-');
  });

  test('guest workspace can return to landing and resume from the saved session catalog', async ({
    page,
  }) => {
    await launchGuest(page);

    const workspaceId = await page.getByTestId('workspace-badge').textContent();
    await page.getByTestId('story-back-to-landing').click();
    await expect(page.getByTestId('landing-page')).toBeVisible();
    await expect(page.getByTestId('landing-session-catalog')).toBeVisible();
    await page.getByTestId(`landing-resume-session-guest:${workspaceId}`).click();

    await expectStoryRoute(page);
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

    await expect(page.getByTestId('story-library-summary')).toContainText('2 manuscript');
    await expect(page.getByTestId('story-active-title')).toHaveText(secondTitle);
    const secondUrl = page.url();

    await page
      .getByTestId('story-list')
      .getByRole('button', { name: new RegExp(firstTitle, 'i') })
      .click();
    await expect(page.getByTestId('story-active-title')).toHaveText(firstTitle);
    await expect(page).not.toHaveURL(secondUrl);

    await page
      .getByTestId('story-list')
      .getByRole('button', { name: new RegExp(secondTitle, 'i') })
      .click();
    await expect(page.getByTestId('story-active-title')).toHaveText(secondTitle);
    await expect(page).not.toHaveURL(firstUrl);
  });

  test('guest and user sessions coexist and can be switched from the guided shell', async ({
    page,
  }) => {
    await launchGuest(page);
    const guestWorkspace = await page.getByTestId('workspace-badge').textContent();

    await page.getByTestId('story-back-to-landing').click();
    await page.getByTestId('landing-sign-in').click();
    await page.getByTestId('login-email').fill('operator@novel.engine');
    await page.getByTestId('login-password').fill('demo-password');
    await page.getByTestId('login-submit').click();

    await expect(page.getByTestId('workspace-badge')).toHaveText('user-operator');
    await expect(page.getByTestId('session-switcher')).toBeVisible();
    await page.getByRole('button', { name: /guest workspace/i }).click();

    await expectStoryRoute(page);
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

    await page.goto('/story?view=workspace');
    await expectStoryRoute(page);
    await expect(page.getByTestId('workspace-badge')).toContainText('guest-direct-test');
    await expect(page.getByTestId('story-create-form')).toBeVisible();
    await expect(page.getByTestId('story-session-panel')).toContainText(
      'guest-direct-test',
    );
  });
});
