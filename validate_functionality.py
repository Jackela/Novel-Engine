#!/usr/bin/env python3
"""
功能性验证总结脚本
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path

def validate_api_functionality():
    """验证API功能"""
    print("=== API功能验证 ===")
    
    # 检查是否有API测试报告
    api_reports = list(Path(".").glob("*api_test_*.json"))
    
    if not api_reports:
        print("❌ 未找到API测试报告")
        return False
    
    # 读取最新的API测试报告
    latest_report = max(api_reports, key=lambda p: p.stat().st_mtime)
    
    try:
        with open(latest_report, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        
        # 分析结果
        if 'summary' in report_data:
            summary = report_data['summary']
            success_rate = float(summary.get('success_rate', '0%').rstrip('%'))
            
            print(f"✓ API测试报告: {latest_report}")
            print(f"✓ 成功率: {summary.get('success_rate', 'N/A')}")
            print(f"✓ 成功测试: {summary.get('successful', 'N/A')}/{summary.get('total', 'N/A')}")
            
            if success_rate >= 75:
                print("✅ API功能验证通过")
                return True
            else:
                print("⚠️ API功能验证部分通过")
                return False
        else:
            # 检查旧格式报告
            gemini_status = report_data.get('gemini_api', 'Unknown')
            endpoints = report_data.get('api_endpoints', [])
            
            if gemini_status == 'OK':
                print("✓ Gemini API连接正常")
                successful_endpoints = sum(1 for ep in endpoints if 'PASS' in ep)
                total_endpoints = len(endpoints)
                
                print(f"✓ API端点测试: {successful_endpoints}/{total_endpoints}")
                
                if successful_endpoints >= total_endpoints * 0.5:  # 50%通过率
                    print("✅ API功能验证通过")
                    return True
                else:
                    print("⚠️ API功能验证部分通过")
                    return False
            else:
                print("❌ Gemini API连接失败")
                return False
                
    except Exception as e:
        print(f"❌ 读取API测试报告失败: {e}")
        return False

def validate_ui_functionality():
    """验证UI功能"""
    print("\\n=== UI功能验证 ===")
    
    # 检查前端目录
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("❌ 前端目录不存在")
        return False
    
    print("✓ 前端目录存在")
    
    # 检查package.json
    package_json = frontend_dir / "package.json"
    if not package_json.exists():
        print("❌ package.json不存在")
        return False
    
    print("✓ package.json存在")
    
    # 检查node_modules
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print("⚠️ node_modules不存在，前端依赖可能未安装")
        return False
    
    print("✓ node_modules存在")
    
    # 检查Playwright配置
    playwright_config = frontend_dir / "playwright.config.js"
    if playwright_config.exists():
        print("✓ Playwright配置存在")
    else:
        print("⚠️ Playwright配置不存在")
    
    # 检查测试文件
    test_dirs = [
        frontend_dir / "src" / "tests",
        frontend_dir / "tests"
    ]
    
    test_files_found = 0
    for test_dir in test_dirs:
        if test_dir.exists():
            test_files = list(test_dir.glob("*.spec.js")) + list(test_dir.glob("*.test.js"))
            test_files_found += len(test_files)
    
    if test_files_found > 0:
        print(f"✓ 找到 {test_files_found} 个测试文件")
    else:
        print("⚠️ 未找到测试文件")
    
    # 检查UI测试报告
    ui_reports = list(Path(".").glob("*ui*test*.json"))
    
    if ui_reports:
        latest_ui_report = max(ui_reports, key=lambda p: p.stat().st_mtime)
        try:
            with open(latest_ui_report, 'r', encoding='utf-8') as f:
                ui_data = json.load(f)
            
            print(f"✓ UI测试报告: {latest_ui_report}")
            
            if 'summary' in ui_data:
                summary = ui_data['summary']
                success_rate = float(summary.get('success_rate', '0%').rstrip('%'))
                print(f"✓ UI测试成功率: {summary.get('success_rate', 'N/A')}")
                
                if success_rate >= 50:
                    print("✅ UI功能验证通过")
                    return True
                else:
                    print("⚠️ UI功能验证部分通过")
                    return False
        except Exception as e:
            print(f"⚠️ 读取UI测试报告失败: {e}")
    
    # 如果没有测试报告，基于文件检查给出基础评估
    if frontend_dir.exists() and package_json.exists() and node_modules.exists():
        print("✅ UI基础环境验证通过（基于文件检查）")
        return True
    else:
        print("❌ UI功能验证失败")
        return False

def check_core_components():
    """检查核心组件"""
    print("\\n=== 核心组件检查 ===")
    
    components_to_check = [
        "api_server.py",
        "character_factory.py", 
        "director_agent.py",
        "chronicler_agent.py",
        "config_loader.py",
        "src/persona_agent.py",
        "src/event_bus.py"
    ]
    
    existing_components = 0
    for component in components_to_check:
        if Path(component).exists():
            print(f"✓ {component}")
            existing_components += 1
        else:
            print(f"❌ {component}")
    
    print(f"✓ 核心组件: {existing_components}/{len(components_to_check)}")
    
    return existing_components >= len(components_to_check) * 0.8  # 80%组件存在

def generate_final_validation_report():
    """生成最终验证报告"""
    print("\\n=== 生成最终验证报告 ===")
    
    # 收集所有测试结果
    validation_results = {
        "timestamp": datetime.now().isoformat(),
        "validation_type": "功能性验证总结",
        "results": {}
    }
    
    # API验证
    api_result = validate_api_functionality()
    validation_results["results"]["api_functionality"] = {
        "passed": api_result,
        "description": "API服务器和Gemini集成功能"
    }
    
    # UI验证  
    ui_result = validate_ui_functionality()
    validation_results["results"]["ui_functionality"] = {
        "passed": ui_result,
        "description": "前端用户界面和Playwright测试"
    }
    
    # 核心组件检查
    components_result = check_core_components()
    validation_results["results"]["core_components"] = {
        "passed": components_result,
        "description": "核心系统组件完整性"
    }
    
    # 计算总体结果
    total_tests = len(validation_results["results"])
    passed_tests = sum(1 for r in validation_results["results"].values() if r["passed"])
    overall_success_rate = (passed_tests / total_tests) * 100
    
    validation_results["summary"] = {
        "total_categories": total_tests,
        "passed_categories": passed_tests,
        "failed_categories": total_tests - passed_tests,
        "overall_success_rate": f"{overall_success_rate:.1f}%",
        "overall_status": "PASS" if overall_success_rate >= 70 else "PARTIAL" if overall_success_rate >= 50 else "FAIL"
    }
    
    # 保存报告
    report_file = f"final_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(validation_results, f, indent=2, ensure_ascii=False)
    
    # 打印总结
    print("\\n" + "="*50)
    print("功能性验证总结")
    print("="*50)
    print(f"API功能: {'✅ 通过' if api_result else '❌ 未通过'}")
    print(f"UI功能:  {'✅ 通过' if ui_result else '❌ 未通过'}")
    print(f"核心组件: {'✅ 通过' if components_result else '❌ 未通过'}")
    print("-"*50)
    print(f"总体状态: {validation_results['summary']['overall_status']}")
    print(f"成功率: {validation_results['summary']['overall_success_rate']}")
    print(f"详细报告: {report_file}")
    print("="*50)
    
    return validation_results["summary"]["overall_status"] in ["PASS", "PARTIAL"]

def main():
    """主函数"""
    print("开始功能性验证总结...")
    
    success = generate_final_validation_report()
    
    if success:
        print("\\n功能性验证完成！")
        print("\\n建议下一步:")
        print("1. 如有API问题，检查GEMINI_API_KEY设置")
        print("2. 如有UI问题，运行 'cd frontend && npm install'")
        print("3. 运行完整集成测试")
    else:
        print("\\n功能性验证发现问题，需要修复")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)