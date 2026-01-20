import { test, expect } from './fixtures';

test.describe('Weaver Workflow', () => {
  test('can add, drag, and connect nodes', async ({ page }) => {
    await page.goto('/weaver', { waitUntil: 'domcontentloaded' });

    await expect(page.getByRole('heading', { name: 'Story Weaver' })).toBeVisible();
    const canvas = page.locator('[data-testid="weaver-canvas"]');
    await expect(canvas).toBeAttached();

    await page.getByRole('button', { name: 'Character' }).click();
    const newCharacter = page
      .locator('.react-flow__node')
      .filter({ hasText: 'New Character' })
      .first();
    await expect(newCharacter).toBeVisible();

    const startBox = await newCharacter.boundingBox();
    expect(startBox).not.toBeNull();
    if (!startBox) return;

    await page.mouse.move(startBox.x + startBox.width / 2, startBox.y + startBox.height / 2);
    await page.mouse.down();
    await page.mouse.move(startBox.x + startBox.width / 2 + 120, startBox.y + startBox.height / 2 + 80);
    await page.mouse.up();

    const endBox = await newCharacter.boundingBox();
    expect(endBox).not.toBeNull();
    if (!endBox) return;

    await page.getByRole('button', { name: 'Event' }).click();
    const newEvent = page
      .locator('.react-flow__node')
      .filter({ hasText: 'New Event' })
      .first();
    await expect(newEvent).toBeVisible();

    const edgesBefore = await page.evaluate(() => {
      const store = (window as any).__weaverStore;
      return store?.getState().edges.length ?? 0;
    });

    await page.waitForFunction(() => {
      const store = (window as any).__weaverStore;
      if (!store) return false;
      const state = store.getState();
      const hasCharacter = state.nodes.some((node: any) => node.data?.name === 'New Character');
      const hasEvent = state.nodes.some((node: any) => node.data?.title === 'New Event');
      return hasCharacter && hasEvent;
    });

    await page.evaluate(() => {
      const store = (window as any).__weaverStore;
      if (!store) return;
      const state = store.getState();
      const source = state.nodes.find((node: any) => node.data?.name === 'New Character')?.id;
      const target = state.nodes.find((node: any) => node.data?.title === 'New Event')?.id;
      if (source && target) {
        state.onConnect({ source, target });
      }
    });

    await expect
      .poll(async () => {
        return await page.evaluate(() => {
          const store = (window as any).__weaverStore;
          return store?.getState().edges.length ?? 0;
        });
      }, { timeout: 5000 })
      .toBeGreaterThan(edgesBefore);
  });
});
