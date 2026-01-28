import { test, expect } from './fixtures';

test.describe('Weaver Character Generation', () => {
  test('@weaver-smoke dialog submit creates loading node then resolves to idle', async ({
    page,
  }) => {
    // ========================================
    // GIVEN: 用户在 Weaver 画布，且 API 已 mock
    // ========================================
    await test.step('GIVEN: API mock 配置为返回成功的角色数据', async () => {
      await page.route('**/api/generation/character', async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 200));
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            name: 'Zenith Arc',
            tagline: 'A spark that bends the grid.',
            bio: 'Zenith navigates lost circuits with quiet precision.',
            visual_prompt: 'neon silhouette, cyan glow, circuit motifs',
            traits: ['curious', 'steady'],
          }),
        });
      });
    });

    await test.step('GIVEN: 用户在 Weaver 画布页面', async () => {
      await page.goto('/weaver', { waitUntil: 'domcontentloaded' });
    });

    // ========================================
    // WHEN: 用户打开生成对话框并提交表单
    // ========================================
    await test.step('WHEN: 用户点击 Generate 按钮打开对话框', async () => {
      await page.getByRole('button', { name: 'Generate' }).click();
      await expect(page.getByRole('heading', { name: 'Generate Character' })).toBeVisible();
    });

    await test.step('WHEN: 用户填写 Archetype 和选择 Tone', async () => {
      await page.getByLabel('Archetype').fill('Wanderer');
      await page.getByLabel('Tone').click();
      await page.getByRole('option', { name: 'Noir' }).click();
    });

    await test.step('WHEN: 用户点击对话框内的 Generate 按钮提交', async () => {
      await page.getByRole('button', { name: 'Generate' }).click();
    });

    // ========================================
    // THEN: 节点经历 loading -> idle 状态转换
    // ========================================
    await test.step('THEN: 画布上出现一个 loading 状态的节点', async () => {
      const loadingNode = page.locator('.weaver-node.node-loading');
      await expect(loadingNode).toHaveCount(1);
      await expect(loadingNode).toContainText('Generating...');
    });

    await test.step('THEN: 节点最终变为 idle 状态并显示角色信息', async () => {
      const resolvedNode = page.locator('.weaver-node.node-idle', {
        hasText: 'Zenith Arc',
      });
      await expect(resolvedNode).toBeVisible();
      await expect(resolvedNode).toContainText('A spark that bends the grid.');
    });
  });

  test('@weaver-smoke generation error displays error state on node', async ({ page }) => {
    // ========================================
    // GIVEN: 用户在 Weaver 画布，且 API 会返回错误
    // ========================================
    await test.step('GIVEN: API mock 配置为返回 500 错误', async () => {
      await page.route('**/api/generation/character', async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 100));
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'LLM service unavailable' }),
        });
      });
    });

    await test.step('GIVEN: 用户在 Weaver 画布页面', async () => {
      await page.goto('/weaver', { waitUntil: 'domcontentloaded' });
    });

    // ========================================
    // WHEN: 用户提交角色生成请求
    // ========================================
    await test.step('WHEN: 用户打开生成对话框', async () => {
      await page.getByRole('button', { name: 'Generate' }).click();
      await expect(page.getByRole('heading', { name: 'Generate Character' })).toBeVisible();
    });

    await test.step('WHEN: 用户填写表单并提交', async () => {
      await page.getByLabel('Archetype').fill('Mystic');
      await page.getByLabel('Tone').click();
      await page.getByRole('option', { name: 'Noir' }).click();
      await page.getByRole('button', { name: 'Generate' }).click();
    });

    // ========================================
    // THEN: 节点显示错误状态
    // ========================================
    await test.step('THEN: 画布上出现一个 error 状态的节点', async () => {
      const errorNode = page.locator('.weaver-node.node-error');
      await expect(errorNode).toBeVisible({ timeout: 5000 });
    });
  });
});
