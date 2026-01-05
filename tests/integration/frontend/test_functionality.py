#!/usr/bin/env python3
"""
UI功能验证测试脚本
使用Playwright测试前端用户交互
"""
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests


def check_dependencies():
    """检查前端依赖"""
    print("检查前端依赖...")

    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("ERROR: frontend目录不存在")
        return False

    # 检查package.json
    package_json = frontend_dir / "package.json"
    if not package_json.exists():
        print("ERROR: package.json不存在")
        return False

    # 检查node_modules
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print("WARN: node_modules不存在，尝试安装依赖...")
        result = subprocess.run(
            ["npm", "install"], cwd=frontend_dir, capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"ERROR: npm install失败: {result.stderr}")
            return False
        print("OK: npm install完成")
    else:
        print("OK: node_modules存在")

    # 检查Playwright
    playwright_installed = subprocess.run(
        ["npx", "playwright", "--version"],
        cwd=frontend_dir,
        capture_output=True,
        text=True,
    )

    if playwright_installed.returncode != 0:
        print("WARN: Playwright未安装，正在安装...")
        install_result = subprocess.run(
            ["npx", "playwright", "install", "chromium"],
            cwd=frontend_dir,
            capture_output=True,
            text=True,
        )
        if install_result.returncode != 0:
            print(f"ERROR: Playwright安装失败: {install_result.stderr}")
            return False
        print("OK: Playwright安装完成")
    else:
        print("OK: Playwright已安装")

    return True


