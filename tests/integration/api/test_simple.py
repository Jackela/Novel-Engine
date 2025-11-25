#!/usr/bin/env python3
"""
简化的API功能验证测试
"""

import json
import os
import sys
import time
from datetime import datetime

import requests


def check_env():
    """检查环境"""
    print("检查环境...")

    # 检查GEMINI_API_KEY
    if not os.getenv("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY not set")
        return False

    print("OK: GEMINI_API_KEY is set")
    return True


@pytest.mark.integration
def test_gemini_direct():
    """直接测试Gemini API"""
    import pytest

    pytest.skip("Integration script - use main() instead")

    print("测试Gemini API...")

    try:
        import google.generativeai as genai

        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content("Say 'API test OK'")

        if response and response.text:
            print(f"OK: {response.text.strip()}")
            return True
        else:
            print("ERROR: No response")
            return False
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False


@pytest.mark.integration
def test_api_server():
    """测试API服务器"""
    import pytest

    pytest.skip("Integration script - use main() instead")

    print("启动并测试API服务器...")

    import subprocess

    # 启动服务器
    server = subprocess.Popen(
        [sys.executable, "api_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        # 等待启动
        time.sleep(5)

        base_url = "http://127.0.0.1:8000"
        results = []

        # 测试health
        try:
            r = requests.get(f"{base_url}/health", timeout=10)
            if r.status_code == 200:
                print("OK: /health")
                results.append("health: PASS")
            else:
                print(f"ERROR: /health status {r.status_code}")
                results.append("health: FAIL")
        except Exception as e:
            print(f"ERROR: /health - {e}")
            results.append("health: ERROR")

        # 测试characters
        try:
            r = requests.get(f"{base_url}/characters", timeout=10)
            if r.status_code == 200:
                data = r.json()
                chars = len(data.get("characters", []))
                print(f"OK: /characters ({chars} found)")
                results.append(f"characters: PASS ({chars})")
            else:
                print(f"ERROR: /characters status {r.status_code}")
                results.append("characters: FAIL")
        except Exception as e:
            print(f"ERROR: /characters - {e}")
            results.append("characters: ERROR")

        return results

    finally:
        # 清理服务器
        server.terminate()
        server.wait()
        print("服务器已停止")


def main():
    """主函数"""
    print("=== API功能验证测试 ===")
    start_time = datetime.now()

    if not check_env():
        return False

    if not test_gemini_direct():
        return False

    results = test_api_server()

    # 保存结果
    report = {
        "timestamp": start_time.isoformat(),
        "gemini_api": "OK",
        "api_endpoints": results,
    }

    report_file = f"api_test_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"报告已保存: {report_file}")
    print("API功能验证完成")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
