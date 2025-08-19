
import { test, expect } from '@playwright/test';

test.describe('用户交互测试', () => {
  test('按钮和链接交互', async ({ page }) => {
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');
    
    // 查找并测试按钮
    const buttons = page.locator('button, [role="button"]');
    const buttonCount = await buttons.count();
    console.log('找到按钮数量:', buttonCount);
    
    if (buttonCount > 0) {
      // 点击第一个按钮
      await buttons.first().click();
      await page.waitForTimeout(1000);
      
      console.log('成功点击按钮');
    }
    
    // 截图记录交互后状态
    await page.screenshot({ 
      path: 'test-results/after-interaction.png', 
      fullPage: true 
    });
  });
  
  test('表单输入测试', async ({ page }) => {
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');
    
    // 查找输入框
    const inputs = page.locator('input, textarea');
    const inputCount = await inputs.count();
    console.log('找到输入框数量:', inputCount);
    
    if (inputCount > 0) {
      // 在第一个输入框中输入文本
      await inputs.first().fill('测试输入');
      await page.waitForTimeout(500);
      
      console.log('成功输入文本');
    }
  });
});
    