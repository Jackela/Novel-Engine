
import { test, expect } from '@playwright/test';

test.describe('API集成测试', () => {
  test('检查API连接状态', async ({ page }) => {
    // 拦截API请求
    const apiCalls = [];
    page.on('request', request => {
      if (request.url().includes('api') || request.url().includes('8003')) {
        apiCalls.push(request.url());
      }
    });
    
    await page.goto('http://localhost:5173');
    await page.waitForTimeout(5000); // 等待可能的API调用
    
    console.log('检测到的API调用:', apiCalls);
    
    // 截图记录当前状态
    await page.screenshot({ 
      path: 'test-results/api-integration.png', 
      fullPage: true 
    });
  });
  
  test('错误状态处理', async ({ page }) => {
    await page.goto('http://localhost:5173');
    
    // 查找错误信息显示
    const errorElements = await page.locator('.error, [class*="error"], [data-testid*="error"]').count();
    console.log('错误元素数量:', errorElements);
    
    // 查找加载状态
    const loadingElements = await page.locator('.loading, [class*="loading"], [data-testid*="loading"]').count();
    console.log('加载元素数量:', loadingElements);
  });
});
    