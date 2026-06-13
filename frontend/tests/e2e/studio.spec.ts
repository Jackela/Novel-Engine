import { expect, test } from '@playwright/test';

test('guest writes, accepts an AI proposal, reviews history, and exports', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /24-hour guest studio/i }).click();
  await expect(page).toHaveURL(/\/projects$/);

  await page.getByLabel('Title').fill('The Glass Harbor');
  await page.getByRole('button', { name: /create project/i }).click();
  await expect(page).toHaveURL(/\/projects\/[^/]+\/manuscript/);
  await expect(page.getByText('saved', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'Add Outline' }).click();
  await expect(page.getByRole('textbox', { name: 'Document title' })).toHaveValue('Outline 1');
  await page.getByRole('button', { name: 'Add Characters' }).click();
  await expect(page.getByRole('textbox', { name: 'Document title' })).toHaveValue('Characters 1');
  await page.getByRole('button', { name: 'Chapter 1' }).click();

  const editor = page.locator('.cm-content');
  await editor.click();
  await page.keyboard.press('Control+A');
  await page.keyboard.type('# Chapter 1\n\nThe harbor bell rang twice.');
  await expect(page.getByText('saved', { exact: true })).toBeVisible({ timeout: 10_000 });

  await page.getByPlaceholder('Describe the change or direction...').fill('Bring in the storm.');
  await page.getByRole('button', { name: 'Continue' }).click();
  await expect(page.getByText('Proposed Markdown')).toBeVisible();
  await page.getByRole('button', { name: 'Accept' }).click();

  const inspector = page.locator('.studio-inspector');
  await inspector.getByRole('button', { name: 'History' }).click();
  await expect(page.getByText('Revision history')).toBeVisible();
  const restoreButtons = page.getByRole('button', { name: 'Restore revision' });
  await expect(restoreButtons).not.toHaveCount(0);
  await restoreButtons.first().click();

  await page.locator('.studio-topbar').getByRole('button', { name: 'Review' }).click();
  await expect(page.getByText('Review findings')).toBeVisible();

  await page.locator('.export-menu summary').click();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'MARKDOWN' }).click();
  expect((await download).suggestedFilename()).toMatch(/\.md$/);
});
