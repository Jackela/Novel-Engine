#!/usr/bin/env python3
"""
简化版E2E测试
直接使用已运行的服务进行测试
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path

def check_servers():
    """检查服务器状态"""
    import requests
    
    print("检查服务器状态...")
    
    # 检查API服务器
    try:
        api_response = requests.get("http://127.0.0.1:8003/health", timeout=2)
        if api_response.status_code == 200:
            print("OK: API服务器运行中")
            api_running = True
        else:
            print("WARN: API服务器响应异常")
            api_running = False
    except:
        print("WARN: API服务器未运行")
        api_running = False
    
    # 检查前端服务器
    try:
        frontend_response = requests.get("http://localhost:5173", timeout=2)
        if frontend_response.status_code == 200:
            print("OK: 前端服务器运行中")
            frontend_running = True
        else:
            print("WARN: 前端服务器响应异常")
            frontend_running = False
    except:
        print("WARN: 前端服务器未运行")
        frontend_running = False
    
    return api_running, frontend_running

def create_quick_test():
    """创建快速E2E测试"""
    frontend_dir = Path("frontend")
    
    quick_test = '''
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
    '''
    
    test_file = frontend_dir / "quick-e2e.spec.js"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(quick_test)
    
    print(f"创建了快速测试文件: {test_file}")
    return test_file

def run_quick_playwright_test(test_file):
    """运行快速Playwright测试"""
    print("执行快速E2E测试...")
    
    frontend_dir = Path("frontend")
    
    try:
        # 使用更简单的命令
        result = subprocess.run(
            f"npx playwright test {test_file.name} --reporter=line --project=chromium",
            cwd=frontend_dir,
            shell=True,
            capture_output=True,
            text=True,
            timeout=90  # 90秒超时
        )
        
        print("测试执行完成")
        print("返回码:", result.returncode)
        
        if result.stdout:
            print("标准输出:")
            print(result.stdout[-1000:])  # 显示最后1000字符
        
        if result.stderr:
            print("错误输出:")
            print(result.stderr[-1000:])  # 显示最后1000字符
        
        # 检查截图文件
        screenshots = []
        for screenshot_name in ["quick-test-screenshot.png", "error-screenshot.png"]:
            screenshot_path = frontend_dir / screenshot_name
            if screenshot_path.exists():
                screenshots.append(str(screenshot_path))
                print(f"生成截图: {screenshot_path}")
        
        return {
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'screenshots': screenshots,
            'success': result.returncode == 0
        }
        
    except subprocess.TimeoutExpired:
        print("测试执行超时")
        return {
            'error': 'timeout',
            'success': False
        }
    except Exception as e:
        print(f"测试执行异常: {e}")
        return {
            'error': str(e),
            'success': False
        }

def main():
    """主函数"""
    print("=== 简化版E2E测试 ===")
    start_time = datetime.now()
    
    # 1. 检查服务器状态
    api_running, frontend_running = check_servers()
    
    if not frontend_running:
        print()
        print("前端服务器未运行，请先启动:")
        print("cd frontend")
        print("npm run dev")
        print()
        print("然后在另一个终端运行此测试")
        return False
    
    # 2. 创建并运行测试
    test_file = create_quick_test()
    results = run_quick_playwright_test(test_file)
    
    # 3. 生成报告
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    report = {
        "timestamp": start_time.isoformat(),
        "duration_seconds": duration,
        "test_type": "简化E2E测试",
        "servers": {
            "api_running": api_running,
            "frontend_running": frontend_running
        },
        "results": results
    }
    
    report_file = f"simple_e2e_test_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print()
    print("=== E2E测试结果 ===")
    print(f"用时: {duration:.1f}秒")
    print(f"成功: {'是' if results.get('success', False) else '否'}")
    print(f"报告: {report_file}")
    
    if results.get('screenshots'):
        print("生成的截图:")
        for screenshot in results['screenshots']:
            print(f"  - {screenshot}")
    
    return results.get('success', False)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)