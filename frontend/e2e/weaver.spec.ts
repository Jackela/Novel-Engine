import { test, expect } from '../tests/e2e/fixtures';
import { safeGoto } from '../tests/e2e/utils/navigation';
import { scalePerf } from '../tests/e2e/utils/perf';

test.describe('Weaver Visual Workflow', () => {
  test('@weaver-smoke drag node, connect, and verify animated edge', async ({ page }) => {
    await safeGoto(page, '/weaver');

    await expect(page.getByRole('heading', { name: 'Story Weaver' })).toBeVisible({
      timeout: scalePerf(30_000),
    });

    await page.getByRole('button', { name: 'Character' }).click();
    await page.getByRole('button', { name: 'Event' }).click();

    await page.waitForFunction(() => {
      const store = (window as any).__weaverStore;
      if (!store) return false;
      const state = store.getState();
      const hasCharacter = state.nodes.some((node: any) => node.data?.name === 'New Character');
      const hasEvent = state.nodes.some((node: any) => node.data?.title === 'New Event');
      return hasCharacter && hasEvent;
    });

    const nodeId = await page.evaluate(() => {
      const store = (window as any).__weaverStore;
      const state = store.getState();
      return state.nodes.find((node: any) => node.data?.name === 'New Character')?.id;
    });
    expect(nodeId).toBeTruthy();

    const nodeLocator = page.locator(`.react-flow__node[data-id="${nodeId}"]`);
    await expect(nodeLocator).toBeVisible();

    const nodeBox = await nodeLocator.boundingBox();
    expect(nodeBox).not.toBeNull();
    if (!nodeBox) return;

    await page.mouse.move(nodeBox.x + nodeBox.width / 2, nodeBox.y + nodeBox.height / 2);
    await page.mouse.down();
    await page.mouse.move(nodeBox.x + nodeBox.width / 2 + 140, nodeBox.y + nodeBox.height / 2 + 90);
    await page.mouse.up();
    await page.waitForTimeout(200);

    await page.evaluate(() => {
      const store = (window as any).__weaverStore;
      const state = store.getState();
      const source = state.nodes.find((node: any) => node.data?.name === 'New Character')?.id;
      const target = state.nodes.find((node: any) => node.data?.title === 'New Event')?.id;
      if (source && target) {
        state.onConnect({ source, target });
      }
    });

    await expect
      .poll(() => page.locator('.react-flow__edge.animated').count(), { timeout: 5000 })
      .toBeGreaterThan(0);
  });
});
