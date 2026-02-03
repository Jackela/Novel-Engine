/**
 * Spatial Assertions for Layout Verification
 *
 * "The Blind Swordsman's Eye" - A text-driven system for verifying UI layout
 * without relying on visual feedback. These assertions use bounding box math
 * to detect overlaps, overflow, and spatial relationships.
 *
 * Why: In vibe coding, we cannot visually verify UI. These assertions provide
 * objective, measurable proof of layout correctness.
 */

import { Locator, Page, expect } from '@playwright/test';

/**
 * Bounding box representation for spatial calculations.
 */
export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

/**
 * Result of a spatial assertion check.
 */
export interface SpatialCheckResult {
  passed: boolean;
  message: string;
  details?: Record<string, unknown>;
}

/**
 * Retrieves the bounding box of a locator.
 *
 * Why: Centralizes bounding box retrieval with proper error handling.
 */
export async function getBoundingBox(locator: Locator): Promise<BoundingBox> {
  const box = await locator.boundingBox();
  if (!box) {
    throw new Error(
      `Element not found or not visible: ${locator.toString()}`
    );
  }
  return box;
}

/**
 * Asserts that element A is positioned to the right of element B.
 *
 * Why: Verifies horizontal layout ordering without visual inspection.
 *
 * @param elementA - The element that should be on the right
 * @param elementB - The element that should be on the left
 * @param minGap - Optional minimum gap between elements (default: 0)
 */
export async function expectRightOf(
  elementA: Locator,
  elementB: Locator,
  minGap: number = 0
): Promise<void> {
  const boxA = await getBoundingBox(elementA);
  const boxB = await getBoundingBox(elementB);

  const bRightEdge = boxB.x + boxB.width;
  const gap = boxA.x - bRightEdge;

  expect(
    gap >= minGap,
    `Expected element A (x=${boxA.x}) to be at least ${minGap}px to the right of element B (right edge=${bRightEdge}). ` +
      `Actual gap: ${gap}px`
  ).toBe(true);
}

/**
 * Asserts that element A is positioned below element B.
 *
 * Why: Verifies vertical layout ordering without visual inspection.
 *
 * @param elementA - The element that should be below
 * @param elementB - The element that should be above
 * @param minGap - Optional minimum gap between elements (default: 0)
 */
export async function expectBelow(
  elementA: Locator,
  elementB: Locator,
  minGap: number = 0
): Promise<void> {
  const boxA = await getBoundingBox(elementA);
  const boxB = await getBoundingBox(elementB);

  const bBottomEdge = boxB.y + boxB.height;
  const gap = boxA.y - bBottomEdge;

  expect(
    gap >= minGap,
    `Expected element A (y=${boxA.y}) to be at least ${minGap}px below element B (bottom edge=${bBottomEdge}). ` +
      `Actual gap: ${gap}px`
  ).toBe(true);
}

/**
 * Checks if two bounding boxes overlap.
 *
 * Why: Core overlap detection algorithm using axis-aligned bounding box (AABB) intersection.
 */
function doBoxesOverlap(boxA: BoundingBox, boxB: BoundingBox): boolean {
  // Two rectangles do NOT overlap if one is completely to the left, right, above, or below the other
  const noOverlap =
    boxA.x + boxA.width <= boxB.x || // A is completely to the left of B
    boxB.x + boxB.width <= boxA.x || // B is completely to the left of A
    boxA.y + boxA.height <= boxB.y || // A is completely above B
    boxB.y + boxB.height <= boxA.y; // B is completely above A

  return !noOverlap;
}

/**
 * Calculates the overlap area between two bounding boxes.
 *
 * Why: Provides quantitative measure of overlap severity.
 */
function calculateOverlapArea(boxA: BoundingBox, boxB: BoundingBox): number {
  if (!doBoxesOverlap(boxA, boxB)) return 0;

  const overlapLeft = Math.max(boxA.x, boxB.x);
  const overlapRight = Math.min(boxA.x + boxA.width, boxB.x + boxB.width);
  const overlapTop = Math.max(boxA.y, boxB.y);
  const overlapBottom = Math.min(boxA.y + boxA.height, boxB.y + boxB.height);

  const overlapWidth = overlapRight - overlapLeft;
  const overlapHeight = overlapBottom - overlapTop;

  return overlapWidth * overlapHeight;
}

/**
 * Overlap detection result for a pair of elements.
 */
export interface OverlapResult {
  indexA: number;
  indexB: number;
  overlapArea: number;
  boxA: BoundingBox;
  boxB: BoundingBox;
}

/**
 * Asserts that none of the provided elements overlap with each other.
 *
 * Why: Critical for verifying that UI elements don't visually collide,
 * which is impossible to verify without visual inspection in vibe coding.
 *
 * @param elements - Array of locators to check for mutual overlap
 * @param tolerance - Pixel tolerance for overlap (default: 1px to account for sub-pixel rendering)
 */
