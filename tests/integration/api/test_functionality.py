#!/usr/bin/env python3
"""
API功能验证测试脚本
测试真实Gemini API调用功能
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import List

import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def check_dependencies():
    """检查依赖包"""
    print("检查依赖包...")
    deps = {
        "google.generativeai": "google-generativeai",
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "requests": "requests",
    }

    missing = []
    for module, package in deps.items():
        try:
            __import__(module)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - 缺失")
            missing.append(package)

    if missing:
        print(f"\n❌ 缺失依赖: {', '.join(missing)}")
        print("请运行: pip install " + " ".join(missing))
        return False

    return True


def check_environment():
    """检查环境变量"""
    print("\n🔍 检查环境变量...")

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("❌ GEMINI_API_KEY 未设置")
        print("请设置环境变量: export GEMINI_API_KEY=your_key_here")
        return False

    print(f"✅ GEMINI_API_KEY 已设置 (长度: {len(gemini_key)})")
    return True


def test_gemini_api_direct():
    """直接测试Gemini API调用"""
    import pytest

    pytest.skip("Integration script - use main() instead")

    print("\n🧪 直接测试Gemini API...")

    try:
        import google.generativeai as genai

        # 配置API
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

        # 创建模型
        model = genai.GenerativeModel("gemini-1.5-flash")

        # 测试简单生成
        response = model.generate_content(
            "Hello, please respond with 'API test successful'"
        )

        if response and response.text:
            print(f"✅ Gemini API 响应: {response.text.strip()}")
            return True
        else:
            print("❌ Gemini API 无响应")
            return False

    except Exception as e:
        print(f"❌ Gemini API 错误: {str(e)}")
        return False


def start_api_server():
    """启动API服务器"""
    print("\n🚀 启动API服务器...")

    try:
        import subprocess

        # 启动服务器进程
        process = subprocess.Popen(
            [sys.executable, "api_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # 等待服务器启动
        time.sleep(3)

        return process

    except Exception as e:
        print(f"❌ 启动服务器失败: {str(e)}")
        return None


def test_api_endpoints(base_url="http://127.0.0.1:8000"):
    """测试API端点"""
    import pytest

    pytest.skip("Integration script - use main() instead")

    print(f"\n🧪 测试API端点 ({base_url})...")

    test_results = []

    # 测试健康检查
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            print("✅ /health - 正常")
            test_results.append(("health", True, response.json()))
        else:
            print(f"❌ /health - 状态码: {response.status_code}")
            test_results.append(("health", False, response.text))
    except Exception as e:
        print(f"❌ /health - 错误: {str(e)}")
        test_results.append(("health", False, str(e)))

    # 测试根路径
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        if response.status_code == 200:
            print("✅ / - 正常")
            test_results.append(("root", True, response.json()))
        else:
            print(f"❌ / - 状态码: {response.status_code}")
            test_results.append(("root", False, response.text))
    except Exception as e:
        print(f"❌ / - 错误: {str(e)}")
        test_results.append(("root", False, str(e)))

    # 测试字符列表
    try:
        response = requests.get(f"{base_url}/characters", timeout=10)
        if response.status_code == 200:
            data = response.json()
            characters = data.get("characters", [])
            print(f"✅ /characters - 找到 {len(characters)} 个角色")
            test_results.append(("characters", True, data))
        else:
            print(f"❌ /characters - 状态码: {response.status_code}")
            test_results.append(("characters", False, response.text))
    except Exception as e:
        print(f"❌ /characters - 错误: {str(e)}")
        test_results.append(("characters", False, str(e)))

    # 测试模拟运行（如果有角色）
    characters_data = None
    for test_name, success, data in test_results:
        if test_name == "characters" and success:
            characters_data = data
            break

    if characters_data and characters_data.get("characters"):
        available_chars = characters_data["characters"]
        if len(available_chars) >= 2:
            test_chars = available_chars[:2]  # 取前两个角色
            try:
                simulation_request = {"character_names": test_chars, "turns": 1}
                response = requests.post(
                    f"{base_url}/simulations", json=simulation_request, timeout=30
                )
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ /simulations - 模拟完成，故事长度: {len(data.get('story', ''))}")
                    test_results.append(("simulations", True, data))
                else:
                    print(f"❌ /simulations - 状态码: {response.status_code}")
                    test_results.append(("simulations", False, response.text))
            except Exception as e:
                print(f"❌ /simulations - 错误: {str(e)}")
                test_results.append(("simulations", False, str(e)))
        else:
            print("⚠️ /simulations - 角色不足，跳过测试")
    else:
        print("⚠️ /simulations - 无可用角色，跳过测试")

    return test_results


def generate_test_report(test_results: List, start_time: datetime):
    """生成测试报告"""
    print("\n📊 生成测试报告...")

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    report = {
        "test_run": {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "test_type": "API功能验证",
        },
        "results": {},
    }

    successful_tests = 0
    total_tests = len(test_results)

    for test_name, success, data in test_results:
        report["results"][test_name] = {
            "success": success,
            "data": data if success else None,
            "error": data if not success else None,
        }
        if success:
            successful_tests += 1

    report["summary"] = {
        "total_tests": total_tests,
        "successful_tests": successful_tests,
        "failed_tests": total_tests - successful_tests,
        "success_rate": (
            f"{(successful_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
        ),
    }

    # 保存报告
    report_file = f"api_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"✅ 测试报告已保存: {report_file}")

    # 打印摘要
    print("\n📈 测试摘要:")
    print(f"   总测试数: {total_tests}")
    print(f"   成功测试: {successful_tests}")
    print(f"   失败测试: {total_tests - successful_tests}")
    print(f"   成功率: {report['summary']['success_rate']}")
    print(f"   用时: {duration:.2f}秒")

    return report


def main():
    """主测试流程"""
    print("开始API功能验证测试")
    start_time = datetime.now()

    # 检查依赖
    if not check_dependencies():
        return False

    # 检查环境
    if not check_environment():
        return False

    # 直接测试Gemini API
    if not test_gemini_api_direct():
        return False

    # 启动服务器
    server_process = start_api_server()
    if not server_process:
        return False

    try:
        # 等待服务器完全启动
        time.sleep(5)

        # 测试API端点
        test_results = test_api_endpoints()

        # 生成报告
        report = generate_test_report(test_results, start_time)

        # 判断整体是否成功
        success_rate = float(report["summary"]["success_rate"].rstrip("%"))
        if success_rate >= 80:
            print("\n🎉 API功能验证 - 通过")
            return True
        else:
            print("\n❌ API功能验证 - 失败")
            return False

    finally:
        # 清理服务器进程
        if server_process:
            server_process.terminate()
            server_process.wait()
            print("🧹 服务器进程已清理")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
