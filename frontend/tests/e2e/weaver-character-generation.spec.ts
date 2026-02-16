import { test, expect } from './fixtures';
import { safeGoto } from './utils/navigation';

test.describe('Weaver Character Generation', () => {
  test('@weaver-smoke dialog submit creates loading node then resolves to idle', async ({
    page,
  }) => {
    // ========================================
    // GIVEN: 用户在 Weaver 画布，且 API 已 mock
    // ========================================
    await test.step('GIVEN: API mock 配置为返回成功的角色数据', async () => {
      await page.addInitScript(() => {
        (window as any).__e2eGenerationMode = 'success';
        (window as any).__e2eGenerationDelayMs = 1000;
      });
    });

    await test.step('GIVEN: 用户在 Weaver 画布页面', async () => {
      await safeGoto(page, '/weaver');
      await expect(page.getByRole('heading', { name: 'Story Weaver' })).toBeVisible({
        timeout: 30_000,
      });
    });

    // ========================================
    // WHEN: 用户打开生成对话框并提交表单
    // ========================================
    await test.step('WHEN: 用户点击 Generate 按钮打开对话框', async () => {
      const generateButton = page.getByRole('button', { name: /^Generate$/i });
      await expect(generateButton).toBeVisible({ timeout: 20_000 });
      await generateButton.click();
      await expect(page.getByRole('heading', { name: 'Generate Character' })).toBeVisible();
    });

    await test.step('WHEN: 用户填写 Archetype 和选择 Tone', async () => {
      await page.getByLabel('Archetype').fill('Wanderer');
      await page.getByLabel('Tone').click();
      await page.getByRole('option', { name: 'Noir' }).click();
    });

    await test.step('WHEN: 用户点击对话框内的 Generate 按钮提交', async () => {
      await page
        .locator('[role="dialog"]')
        .getByRole('button', { name: /^Generate$/i })
        .click();
    });

    // ========================================
    // THEN: 节点经历 loading -> idle 状态转换
    // ========================================
    await test.step('THEN: 画布上出现一个 loading 状态的节点', async () => {
      const loadingNode = page.locator('.weaver-node.node-loading');
      await expect(loadingNode).toHaveCount(1, { timeout: 20_000 });
      await expect(loadingNode).toContainText('Generating...', { timeout: 20_000 });
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
      await page.addInitScript(() => {
        (window as any).__e2eGenerationMode = 'error';
        (window as any).__e2eGenerationDelayMs = 100;
      });
    });

    await test.step('GIVEN: 用户在 Weaver 画布页面', async () => {
      await safeGoto(page, '/weaver');
      await expect(page.getByRole('heading', { name: 'Story Weaver' })).toBeVisible({
        timeout: 30_000,
      });
    });

    // ========================================
    // WHEN: 用户提交角色生成请求
    // ========================================
    await test.step('WHEN: 用户打开生成对话框', async () => {
      const generateButton = page.getByRole('button', { name: /^Generate$/i });
      await expect(generateButton).toBeVisible({ timeout: 20_000 });
      await generateButton.click();
      await expect(page.getByRole('heading', { name: 'Generate Character' })).toBeVisible();
    });

    await test.step('WHEN: 用户填写表单并提交', async () => {
      await page.getByLabel('Archetype').fill('Mystic');
      await page.getByLabel('Tone').click();
      await page.getByRole('option', { name: 'Noir' }).click();
      await page
        .locator('[role="dialog"]')
        .getByRole('button', { name: /^Generate$/i })
        .click();
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
