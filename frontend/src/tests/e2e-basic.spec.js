// 基础E2E测试
import { test, expect } from '@playwright/test';

test('基础页面加载测试', async ({ page }) => {
  console.log('开始E2E测试...');
  
  // 访问主页
  await page.goto('http://localhost:5173');
  
  // 等待页面加载
  await page.waitForLoadState('networkidle');
  
  // 获取页面标题
  const title = await page.title();
  console.log('页面标题:', title);
  
  // 检查页面内容
  const body = page.locator('body');
  await expect(body).toBeVisible();
  
  // 截图
  await page.screenshot({ path: 'e2e-test-result.png', fullPage: true });
  
  console.log('E2E测试完成');
});

test('UI元素交互测试', async ({ page }) => {
  await page.goto('http://localhost:5173');
  await page.waitForLoadState('networkidle');
  
  // 查找UI元素
  const buttons = await page.locator('button, [role="button"]').count();
  const links = await page.locator('a').count();
  const inputs = await page.locator('input').count();
  
  console.log(`UI元素统计 - 按钮: ${buttons}, 链接: ${links}, 输入框: ${inputs}`);
  
  // 尝试点击第一个按钮（如果存在）
  if (buttons > 0) {
    await page.locator('button').first().click();
    await page.waitForTimeout(1000);
    console.log('按钮点击测试完成');
  }
});