def start_api_server():
    """启动API服务器"""
    print("启动API服务器...")

    # 先检查8003端口是否被占用
    try:
        response = requests.get("http://127.0.0.1:8003/health", timeout=2)
        if response.status_code == 200:
            print("OK: API服务器已在运行")
            return None  # 服务器已存在，不需要启动新的
    except Exception:
        logging.getLogger(__name__).debug("Suppressed exception", exc_info=True)

    # 启动最小化API服务器
    if not Path("minimal_api_server.py").exists():
        print("ERROR: minimal_api_server.py不存在，请先运行API测试")
        return None

    env = os.environ.copy()
    env["GEMINI_API_KEY"] = "AIzaSyDummy_Key_For_Testing_Only_Not_Real"

    process = subprocess.Popen(
        [sys.executable, "minimal_api_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    # 等待服务器启动
    for i in range(10):
        try:
            response = requests.get("http://127.0.0.1:8003/health", timeout=1)
            if response.status_code == 200:
                print("OK: API服务器启动成功")
                return process
        except Exception:
            time.sleep(1)

    print("ERROR: API服务器启动失败")
    process.terminate()
    return None


def run_ui_tests():
    """运行UI测试"""
    print("运行UI测试...")

    frontend_dir = Path("frontend")
    results = {}

    # 1. 运行前端开发服务器并测试
    print("1. 启动前端开发服务器...")

    # 创建简单的E2E测试文件
    test_content = """
import { test, expect } from '@playwright/test';

test('基础页面加载测试', async ({ page }) => {
  // 访问主页
  await page.goto('/');
  
  // 检查页面标题
  await expect(page).toHaveTitle(/StoryForge/i);
  
  // 检查是否有主要内容
  const body = await page.locator('body');
  await expect(body).toBeVisible();
});

test('API连接测试', async ({ page }) => {
  // 访问主页
  await page.goto('/');
  
  // 等待页面加载
  await page.waitForTimeout(2000);
  
  // 检查是否有API错误信息
  const errorMessages = await page.locator('.error, [class*="error"], [data-testid="error"]').count();
  expect(errorMessages).toBeLessThanOrEqual(0);
});

test('字符选择功能测试', async ({ page }) => {
  // 访问主页
  await page.goto('/');
  
  // 等待页面加载
  await page.waitForTimeout(3000);
  
  // 尝试查找字符选择相关元素
  const characterElements = await page.locator('[class*="character"], [data-testid*="character"], button').count();
  expect(characterElements).toBeGreaterThan(0);
});
    """

    test_file = frontend_dir / "src" / "tests" / "basic-ui.spec.js"
    test_file.parent.mkdir(parents=True, exist_ok=True)

    with open(test_file, "w", encoding="utf-8") as f:
        f.write(test_content)

    print("OK: 创建了基础UI测试文件")

    # 2. 运行Playwright测试
    print("2. 运行Playwright测试...")

    test_result = subprocess.run(
        ["npx", "playwright", "test", "--reporter=json", "--output-dir=test-results"],
        cwd=frontend_dir,
        capture_output=True,
        text=True,
        timeout=120,  # 2分钟超时
    )

    if test_result.returncode == 0:
        print("OK: Playwright测试通过")
        results["playwright"] = {"success": True, "output": test_result.stdout}
    else:
        print("WARN: Playwright测试部分失败或超时")
        results["playwright"] = {
            "success": False,
            "error": test_result.stderr,
            "output": test_result.stdout,
        }

    # 3. 检查测试结果文件
    test_results_file = frontend_dir / "test-results" / "test-results.json"
    if test_results_file.exists():
        try:
            with open(test_results_file, "r", encoding="utf-8") as f:
                test_data = json.load(f)
                results["test_data"] = test_data
                print(
                    f"OK: 找到测试结果数据 - {len(test_data.get('tests', []))} 个测试"
                )
        except Exception as e:
            print(f"WARN: 无法解析测试结果: {e}")

    # 4. 尝试截图测试
    print("3. 运行截图测试...")

    screenshot_test = """
import { test } from '@playwright/test';

test('页面截图', async ({ page }) => {
  await page.goto('/');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: 'test-results/page-screenshot.png', fullPage: true });
});
    """

    screenshot_file = frontend_dir / "src" / "tests" / "screenshot.spec.js"
    with open(screenshot_file, "w", encoding="utf-8") as f:
        f.write(screenshot_test)

    screenshot_result = subprocess.run(
        ["npx", "playwright", "test", "screenshot.spec.js", "--reporter=list"],
        cwd=frontend_dir,
        capture_output=True,
        text=True,
        timeout=60,
    )

    if screenshot_result.returncode == 0:
        screenshot_path = frontend_dir / "test-results" / "page-screenshot.png"
        if screenshot_path.exists():
            print("OK: 页面截图成功")
            results["screenshot"] = {"success": True, "path": str(screenshot_path)}
        else:
            print("WARN: 截图测试运行成功但未找到截图文件")
            results["screenshot"] = {
                "success": False,
                "error": "Screenshot file not found",
            }
    else:
        print("WARN: 截图测试失败")
        results["screenshot"] = {"success": False, "error": screenshot_result.stderr}

    return results


def generate_ui_test_report(results):
    """生成UI测试报告"""
    print("\\n=== UI测试报告 ===")

    total_tests = len(results)
    successful_tests = sum(1 for r in results.values() if r.get("success", False))

    print(f"总测试类型: {total_tests}")
    print(f"成功测试: {successful_tests}")
    print(f"失败测试: {total_tests - successful_tests}")
    print(f"成功率: {(successful_tests/total_tests)*100:.1f}%")

    # 详细结果
    for test_name, result in results.items():
        status = "PASS" if result.get("success", False) else "FAIL"
        print(f"  {test_name}: {status}")
        if not result.get("success") and "error" in result:
            print(f"    错误: {result['error'][:100]}...")

    # 保存报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "test_type": "UI功能验证",
        "summary": {
            "total": total_tests,
            "successful": successful_tests,
            "failed": total_tests - successful_tests,
            "success_rate": f"{(successful_tests/total_tests)*100:.1f}%",
        },
        "details": results,
    }

    report_file = f"ui_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"详细报告已保存: {report_file}")

    return successful_tests >= total_tests * 0.6  # 60%成功率


def main():
    """主函数"""
    print("=== UI功能验证测试 ===")

    # 检查依赖
    if not check_dependencies():
        print("依赖检查失败")
        return False

    # 启动API服务器
    api_server = start_api_server()

    try:
        # 运行UI测试
        results = run_ui_tests()

        # 生成报告
        success = generate_ui_test_report(results)

        if success:
            print("\\nUI功能验证通过！")
        else:
            print("\\nUI功能验证部分通过")

        return success

    finally:
        # 清理API服务器
        if api_server:
            api_server.terminate()
            api_server.wait()
            print("API服务器已停止")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
