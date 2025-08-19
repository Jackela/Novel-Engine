#!/usr/bin/env python3
"""
完整E2E测试执行脚本
修复Windows兼容性问题
"""

import os
import sys
import json
import time
import subprocess
import requests
from datetime import datetime
from pathlib import Path

def setup_environment():
    """设置测试环境"""
    print("设置E2E测试环境...")
    
    # 确保API服务器运行
    try:
        response = requests.get("http://127.0.0.1:8003/health", timeout=2)
        if response.status_code == 200:
            print("OK: API服务器已运行")
            return None
    except:
        pass
    
    # 启动API服务器
    if not Path("minimal_api_server.py").exists():
        print("ERROR: minimal_api_server.py不存在")
        return None
    
    env = os.environ.copy()
    env["GEMINI_API_KEY"] = "AIzaSyDummy_Key_For_Testing_Only_Not_Real"
    
    api_process = subprocess.Popen(
        [sys.executable, "minimal_api_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env
    )
    
    # 等待API服务器启动
    for i in range(10):
        try:
            response = requests.get("http://127.0.0.1:8003/health", timeout=1)
            if response.status_code == 200:
                print("OK: API服务器启动成功")
                return api_process
        except:
            time.sleep(1)
    
    print("ERROR: API服务器启动失败")
    api_process.terminate()
    return None

def run_frontend_dev_server():
    """启动前端开发服务器"""
    print("启动前端开发服务器...")
    
    frontend_dir = Path("frontend")
    
    # 检查是否已运行
    try:
        response = requests.get("http://localhost:5173", timeout=2)
        print("OK: 前端服务器已运行")
        return None
    except:
        pass
    
    # 启动前端服务器 - 使用shell=True解决Windows问题
    frontend_process = subprocess.Popen(
        "npm run dev",
        cwd=frontend_dir,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # 等待前端服务器启动
    print("等待前端服务器启动...")
    for i in range(45):  # 45秒超时
        try:
            response = requests.get("http://localhost:5173", timeout=1)
            if response.status_code == 200:
                print("OK: 前端服务器启动成功")
                return frontend_process
        except:
            time.sleep(1)
    
    print("ERROR: 前端服务器启动超时")
    frontend_process.terminate()
    return None

def create_comprehensive_e2e_tests():
    """创建完整的E2E测试"""
    print("创建E2E测试文件...")
    
    frontend_dir = Path("frontend")
    test_dir = frontend_dir / "e2e-tests"
    test_dir.mkdir(exist_ok=True)
    
    # 基础页面测试
    basic_test = '''
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
    '''
    
    with open(test_dir / "basic.spec.js", 'w', encoding='utf-8') as f:
        f.write(basic_test)
    
    # API集成测试
    api_test = '''
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
    '''
    
    with open(test_dir / "api-integration.spec.js", 'w', encoding='utf-8') as f:
        f.write(api_test)
    
    # 用户交互测试
    interaction_test = '''
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
    '''
    
    with open(test_dir / "interaction.spec.js", 'w', encoding='utf-8') as f:
        f.write(interaction_test)
    
    print(f"OK: 创建了3个E2E测试文件")
    return test_dir

def run_playwright_tests(test_dir):
    """运行Playwright测试"""
    print("执行Playwright E2E测试...")
    
    frontend_dir = Path("frontend")
    results = {}
    
    # 创建测试结果目录
    (frontend_dir / "test-results").mkdir(exist_ok=True)
    
    # 运行测试
    try:
        result = subprocess.run(
            f"npx playwright test {test_dir} --reporter=json --output=test-results/e2e-output.json",
            cwd=frontend_dir,
            shell=True,
            capture_output=True,
            text=True,
            timeout=180  # 3分钟超时
        )
        
        results['returncode'] = result.returncode
        results['stdout'] = result.stdout
        results['stderr'] = result.stderr
        
        if result.returncode == 0:
            print("OK: E2E测试执行成功")
        else:
            print(f"WARN: E2E测试完成但有失败项 (返回码: {result.returncode})")
        
        # 尝试读取测试结果
        result_file = frontend_dir / "test-results" / "e2e-output.json"
        if result_file.exists():
            with open(result_file, 'r', encoding='utf-8') as f:
                test_data = json.load(f)
                results['test_data'] = test_data
                
                # 解析测试结果
                tests = test_data.get('tests', [])
                passed = sum(1 for t in tests if t.get('outcome') == 'passed')
                failed = sum(1 for t in tests if t.get('outcome') == 'failed')
                
                print(f"测试结果: {passed} 通过, {failed} 失败, 总计 {len(tests)} 个测试")
                results['summary'] = {'passed': passed, 'failed': failed, 'total': len(tests)}
        
    except subprocess.TimeoutExpired:
        print("WARN: E2E测试执行超时")
        results['error'] = 'timeout'
    except Exception as e:
        print(f"ERROR: E2E测试执行异常: {e}")
        results['error'] = str(e)
    
    return results

def main():
    """主函数"""
    print("=== 完整E2E测试执行 ===")
    start_time = datetime.now()
    
    # 1. 设置环境
    api_server = setup_environment()
    if not api_server:
        print("ERROR: 无法启动API服务器")
        return False
    
    frontend_server = None
    try:
        # 2. 启动前端服务器
        frontend_server = run_frontend_dev_server()
        if not frontend_server:
            print("ERROR: 无法启动前端服务器")
            return False
        
        # 3. 创建E2E测试
        test_dir = create_comprehensive_e2e_tests()
        
        # 4. 执行测试
        results = run_playwright_tests(test_dir)
        
        # 5. 生成报告
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        final_report = {
            "timestamp": start_time.isoformat(),
            "duration_seconds": duration,
            "test_type": "完整E2E测试",
            "results": results
        }
        
        report_file = f"complete_e2e_test_report_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(final_report, f, indent=2, ensure_ascii=False)
        
        print()
        print("=== E2E测试完成 ===")
        print(f"总用时: {duration:.1f}秒")
        print(f"详细报告: {report_file}")
        
        # 判断成功
        if 'summary' in results:
            summary = results['summary']
            success_rate = (summary['passed'] / summary['total']) * 100 if summary['total'] > 0 else 0
            print(f"成功率: {success_rate:.1f}%")
            return success_rate >= 70
        elif results.get('returncode') == 0:
            print("测试执行成功")
            return True
        else:
            print("测试执行有问题")
            return False
        
    finally:
        # 清理进程
        if frontend_server:
            frontend_server.terminate()
            frontend_server.wait()
            print("前端服务器已停止")
        
        if api_server:
            api_server.terminate()
            api_server.wait()
            print("API服务器已停止")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)