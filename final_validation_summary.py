#!/usr/bin/env python3
"""
最终功能性验证总结
"""

import os
import json
from datetime import datetime
from pathlib import Path

def main():
    """主函数"""
    print("=" * 60)
    print("功能性验证总结报告")
    print("=" * 60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # API功能验证结果
    print("1. API功能验证")
    print("-" * 30)
    
    api_reports = list(Path(".").glob("*api_test_*.json"))
    minimal_reports = list(Path(".").glob("minimal_api_test_*.json"))
    
    if minimal_reports:
        latest_report = max(minimal_reports, key=lambda p: p.stat().st_mtime)
        try:
            with open(latest_report, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            summary = data.get('summary', {})
            success_rate = summary.get('success_rate', '0%')
            successful = summary.get('successful', 0)
            total = summary.get('total', 0)
            
            print(f"测试报告: {latest_report.name}")
            print(f"成功率: {success_rate}")
            print(f"测试结果: {successful}/{total}")
            
            if success_rate == '100.0%':
                print("状态: PASS - API功能完全正常")
                api_status = "PASS"
            elif float(success_rate.rstrip('%')) >= 75:
                print("状态: PARTIAL - API功能基本正常")
                api_status = "PARTIAL"
            else:
                print("状态: FAIL - API功能存在问题")
                api_status = "FAIL"
                
        except Exception as e:
            print(f"报告读取错误: {e}")
            api_status = "UNKNOWN"
    else:
        print("未找到API测试报告")
        api_status = "MISSING"
    
    print()
    
    # UI功能验证结果
    print("2. UI功能验证")
    print("-" * 30)
    
    frontend_dir = Path("frontend")
    if frontend_dir.exists():
        print("前端目录: 存在")
        
        package_json = frontend_dir / "package.json"
        node_modules = frontend_dir / "node_modules"
        playwright_config = frontend_dir / "playwright.config.js"
        
        if package_json.exists():
            print("package.json: 存在")
        else:
            print("package.json: 不存在")
        
        if node_modules.exists():
            print("node_modules: 存在")
        else:
            print("node_modules: 不存在 (需要 npm install)")
        
        if playwright_config.exists():
            print("Playwright配置: 存在")
        else:
            print("Playwright配置: 不存在")
        
        # 检查UI测试报告
        ui_reports = list(Path(".").glob("*ui*test*.json"))
        if ui_reports:
            print(f"UI测试报告: 找到 {len(ui_reports)} 个")
            ui_status = "PARTIAL"
        else:
            print("UI测试报告: 未找到")
            ui_status = "PARTIAL" if (package_json.exists() and node_modules.exists()) else "FAIL"
    else:
        print("前端目录: 不存在")
        ui_status = "FAIL"
    
    print()
    
    # 核心组件检查
    print("3. 核心组件检查")
    print("-" * 30)
    
    components = [
        "api_server.py",
        "character_factory.py", 
        "director_agent.py",
        "chronicler_agent.py",
        "config_loader.py",
        "src/persona_agent.py",
        "src/event_bus.py"
    ]
    
    existing = 0
    for comp in components:
        if Path(comp).exists():
            print(f"{comp}: 存在")
            existing += 1
        else:
            print(f"{comp}: 不存在")
    
    components_status = "PASS" if existing >= len(components) * 0.8 else "PARTIAL" if existing >= len(components) * 0.5 else "FAIL"
    
    print()
    print("=" * 60)
    print("最终结果汇总")
    print("=" * 60)
    
    print(f"API功能:  {api_status}")
    print(f"UI功能:   {ui_status}")
    print(f"核心组件: {components_status}")
    print(f"组件完整性: {existing}/{len(components)} ({existing/len(components)*100:.1f}%)")
    
    # 计算整体状态
    status_scores = {"PASS": 3, "PARTIAL": 2, "FAIL": 1, "MISSING": 0, "UNKNOWN": 1}
    total_score = status_scores.get(api_status, 0) + status_scores.get(ui_status, 0) + status_scores.get(components_status, 0)
    max_score = 9  # 3 categories * 3 points each
    
    overall_percentage = (total_score / max_score) * 100
    
    if overall_percentage >= 80:
        overall_status = "EXCELLENT"
    elif overall_percentage >= 65:
        overall_status = "GOOD"
    elif overall_percentage >= 50:
        overall_status = "ACCEPTABLE"
    else:
        overall_status = "NEEDS_WORK"
    
    print("-" * 60)
    print(f"整体评估: {overall_status} ({overall_percentage:.1f}%)")
    print("=" * 60)
    
    # 建议
    print("建议和修复指南:")
    print()
    
    if api_status in ["FAIL", "MISSING"]:
        print("API问题修复:")
        print("- 确保设置了有效的 GEMINI_API_KEY 环境变量")
        print("- 运行: python test_fixed_api.py")
    
    if ui_status == "FAIL":
        print("UI问题修复:")
        print("- cd frontend")
        print("- npm install")
        print("- npm run dev")
    
    if components_status != "PASS":
        print("组件问题:")
        print("- 检查缺失的组件文件")
        print("- 确保项目结构完整")
    
    # 保存最终报告
    final_report = {
        "timestamp": datetime.now().isoformat(),
        "validation_summary": {
            "api_status": api_status,
            "ui_status": ui_status,
            "components_status": components_status,
            "overall_status": overall_status,
            "overall_percentage": overall_percentage,
            "components_count": f"{existing}/{len(components)}"
        }
    }
    
    report_file = f"final_validation_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(final_report, f, indent=2, ensure_ascii=False)
    
    print()
    print(f"详细报告已保存: {report_file}")
    print("=" * 60)

if __name__ == "__main__":
    main()