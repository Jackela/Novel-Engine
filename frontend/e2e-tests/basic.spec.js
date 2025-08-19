
import { test, expect } from '@playwright/test';

test.describe('基础功能测试', () => {
  test('页面加载和标题检查', async ({ page }) => {
    await page.goto('http://localhost:5173');
    
    // 等待页面加载
    await page.waitForLoadState('networkidle');
    
    // 检查页面标题
    const title = await page.title();
    expect(title).toBeTruthy();
    console.log('页面标题:', title);
    
    // 截图记录
    await page.screenshot({ 
      path: 'test-results/basic-page.png', 
      fullPage: true 
    });
  });
  
  test('页面内容检查', async ({ page }) => {
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');
    
    // 检查页面是否有内容
    const body = await page.locator('body');
    await expect(body).toBeVisible();
    
    // 检查是否有React根元素
    const root = await page.locator('#root, [data-reactroot]').count();
    expect(root).toBeGreaterThan(0);
    
    // 查找可能的按钮或交互元素
    const interactiveElements = await page.locator('button, [role="button"], input, a').count();
    console.log('交互元素数量:', interactiveElements);
  });
});
    