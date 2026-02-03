import { test, expect } from './fixtures';

test.describe('Weaver Scene Generation', () => {
  test('@weaver-smoke generates scene from selected character with smart placement', async ({
    page,
  }) => {
    // ========================================
    // GIVEN: 用户在 Weaver 画布，且 API 已 mock
    // ========================================
    await test.step('GIVEN: API mock 配置为返回成功的场景数据', async () => {
      await page.addInitScript(() => {
        (window as any).__e2eSceneMode = 'success';
        (window as any).__e2eSceneDelayMs = 300;
      });
    });

    await test.step('GIVEN: 用户在 Weaver 画布页面', async () => {
      await page.goto('/weaver', { waitUntil: 'domcontentloaded' });
    });

    // ========================================
    // WHEN: 用户选中角色节点并生成场景
    // ========================================
    await test.step('WHEN: 用户选中 Alice 角色节点', async () => {
      // Click on the Alice character node to select it
      const aliceNode = page.locator('.weaver-node', { hasText: 'Alice' });
      await aliceNode.click();
      await expect(aliceNode).toHaveClass(/node-active/);
    });

    await test.step('WHEN: 用户点击 Generate Scene 按钮打开对话框', async () => {
      await page.getByRole('button', { name: 'Generate Scene' }).click();
      await expect(page.getByRole('heading', { name: 'Generate Scene' })).toBeVisible();
    });

    await test.step('WHEN: 用户选择 Scene Type 和 Tone', async () => {
      await page.getByLabel('Scene Type').click();
      await page.getByRole('option', { name: 'Opening' }).click();
      await page.getByLabel('Tone').click();
      await page.getByRole('option', { name: 'Mystical' }).click();
    });

    await test.step('WHEN: 用户点击对话框内的 Generate 按钮提交', async () => {
      await page
        .locator('[role="dialog"]')
        .getByRole('button', { name: /^Generate$/i })
        .click();
    });

    // ========================================
    // THEN: 场景节点出现并连接到角色节点
    // ========================================
    await test.step('THEN: 画布上出现一个 loading 状态的场景节点', async () => {
      const loadingNode = page.locator('.weaver-node.node-loading[data-node-type="scene"]');
      await expect(loadingNode).toHaveCount(1);
      await expect(loadingNode).toContainText('Generating...');
    });

    await test.step('THEN: 场景节点最终变为 idle 状态并显示场景信息', async () => {
      const resolvedNode = page.locator('.weaver-node.node-idle[data-node-type="scene"]', {
        hasText: 'The Shadows Whisper',
      });
      await expect(resolvedNode).toBeVisible({ timeout: 5000 });
      await expect(resolvedNode).toContainText('Nyx discovers a mysterious tome');
    });

    await test.step('THEN: 存在从角色到场景的连线', async () => {
      // Check that an edge exists connecting the character to the scene
      const edges = page.locator('.react-flow__edge');
      await expect(edges).not.toHaveCount(0);
    });
  });

  test('@weaver-smoke disables Generate Scene button when no character selected', async ({
    page,
  }) => {
    // ========================================
    // GIVEN: 用户在 Weaver 画布，无节点选中
    // ========================================
    await test.step('GIVEN: 用户在 Weaver 画布页面', async () => {
      await page.goto('/weaver', { waitUntil: 'domcontentloaded' });
    });

    await test.step('GIVEN: 点击画布空白处取消所有选择', async () => {
      // Click on empty canvas area to deselect all nodes
      await page.locator('.react-flow__pane').click({ position: { x: 10, y: 10 } });
    });

    // ========================================
    // THEN: Generate Scene 按钮禁用
    // ========================================
    await test.step('THEN: Generate Scene 按钮应该被禁用', async () => {
      const generateSceneButton = page.getByRole('button', { name: 'Generate Scene' });
      await expect(generateSceneButton).toBeDisabled();
    });
  });

  test('@weaver-smoke handles API error gracefully', async ({ page }) => {
    // ========================================
    // GIVEN: 用户在 Weaver 画布，且 API 会返回错误
    // ========================================
    await test.step('GIVEN: API mock 配置为返回 500 错误', async () => {
      await page.addInitScript(() => {
        (window as any).__e2eSceneMode = 'error';
        (window as any).__e2eSceneDelayMs = 100;
      });
    });

    await test.step('GIVEN: 用户在 Weaver 画布页面', async () => {
      await page.goto('/weaver', { waitUntil: 'domcontentloaded' });
    });

    // ========================================
    // WHEN: 用户选中角色并提交场景生成请求
    // ========================================
    await test.step('WHEN: 用户选中 Alice 角色节点', async () => {
      const aliceNode = page.locator('.weaver-node', { hasText: 'Alice' });
      await aliceNode.click();
      await expect(aliceNode).toHaveClass(/node-active/);
    });

    await test.step('WHEN: 用户打开生成对话框', async () => {
      await page.getByRole('button', { name: 'Generate Scene' }).click();
      await expect(page.getByRole('heading', { name: 'Generate Scene' })).toBeVisible();
    });

    await test.step('WHEN: 用户填写表单并提交', async () => {
      await page.getByLabel('Scene Type').click();
      await page.getByRole('option', { name: 'Opening' }).click();
      await page
        .locator('[role="dialog"]')
        .getByRole('button', { name: /^Generate$/i })
        .click();
    });

    // ========================================
    // THEN: 节点显示错误状态
    // ========================================
    await test.step('THEN: 画布上出现一个 error 状态的场景节点', async () => {
      const errorNode = page.locator('.weaver-node.node-error[data-node-type="scene"]');
      await expect(errorNode).toBeVisible({ timeout: 5000 });
    });

    await test.step('THEN: 画布保持稳定（其他节点仍存在）', async () => {
      // Verify the canvas is stable - character nodes should still be there
      const characterNodes = page.locator('.weaver-node[data-node-type="character"]');
      await expect(characterNodes).not.toHaveCount(0);
    });
  });
});
