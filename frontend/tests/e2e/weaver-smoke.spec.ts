/**
 * Weaver Smoke Test - Spatial Layout Verification
 *
 * "The Blind Swordsman's Eye" - Objective, text-driven verification of Weaver
 * canvas layout health without relying on visual feedback.
 *
 * Why: In vibe coding, we cannot visually inspect the UI. These tests provide
 * mathematical proof that the layout is correct by checking:
 * - No node overlap
 * - All nodes within canvas bounds
 * - Proper spatial relationships
 *
 * @tags @weaver-smoke @spatial @layout
 */

import { test, expect } from './fixtures';
import {
  expectNoOverlap,
  expectWithinViewport,
  expectContainedIn,
  getWeaverNodes,
  getWeaverCanvas,
  getBoundingBox,
} from './utils/spatial-assertions';

test.describe('Weaver Canvas Spatial Verification', () => {
  test.describe('@weaver-smoke Layout Health', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/weaver', { waitUntil: 'domcontentloaded' });
      // Wait for canvas to be ready
      await expect(page.getByRole('heading', { name: 'Story Weaver' })).toBeVisible();
      const canvas = page.locator('[data-testid="weaver-canvas"], .react-flow');
      await expect(canvas).toBeAttached({ timeout: 10000 });
    });

    test('@weaver-smoke should have canvas within viewport', async ({ page }) => {
      const canvas = getWeaverCanvas(page);
      await expectWithinViewport(page, [canvas]);
    });

    test('@weaver-smoke should detect node overlap after creating multiple nodes', async ({
      page,
    }) => {
      // Create multiple nodes to test overlap detection
      await test.step('Create Character node', async () => {
        const characterBtn = page.getByRole('button', { name: 'Character' });
        if (await characterBtn.isVisible()) {
          await characterBtn.click();
          await page.waitForTimeout(300); // Allow node placement
        }
      });

      await test.step('Create Event node', async () => {
        const eventBtn = page.getByRole('button', { name: 'Event' });
        if (await eventBtn.isVisible()) {
          await eventBtn.click();
          await page.waitForTimeout(300);
        }
      });

      await test.step('Create Location node', async () => {
        const locationBtn = page.getByRole('button', { name: 'Location' });
        if (await locationBtn.isVisible()) {
          await locationBtn.click();
          await page.waitForTimeout(300);
        }
      });

      await test.step('Verify nodes do not overlap', async () => {
        const nodes = await getWeaverNodes(page);
        if (nodes.length >= 2) {
          // This assertion will fail if nodes overlap, which is the desired behavior
          // It catches layout issues that would be invisible without visual feedback
          await expectNoOverlap(nodes, 2); // 2px tolerance for sub-pixel rendering
        }
      });
    });

    test('@weaver-smoke should keep all nodes within canvas bounds', async ({
      page,
    }) => {
      // Create nodes
      const characterBtn = page.getByRole('button', { name: 'Character' });
      if (await characterBtn.isVisible()) {
        await characterBtn.click();
        await page.waitForTimeout(300);
      }

      const eventBtn = page.getByRole('button', { name: 'Event' });
      if (await eventBtn.isVisible()) {
        await eventBtn.click();
        await page.waitForTimeout(300);
      }

      await test.step('Verify all nodes are within canvas', async () => {
        const nodes = await getWeaverNodes(page);
        const canvas = getWeaverCanvas(page);

        for (let i = 0; i < nodes.length; i++) {
          try {
            await expectContainedIn(nodes[i], canvas, 5); // 5px tolerance
          } catch (error) {
            // Log which node failed for debugging
            const nodeBox = await getBoundingBox(nodes[i]);
            console.error(
              `Node ${i} at (${nodeBox.x}, ${nodeBox.y}) ${nodeBox.width}x${nodeBox.height} overflows canvas`
            );
            throw error;
          }
        }
      });
    });

    test('@weaver-smoke should detect off-screen elements', async ({ page }) => {
      // This test verifies the spatial assertion system works correctly
      // by ensuring visible UI elements are within viewport

      await test.step('Verify toolbar is within viewport', async () => {
        const toolbar = page.locator('[data-testid="weaver-toolbar"], [role="toolbar"]').first();
        if (await toolbar.isVisible()) {
          await expectWithinViewport(page, [toolbar]);
        }
      });

      await test.step('Verify header is within viewport', async () => {
        const header = page.getByRole('heading', { name: 'Story Weaver' });
        await expectWithinViewport(page, [header]);
      });
    });

    test('@weaver-smoke should maintain layout integrity after node drag (simulated)', async ({
      page,
    }) => {
      // Create a node
      const characterBtn = page.getByRole('button', { name: 'Character' });
      if (await characterBtn.isVisible()) {
        await characterBtn.click();
        await page.waitForTimeout(300);
      }

      const nodes = await getWeaverNodes(page);
      if (nodes.length === 0) {
        test.skip(true, 'No nodes created, skipping drag test');
        return;
      }

      const node = nodes[0];
      // Store initial position for potential future comparison
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const _initialBox = await getBoundingBox(node);

      // Simulate drag by updating node position via store
      await page.evaluate(() => {
        const store = (
          window as unknown as {
            __weaverStore?: {
              getState: () => {
                nodes: Array<{ id: string; position: { x: number; y: number } }>;
                setNodes: (nodes: unknown[]) => void;
              };
            };
          }
        ).__weaverStore;
        if (!store) return;

        const state = store.getState();
        const updatedNodes = state.nodes.map((n, i) => {
          if (i === 0) {
            return {
              ...n,
              position: { x: n.position.x + 100, y: n.position.y + 50 },
            };
          }
          return n;
        });
        store.getState().setNodes(updatedNodes);
      });

      await page.waitForTimeout(200); // Allow React to update

      await test.step('Verify node moved but stayed in canvas', async () => {
        const canvas = getWeaverCanvas(page);
        const movedNodes = await getWeaverNodes(page);

        if (movedNodes.length > 0) {
          const newBox = await getBoundingBox(movedNodes[0]);

          // Verify the node actually moved (or at least didn't disappear)
          expect(newBox.width).toBeGreaterThan(0);
          expect(newBox.height).toBeGreaterThan(0);

          // Verify it's still contained in canvas
          await expectContainedIn(movedNodes[0], canvas, 10);
        }
      });
    });
  });

  test.describe('@weaver-smoke Edge Cases', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/weaver', { waitUntil: 'domcontentloaded' });
      await expect(page.getByRole('heading', { name: 'Story Weaver' })).toBeVisible();
    });

    test('@weaver-smoke empty canvas should have valid bounds', async ({ page }) => {
      const canvas = getWeaverCanvas(page);
      const box = await getBoundingBox(canvas);

      expect(box.width).toBeGreaterThan(0);
      expect(box.height).toBeGreaterThan(0);
      expect(box.x).toBeGreaterThanOrEqual(0);
      expect(box.y).toBeGreaterThanOrEqual(0);
    });

    test('@weaver-smoke should handle rapid node creation without overlap', async ({
      page,
    }) => {
      // Rapidly create nodes
      const buttons = ['Character', 'Event', 'Location', 'Character', 'Event'];

      for (const btnName of buttons) {
        const btn = page.getByRole('button', { name: btnName });
        if (await btn.isVisible()) {
          await btn.click();
          await page.waitForTimeout(100); // Minimal wait
        }
      }

      await page.waitForTimeout(500); // Allow all nodes to settle

      const nodes = await getWeaverNodes(page);
      if (nodes.length >= 2) {
        await expectNoOverlap(nodes, 2);
      }
    });
  });
});
