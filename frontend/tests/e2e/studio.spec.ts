import { expect, test, type Locator, type Page } from '@playwright/test';

async function expectNoOverlap(first: Locator, second: Locator) {
  const [firstBox, secondBox] = await Promise.all([first.boundingBox(), second.boundingBox()]);
  expect(firstBox).not.toBeNull();
  expect(secondBox).not.toBeNull();
  if (!firstBox || !secondBox) return;

  const overlaps = !(
    firstBox.x + firstBox.width <= secondBox.x ||
    secondBox.x + secondBox.width <= firstBox.x ||
    firstBox.y + firstBox.height <= secondBox.y ||
    secondBox.y + secondBox.height <= firstBox.y
  );
  expect(overlaps).toBe(false);
}

async function expectResponsiveStudioLayout(page: Page) {
  const tabs = page.getByRole('tab');
  await expect(tabs).toHaveCount(5);
  const tabTops = await tabs.evaluateAll((items) =>
    items.map((item) => item.getBoundingClientRect().top),
  );
  expect(Math.max(...tabTops) - Math.min(...tabTops)).toBeLessThanOrEqual(1);

  const overflow = await page.evaluate(() => {
    const editor = document.querySelector('.studio-editor');
    return {
      document: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      editor: editor ? editor.scrollWidth - editor.clientWidth : Number.POSITIVE_INFINITY,
    };
  });
  expect(overflow.document).toBeLessThanOrEqual(0);
  expect(overflow.editor).toBeLessThanOrEqual(0);

  const order = await page.evaluate(() => {
    const rect = (selector: string) =>
      document.querySelector(selector)?.getBoundingClientRect().top;
    return {
      nav: rect('.studio-nav'),
      editor: rect('.studio-editor'),
      inspector: rect('.studio-inspector'),
    };
  });
  if ((page.viewportSize()?.width ?? 0) <= 949) {
    expect(order.editor).not.toBeUndefined();
    expect(order.nav).not.toBeUndefined();
    expect(order.inspector).not.toBeUndefined();
    expect(order.editor).toBeLessThanOrEqual(order.nav ?? Number.POSITIVE_INFINITY);
    expect(order.editor).toBeLessThanOrEqual(order.inspector ?? Number.POSITIVE_INFINITY);
  }

  const title = page.getByRole('textbox', { name: 'Document title' });
  const saveStatus = page.locator('.save-state');
  const wordCount = page.locator('.editor-header > span');
  await expectNoOverlap(title, saveStatus);
  await expectNoOverlap(title, wordCount);
  await expectNoOverlap(saveStatus, wordCount);
}

