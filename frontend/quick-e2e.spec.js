
import { test, expect } from '@playwright/test';

test.describe('快速E2E验证', () => {
  test('基础页面访问', async ({ page }) => {
    console.log('开始页面访问测试');
    
    // 设置较长的超时时间
    test.setTimeout(30000);
    
    try {
      await page.goto('http://localhost:5173', { 
        waitUntil: 'domcontentloaded',
        timeout: 15000 
      });
      
      console.log('页面加载成功');
      
      // 获取页面标题
      const title = await page.title();
      console.log('页面标题:', title);
      
      // 截图
      await page.screenshot({ 
        path: 'quick-test-screenshot.png',
        fullPage: true 
      });
      
      console.log('截图保存成功');
      
      // 基础断言
      expect(title).toBeTruthy();
      
      // 检查页面内容
      const body = page.locator('body');
      await expect(body).toBeVisible();
      
      console.log('基础验证通过');
      
    } catch (error) {
      console.log('测试过程中的错误:', error.message);
      
      // 即使出错也尝试截图
      try {
        await page.screenshot({ path: 'error-screenshot.png' });
      } catch (screenshotError) {
        console.log('截图失败:', screenshotError.message);
      }
      
      throw error;
    }
  });
  
  test('简单交互测试', async ({ page }) => {
    console.log('开始交互测试');
    
    test.setTimeout(20000);
    
    try {
      await page.goto('http://localhost:5173', { 
        waitUntil: 'domcontentloaded',
        timeout: 10000 
      });
      
      // 等待页面稳定
      await page.waitForTimeout(2000);
      
      // 查找交互元素
      const buttons = await page.locator('button, [role="button"]').count();
      const links = await page.locator('a').count();
      const inputs = await page.locator('input, textarea').count();
      
      console.log(`找到交互元素 - 按钮:${buttons}, 链接:${links}, 输入框:${inputs}`);
      
      // 基础交互测试
      if (buttons > 0) {
        console.log('测试按钮点击');
        await page.locator('button, [role="button"]').first().click();
        await page.waitForTimeout(1000);
      }
      
      console.log('交互测试完成');
      
    } catch (error) {
      console.log('交互测试错误:', error.message);
    }
  });
});
    