export async function expectNoOverlap(
  elements: Locator[],
  tolerance: number = 1
): Promise<void> {
  const boxes: Array<{ index: number; box: BoundingBox; locator: Locator }> = [];

  // Collect all bounding boxes
  for (let i = 0; i < elements.length; i++) {
    try {
      const box = await getBoundingBox(elements[i]);
      boxes.push({ index: i, box, locator: elements[i] });
    } catch {
      // Element not visible, skip
      continue;
    }
  }

  const overlaps: OverlapResult[] = [];

  // Check all pairs for overlap
  for (let i = 0; i < boxes.length; i++) {
    for (let j = i + 1; j < boxes.length; j++) {
      const overlapArea = calculateOverlapArea(boxes[i].box, boxes[j].box);
      if (overlapArea > tolerance * tolerance) {
        overlaps.push({
          indexA: boxes[i].index,
          indexB: boxes[j].index,
          overlapArea,
          boxA: boxes[i].box,
          boxB: boxes[j].box,
        });
      }
    }
  }

  if (overlaps.length > 0) {
    const details = overlaps.map((o) => ({
      elements: `Element ${o.indexA} and Element ${o.indexB}`,
      overlapArea: `${o.overlapArea}px²`,
      boxA: `(${o.boxA.x}, ${o.boxA.y}) ${o.boxA.width}x${o.boxA.height}`,
      boxB: `(${o.boxB.x}, ${o.boxB.y}) ${o.boxB.width}x${o.boxB.height}`,
    }));

    expect(
      false,
      `Found ${overlaps.length} overlapping element pair(s):\n${JSON.stringify(details, null, 2)}`
    ).toBe(true);
  }
}

/**
 * Asserts that all elements are within the viewport boundaries.
 *
 * Why: Detects elements that overflow or are positioned off-screen,
 * which indicates layout bugs.
 *
 * @param page - The Playwright page
 * @param elements - Array of locators to check
 * @param padding - Optional padding from viewport edges (default: 0)
 */
export async function expectWithinViewport(
  page: Page,
  elements: Locator[],
  padding: number = 0
): Promise<void> {
  const viewport = page.viewportSize();
  if (!viewport) {
    throw new Error('Viewport size not available');
  }

  const outOfBounds: Array<{
    index: number;
    box: BoundingBox;
    violations: string[];
  }> = [];

  for (let i = 0; i < elements.length; i++) {
    try {
      const box = await getBoundingBox(elements[i]);
      const violations: string[] = [];

      if (box.x < padding) {
        violations.push(`left edge (${box.x}px) < padding (${padding}px)`);
      }
      if (box.y < padding) {
        violations.push(`top edge (${box.y}px) < padding (${padding}px)`);
      }
      if (box.x + box.width > viewport.width - padding) {
        violations.push(
          `right edge (${box.x + box.width}px) > viewport width - padding (${viewport.width - padding}px)`
        );
      }
      if (box.y + box.height > viewport.height - padding) {
        violations.push(
          `bottom edge (${box.y + box.height}px) > viewport height - padding (${viewport.height - padding}px)`
        );
      }

      if (violations.length > 0) {
        outOfBounds.push({ index: i, box, violations });
      }
    } catch {
      // Element not visible, skip
      continue;
    }
  }

  if (outOfBounds.length > 0) {
    const details = outOfBounds.map((o) => ({
      element: `Element ${o.index}`,
      box: `(${o.box.x}, ${o.box.y}) ${o.box.width}x${o.box.height}`,
      violations: o.violations,
    }));

    expect(
      false,
      `Found ${outOfBounds.length} element(s) outside viewport (${viewport.width}x${viewport.height}):\n${JSON.stringify(details, null, 2)}`
    ).toBe(true);
  }
}

/**
 * Asserts that an element is contained within a parent element.
 *
 * Why: Verifies that child elements don't overflow their containers.
 *
 * @param child - The child element
 * @param parent - The parent/container element
 * @param tolerance - Pixel tolerance (default: 1px)
 */
export async function expectContainedIn(
  child: Locator,
  parent: Locator,
  tolerance: number = 1
): Promise<void> {
  const childBox = await getBoundingBox(child);
  const parentBox = await getBoundingBox(parent);

  const violations: string[] = [];

  if (childBox.x < parentBox.x - tolerance) {
    violations.push(
      `left edge (${childBox.x}px) < parent left (${parentBox.x}px)`
    );
  }
  if (childBox.y < parentBox.y - tolerance) {
    violations.push(
      `top edge (${childBox.y}px) < parent top (${parentBox.y}px)`
    );
  }
  if (childBox.x + childBox.width > parentBox.x + parentBox.width + tolerance) {
    violations.push(
      `right edge (${childBox.x + childBox.width}px) > parent right (${parentBox.x + parentBox.width}px)`
    );
  }
  if (childBox.y + childBox.height > parentBox.y + parentBox.height + tolerance) {
    violations.push(
      `bottom edge (${childBox.y + childBox.height}px) > parent bottom (${parentBox.y + parentBox.height}px)`
    );
  }

  expect(
    violations.length === 0,
    `Child element overflows parent container:\n${violations.join('\n')}\n` +
      `Child: (${childBox.x}, ${childBox.y}) ${childBox.width}x${childBox.height}\n` +
      `Parent: (${parentBox.x}, ${parentBox.y}) ${parentBox.width}x${parentBox.height}`
  ).toBe(true);
}

/**
 * Collects all React Flow nodes and returns their locators.
 *
 * Why: Convenience helper for Weaver canvas node tests.
 *
 * @param page - The Playwright page
 */
export async function getWeaverNodes(page: Page): Promise<Locator[]> {
  const nodeSelector = '.react-flow__node';
  const count = await page.locator(nodeSelector).count();
  const nodes: Locator[] = [];

  for (let i = 0; i < count; i++) {
    nodes.push(page.locator(nodeSelector).nth(i));
  }

  return nodes;
}

/**
 * Gets the Weaver canvas container locator.
 *
 * Why: Convenience helper for canvas boundary tests.
 *
 * @param page - The Playwright page
 */
export function getWeaverCanvas(page: Page): Locator {
  return page.locator('[data-testid="weaver-canvas"], .react-flow');
}
