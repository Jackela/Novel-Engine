import { test, expect } from '@playwright/test';

test.describe('frontend smoke', () => {
  test('guest session can create and publish a story', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByTestId('landing-page')).toBeVisible();
    await page.getByTestId('launch-guest').click();

    await expect(page).toHaveURL(/\/story$/);
    await expect(page.getByTestId('story-workbench-page')).toBeVisible();
    await expect(page.getByTestId('workspace-badge')).toContainText('guest-');

    await page.getByTestId('story-title-input').fill('Smoke Test Story');
    await page.getByTestId('story-premise-input').fill(
      'A courier discovers a map that rewrites the borders of a flooded kingdom.',
    );
    await page.getByTestId('story-target-chapters-input').fill('3');
    await page.getByTestId('story-themes-input').fill('survival, memory, river politics');
    await page.getByTestId('story-create-draft').click();

    await expect(page.getByTestId('story-active-title')).toHaveText('Smoke Test Story');
    await expect(page.getByTestId('story-workflow-state')).toContainText('Created draft manuscript');

    await page.getByTestId('story-generate-blueprint').click();
    await expect(page.getByTestId('story-workflow-state')).toContainText('Generated blueprint');

    await page.getByTestId('story-generate-outline').click();
    await expect(page.getByTestId('story-workflow-state')).toContainText('Generated outline');

    await page.getByTestId('story-draft-chapters').click();
    await expect(page.getByTestId('story-chapter-list')).toContainText('Chapter 1');

    await page.getByTestId('story-review').click();
    await expect(page.getByTestId('story-review-score')).toHaveText('100');

    await page.getByTestId('story-revise').click();
    await expect(page.getByTestId('story-review-panel')).toContainText('publish ready');

    await page.getByTestId('story-export').click();
    await expect(page.getByTestId('story-export-summary')).toBeVisible();

    await page.getByTestId('story-publish').click();
    await expect(page.getByTestId('story-active-title')).toHaveText('Smoke Test Story');
    await expect(page.getByTestId('story-workflow-state')).toContainText('Published story');
  });

  test('login reaches the story workshop and can run the full pipeline', async ({ page }) => {
    await page.goto('/login');

    await page.getByTestId('login-email').fill('operator@novel.engine');
    await page.getByTestId('login-password').fill('demo-password');
    await page.getByTestId('login-submit').click();

    await expect(page).toHaveURL(/\/story$/);
    await expect(page.getByTestId('story-workbench-page')).toBeVisible();

    await page.getByTestId('story-title-input').fill('Pipeline Story');
    await page.getByTestId('story-premise-input').fill(
      'A city archives every vow and begins erasing them one by one.',
    );
    await page.getByTestId('story-target-chapters-input').fill('3');
    await page.getByTestId('story-run-pipeline').click();

    await expect(page.getByTestId('story-pipeline-result')).toBeVisible();
    await expect(page.getByTestId('story-review-score')).toHaveText('100');
    await expect(page.getByTestId('story-workflow-state')).toContainText('Completed pipeline');
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
  });
});
