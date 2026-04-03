import { test, expect, type Page } from '@playwright/test';

function uniqueTitle(prefix: string) {
  return `${prefix} ${Math.random().toString(36).slice(2, 8)}`;
}

async function signIn(page: Page) {
  await page.goto('/login');
  await page.getByTestId('login-email').fill('operator@novel.engine');
  await page.getByTestId('login-password').fill('demo-password');
  await page.getByTestId('login-submit').click();

  await expect(page).toHaveURL(/\/story$/);
  await expect(page.getByTestId('story-workbench-page')).toBeVisible();
}

async function launchGuest(page: Page) {
  await page.goto('/');
  await expect(page.getByTestId('landing-page')).toBeVisible();
  await page.getByTestId('launch-guest').click();

  await expect(page).toHaveURL(/\/story$/);
  await expect(page.getByTestId('story-workbench-page')).toBeVisible();
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
  await expect(page.getByTestId('story-workflow-state')).toContainText('Created draft manuscript');
}

test.describe('frontend smoke', () => {
  // The canonical signed-in flow uses a single stable user workspace
  // (`user-operator`). Keep the smoke suite serial so real API assertions
  // cannot race each other through shared server state.
  test.describe.configure({ mode: 'serial' });

  test('guest session can create and publish a story', async ({ page }) => {
    await launchGuest(page);
    await expect(page.getByTestId('workspace-badge')).toContainText('guest-');

    const storyTitle = uniqueTitle('Smoke Test Story');
    await seedDraftStory(page, {
      title: storyTitle,
      premise: 'A courier discovers a map that rewrites the borders of a flooded kingdom.',
      themes: 'survival, memory, river politics',
    });

    await page.getByTestId('story-generate-blueprint').click();
    await expect(page.getByTestId('story-workflow-state')).toContainText('Generated blueprint');

    await page.getByTestId('story-generate-outline').click();
    await expect(page.getByTestId('story-workflow-state')).toContainText('Generated outline');

    await page.getByTestId('story-draft-chapters').click();
    await expect(page.getByTestId('story-chapter-list')).toContainText('Chapter 1');

    await page.getByTestId('story-review').click();
    await expect(page.getByTestId('story-review-score')).toHaveText(/^\d+$/);
    await expect(page.getByTestId('story-review-panel')).toContainText('publish ready');

    await page.getByTestId('story-revise').click();
    await expect(page.getByTestId('story-review-panel')).toContainText('publish ready');

    await page.getByTestId('story-export').click();
    await expect(page.getByTestId('story-export-summary')).toBeVisible();

    await page.getByTestId('story-publish').click();
    await expect(page.getByTestId('story-active-title')).toHaveText(storyTitle);
    await expect(page.getByTestId('story-workflow-state')).toContainText('Published story');
  });

  test('login reaches the story workshop and can run the full pipeline', async ({ page }) => {
    await signIn(page);
    await page.getByTestId('story-title-input').fill(uniqueTitle('Pipeline Story'));
    await page.getByTestId('story-premise-input').fill(
      'A city archives every vow and begins erasing them one by one.',
    );
    await page.getByTestId('story-target-chapters-input').fill('3');
    await page.getByTestId('story-run-pipeline').click();

    await expect(page.getByTestId('story-pipeline-result')).toBeVisible();
    await expect(page.getByTestId('story-review-score')).toHaveText(/^\d+$/);
    await expect(page.getByTestId('story-review-panel')).toContainText('publish ready');
    await expect(page.getByTestId('story-workflow-state')).toContainText('Completed pipeline');
    await expect(page.getByTestId('workspace-badge')).toHaveText('user-operator');
  });

  test('current story rerun has explicit publish semantics and immutable playback evidence', async ({
    page,
  }) => {
    await signIn(page);

    await page.getByTestId('story-title-input').fill(uniqueTitle('Playback Story'));
    await page.getByTestId('story-premise-input').fill(
      'A debt archivist must restore erased vows before the city forgets its rulers.',
    );
    await page.getByTestId('story-target-chapters-input').fill('3');
    await page.getByTestId('story-run-pipeline').click();

    await expect(page.getByTestId('story-pipeline-result')).toBeVisible();
    await expect(page.getByTestId('story-run-provenance')).toContainText('Selected run');

    await expect(page.getByTestId('story-run-current-pipeline')).toHaveText(
      'Run current pipeline',
    );
    await page.getByTestId('story-current-publish-toggle').check();
    await expect(page.getByTestId('story-run-current-pipeline')).toHaveText(
      'Run current pipeline and publish',
    );
    await page.getByTestId('story-current-publish-toggle').uncheck();

    await page.getByTestId('story-run-current-pipeline').click();

    await expect(page.getByTestId('story-workflow-state')).toContainText(
      'Re-ran pipeline for current story',
    );
    await expect(page.getByTestId('story-run-history')).toBeVisible();
    await expect(page.getByTestId('story-run-playback')).toBeVisible();
    await expect(page.getByTestId('story-run-playback-stats')).toContainText('Artifacts');
    await expect(page.getByTestId('story-run-playback')).toContainText('Structural gate');
    await expect(page.getByTestId('story-run-playback')).toContainText('Semantic gate');
    await expect(page.getByTestId('story-run-playback')).toContainText('Publish gate');
  });

  test('login page reports invalid credentials and can still launch a guest workspace', async ({ page }) => {
    await page.goto('/login');

    await page.getByTestId('login-password').fill('wrong-password');
    await page.getByTestId('login-submit').click();

    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByText('Invalid credentials')).toBeVisible();
    await page.getByTestId('login-back-to-landing').click();
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByTestId('landing-page')).toBeVisible();

    await page.getByTestId('landing-sign-in').click();
    await expect(page).toHaveURL(/\/login$/);

    await page.getByRole('button', { name: 'Continue as guest writer' }).click();

    await expect(page).toHaveURL(/\/story$/);
    await expect(page.getByTestId('story-workbench-page')).toBeVisible();
    await expect(page.getByTestId('workspace-badge')).toContainText('guest-');
  });

  test('guest workspace can return to landing and resume through the app shell', async ({
    page,
  }) => {
    await launchGuest(page);

    const workspaceBadge = page.getByTestId('workspace-badge');
    const workspaceId = await workspaceBadge.textContent();
    await expect(workspaceBadge).toContainText('guest-');

    await page.getByTestId('story-back-to-landing').click();
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByTestId('landing-page')).toBeVisible();

    await page.getByTestId('app-shell-nav').getByRole('link', { name: 'Workshop' }).click();
    await expect(page).toHaveURL(/\/story$/);
    await expect(page.getByTestId('story-workbench-page')).toBeVisible();
    await expect(page.getByTestId('workspace-badge')).toHaveText(workspaceId ?? '');
  });

  test('multiple manuscripts can be created and switched from the library', async ({ page }) => {
    await launchGuest(page);

    const firstTitle = uniqueTitle('Library Story One');
    await seedDraftStory(page, {
      title: firstTitle,
      premise: 'A river judge inherits a city where every bridge keeps a secret ledger.',
    });

    const secondTitle = uniqueTitle('Library Story Two');
    await seedDraftStory(page, {
      title: secondTitle,
      premise: 'A lighthouse courier must deliver letters to ships that no longer exist.',
    });

    await expect(page.getByTestId('story-library-summary')).toContainText('2 manuscript');
    await expect(page.getByTestId('story-active-title')).toHaveText(secondTitle);

    await page
      .getByTestId('story-list')
      .getByRole('button', { name: new RegExp(firstTitle, 'i') })
      .click();
    await expect(page.getByTestId('story-active-title')).toHaveText(firstTitle);

    await page
      .getByTestId('story-list')
      .getByRole('button', { name: new RegExp(secondTitle, 'i') })
      .click();
    await expect(page.getByTestId('story-active-title')).toHaveText(secondTitle);
  });

  test('login replaces a guest workspace with the user workspace', async ({ page }) => {
    await launchGuest(page);
    await expect(page.getByTestId('workspace-badge')).toContainText('guest-');

    await page.getByRole('button', { name: 'Sign out' }).click();
    await expect(page).toHaveURL(/\/$/);

    await page.getByRole('link', { name: 'Sign in' }).click();
    await page.getByTestId('login-email').fill('operator@novel.engine');
    await page.getByTestId('login-password').fill('demo-password');
    await page.getByTestId('login-submit').click();

    await expect(page).toHaveURL(/\/story$/);
    await expect(page.getByTestId('story-workbench-page')).toBeVisible();
    await expect(page.getByTestId('workspace-badge')).toHaveText('user-operator');
  });

  test('launching a guest workspace after login resets back to a guest author id', async ({
    page,
  }) => {
    await signIn(page);
    await expect(page.getByTestId('workspace-badge')).toHaveText('user-operator');

    await page.getByTestId('story-back-to-landing').click();
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByTestId('landing-page')).toBeVisible();

    await page.getByTestId('launch-guest').click();

    await expect(page).toHaveURL(/\/story$/);
    await expect(page.getByTestId('story-workbench-page')).toBeVisible();
    await expect(page.getByTestId('workspace-badge')).toContainText('guest-');
    await expect(page.getByTestId('story-session-summary')).toContainText(
      'Guest author workspace',
    );
  });

  test('direct story access restores the session shell', async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem(
        'novel-engine-session',
        JSON.stringify({
          kind: 'guest',
          workspaceId: 'workspace-direct-test',
        }),
      );
    });

    await page.goto('/story');

    await expect(page.getByTestId('story-workbench-page')).toBeVisible();
    await expect(page.getByTestId('workspace-badge')).toContainText('workspace-direct-test');
    await expect(page.getByTestId('story-create-form')).toBeVisible();
    await expect(page.getByTestId('story-session-panel')).toContainText('workspace-direct-test');
  });
});