test('guest writes, accepts an AI proposal, reviews history, and exports', async ({ page }) => {
  test.setTimeout(120_000);
  await page.goto('/');
  await page.getByRole('button', { name: /24-hour guest studio/i }).click();
  await expect(page).toHaveURL(/\/projects$/);

  await page.getByLabel('Title').fill('The Glass Harbor');
  await page.getByRole('button', { name: /create project/i }).click();
  await expect(page).toHaveURL(/\/projects\/[^/]+\/manuscript/);
  const saveStatus = page.locator('.studio-editor .save-state');
  await expect(saveStatus).toHaveText(/saved/i);
  await expect(saveStatus).toHaveAttribute('aria-live', 'polite');
  await expect(saveStatus).toHaveAttribute('aria-atomic', 'true');

  await page.getByRole('button', { name: 'Add Outline' }).click();
  await expect(page.getByRole('textbox', { name: 'Document title' })).toHaveValue('Outline 1');
  await page.getByRole('button', { name: 'Add Characters' }).click();
  await expect(page.getByRole('textbox', { name: 'Document title' })).toHaveValue('Characters 1');
  await page.getByRole('button', { name: 'Chapter 1', exact: true }).click();

  const editor = page.locator('.cm-content');
  const editorRoot = page.locator('.cm-editor');
  await expect(editor).toBeVisible();
  await page.getByRole('textbox', { name: 'Document title' }).focus();
  await page.keyboard.press('Tab');
  await expect(editor).toBeFocused();
  const focusOutline = await editorRoot.evaluate((element) => {
    const style = getComputedStyle(element);
    return { style: style.outlineStyle, width: Number.parseFloat(style.outlineWidth) };
  });
  expect(focusOutline.style).not.toBe('none');
  expect(focusOutline.width).toBeGreaterThanOrEqual(2);
  await page.keyboard.press('Control+A');
  await page.keyboard.type('# Chapter 1\n\nThe harbor bell rang twice.');
  await expect(saveStatus).toHaveText(/saved/i, { timeout: 10_000 });

  await page.getByPlaceholder('Describe the change or direction...').fill('Bring in the storm.');
  await page.getByRole('button', { name: 'Continue' }).click();
  await expect(page.getByText('Proposed Markdown')).toBeVisible();
  await page.getByRole('button', { name: 'Accept' }).click();

  const inspector = page.locator('.studio-inspector');
  await inspector.getByRole('tab', { name: 'History' }).click();
  await expect(page.getByText('Revision history')).toBeVisible();
  const restoreButtons = page.getByRole('button', { name: 'Restore revision' });
  await expect(restoreButtons).not.toHaveCount(0);
  await restoreButtons.first().click();

  await page.locator('.section-nav').getByRole('button', { name: 'Review' }).click();
  await expect(page.getByRole('heading', { name: 'Review findings' })).toBeVisible();

  await page.locator('.section-nav').getByRole('button', { name: 'Export' }).click();
  await expect(page.getByRole('heading', { name: 'Export project' })).toBeVisible();
  const download = page.waitForEvent('download');
  await page.locator('.export-format').first().click();
  expect((await download).suggestedFilename()).toMatch(/\.md$/);
  await page.locator('.section-nav').getByRole('button', { name: 'History' }).click();
  await expect(page.getByRole('heading', { name: 'Revision history' })).toBeVisible();

  await page.locator('.section-nav').getByRole('button', { name: 'Manuscript' }).click();

  for (const viewport of [
    { width: 1440, height: 900 },
    { width: 1024, height: 900 },
    { width: 949, height: 900 },
    { width: 900, height: 900 },
    { width: 800, height: 900 },
    { width: 375, height: 812 },
  ]) {
    await page.setViewportSize(viewport);
    await page.getByRole('textbox', { name: 'Document title' }).focus();
    await page.keyboard.press('Tab');
    await expect(editor).toBeFocused();
    await expectResponsiveStudioLayout(page);
  }

  const inspectorTabs = page.locator('.studio-inspector');
  const firstTab = inspectorTabs.getByRole('tab').first();
  await firstTab.focus();
  await page.keyboard.press('ArrowRight');
  await expect(inspectorTabs.getByRole('tab').nth(1)).toHaveAttribute('tabindex', '0');
  await page.keyboard.press('Home');
  await expect(firstTab).toHaveAttribute('tabindex', '0');
  await page.keyboard.press('End');
  await expect(inspectorTabs.getByRole('tab').last()).toHaveAttribute('tabindex', '0');

  await page.emulateMedia({ reducedMotion: 'reduce' });
  const motion = await page.locator('.studio').evaluate((element) => {
    const style = getComputedStyle(element);
    return { transitionDuration: style.transitionDuration, animationName: style.animationName };
  });
  expect(motion.transitionDuration).toMatch(/^(0s|1e-05s|0\.01ms)$/);
  expect(motion.animationName).toBe('none');
});

test('offers explicit recovery actions after a save conflict', async ({ page }) => {
  test.setTimeout(60_000);
  let shouldConflict = true;
  await page.route('**/api/projects/*/documents/*', async (route) => {
    if (shouldConflict && route.request().method() === 'PUT') {
      shouldConflict = false;
      await route.fulfill({
        status: 409,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: {
            message: 'Document changed since the requested base revision.',
            current_revision_id: 'server-revision',
          },
        }),
      });
      return;
    }
    await route.continue();
  });

  await page.goto('/');
  await page.getByRole('button', { name: /24-hour guest studio/i }).click();
  await page.getByLabel('Title').fill('Conflict fixture');
  await page.getByRole('button', { name: /create project/i }).click();
  await expect(page).toHaveURL(/\/projects\/[^/]+\/manuscript/);

  const editor = page.locator('.cm-content');
  await editor.click();
  await page.keyboard.press('Control+A');
  await page.keyboard.type('Local draft that must be preserved.');

  await expect(page.getByRole('button', { name: 'Load latest (discard local)' })).toBeVisible({
    timeout: 10_000,
  });
  await expect(page.getByRole('button', { name: 'Keep local and retry overwrite' })).toBeVisible();
});
