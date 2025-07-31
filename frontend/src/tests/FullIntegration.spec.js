// 完整的端到端集成测试
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';
const API_BASE_URL = 'http://localhost:8000';

test.describe('Full System Integration Tests', () => {
  
  test('should complete full user journey from home to character selection', async ({ page }) => {
    // 1. 访问主页
    await page.goto(BASE_URL);
    await expect(page.locator('h1')).toContainText('Warhammer 40k Multi-Agent Simulator');
    
    // 2. 检查后端连接状态
    await expect(page.locator('.status-success')).toBeVisible({ timeout: 15000 });
    
    // 3. 导航到角色选择页面
    await page.locator('a[href="/character-selection"]').click();
    await expect(page.locator('.character-selection-container')).toBeVisible();
    
    // 4. 等待角色加载
    await expect(page.locator('.character-card').first()).toBeVisible({ timeout: 15000 });
    
    // 5. 执行角色选择
    const firstCard = page.locator('.character-card').first();
    await firstCard.click();
    await expect(firstCard).toHaveClass(/selected/);
    
    // 6. 选择第二个角色以满足最小要求
    const secondCard = page.locator('.character-card').nth(1);
    await secondCard.click();
    await expect(secondCard).toHaveClass(/selected/);
    
    // 7. 验证确认按钮可用
    const confirmButton = page.locator('[data-testid="confirm-selection-button"]');
    await expect(confirmButton).toBeEnabled();
    
    // 8. 验证选择计数器
    await expect(page.locator('[data-testid="selection-counter"]')).toContainText('2 of 6');
    
    // 9. 测试确认功能
    await confirmButton.click();
    // 应该显示alert（简化版本）
    
    console.log('✅ Full integration test completed successfully');
  });

  test('should handle error recovery gracefully', async ({ page }) => {
    // Mock API error
    await page.route(`${API_BASE_URL}/characters`, async route => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal Server Error' })
      });
    });
    
    await page.goto(`${BASE_URL}/character-selection`);
    
    // 验证错误处理
    await expect(page.locator('[data-testid="error-container"]')).toBeVisible();
    await expect(page.locator('[data-testid="error-message"]')).toContainText('Server error');
    
    // 测试重试功能
    await expect(page.locator('[data-testid="retry-button"]')).toBeVisible();
    
    console.log('✅ Error recovery test completed successfully');
  });

  test('should maintain responsive design across viewports', async ({ page }) => {
    await page.goto(`${BASE_URL}/character-selection`);
    
    // Wait for initial load
    await expect(page.locator('[data-testid="loading-spinner"]')).not.toBeVisible({ timeout: 15000 });
    
    // 测试桌面视图
    await page.setViewportSize({ width: 1200, height: 800 });
    await expect(page.locator('[data-testid="character-grid"]')).toBeVisible({ timeout: 5000 });
    
    // 测试平板视图
    await page.setViewportSize({ width: 768, height: 1024 });
    await expect(page.locator('[data-testid="character-grid"]')).toBeVisible({ timeout: 5000 });
    
    // 测试移动视图
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.locator('[data-testid="character-grid"]')).toBeVisible({ timeout: 5000 });
    
    console.log('✅ Responsive design test completed successfully');
  });
});