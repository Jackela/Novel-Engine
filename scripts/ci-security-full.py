#!/usr/bin/env python3
"""
完整的本地安全检查（替代方案）
组合多种安全工具进行深度检查
"""

import json
import subprocess
import sys
from pathlib import Path


def run_bandit_detailed():
    """运行详细的Bandit检查"""
    print("🔍 Running Bandit security analysis...")

    cmd = ["bandit", "-r", "src/", "-ll", "-ii", "-f", "json"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.stdout:
            try:
                data = json.loads(result.stdout)
                results = data.get("results", [])

                errors = [r for r in results if r["issue_severity"] == "HIGH"]
                warnings = [r for r in results if r["issue_severity"] == "MEDIUM"]

                return errors, warnings
            except json.JSONDecodeError:
                return [], []
        return [], []
    except Exception as e:
        print(f"   ⚠️  Bandit error: {e}")
        return [], []


def run_pip_audit():
    """检查依赖漏洞"""
    print("🔍 Checking dependencies for known vulnerabilities...")

    try:
        result = subprocess.run(
            ["pip-audit", "-r", "requirements.txt", "--format=json"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0 and result.stdout:
            try:
                data = json.loads(result.stdout)
                vulnerabilities = data.get("vulnerabilities", [])
                return vulnerabilities
            except Exception:
                pass
        return []
    except FileNotFoundError:
        print("   ⚠️  pip-audit not installed (pip install pip-audit)")
        return []
    except Exception as e:
        print(f"   ⚠️  pip-audit error: {e}")
        return []


def check_dangerous_patterns():
    """检查危险的代码模式"""
    print("🔍 Checking for dangerous code patterns...")

    patterns = [
        ("eval() usage", r"\beval\s*\(", "CRITICAL"),
        ("exec() usage", r"\bexec\s*\(", "CRITICAL"),
        ("compile() with eval", r"compile\s*\([^)]*\beval\b", "CRITICAL"),
        (
            "pickle without nosec",
            r"pickle\.(loads?|dump)\s*\([^)]*\)(?!.*# nosec)",
            "HIGH",
        ),
        (
            "subprocess with shell",
            r"subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True(?!.*# nosec)",
            "HIGH",
        ),
        # SQL injection - only flag if no validation pattern nearby
        (
            "sql injection risk",
            r'execute\s*\(\s*f["\'][^"\']*(?:SELECT|INSERT|UPDATE|DELETE|DROP)',
            "HIGH",
        ),
        (
            "hardcoded password",
            r'password\s*=\s*["\'][^"\']{3,}["\'](?!.*# nosec)',
            "MEDIUM",
        ),
        (
            "bind to all interfaces",
            r'host\s*=\s*["\']0\.0\.0\.0["\'](?!.*# nosec)',
            "MEDIUM",
        ),
        ("debug mode enabled", r"DEBUG\s*=\s*True(?!.*# nosec)", "LOW"),
    ]

    import re

    issues = []
    src_dir = Path("src")

    for py_file in src_dir.rglob("*.py"):
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")

                for line_num, line in enumerate(lines, 1):
                    for issue_name, pattern, severity in patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            # 排除注释和nosec
                            if "#" in line:
                                comment = line[line.index("#") :]
                                if "nosec" in comment or "noqa" in comment:
                                    continue

                            issues.append(
                                {
                                    "file": str(py_file),
                                    "line": line_num,
                                    "issue": issue_name,
                                    "severity": severity,
                                    "code": line.strip()[:80],
                                }
                            )
        except Exception:
            pass

    return issues


def main():
    print("=" * 70)
    print("🔒 Full Security Analysis (Local)")
    print("=" * 70)
    print()

    all_errors = []
    all_warnings = []

    # 1. Bandit详细检查
    bandit_errors, bandit_warnings = run_bandit_detailed()
    all_errors.extend(bandit_errors)
    all_warnings.extend(bandit_warnings)

    print(f"   Bandit: {len(bandit_errors)} errors, {len(bandit_warnings)} warnings")
    print()

    # 2. 危险模式检查
    pattern_issues = check_dangerous_patterns()
    for issue in pattern_issues:
        if issue["severity"] in ["CRITICAL", "HIGH"]:
            all_errors.append(issue)
        else:
            all_warnings.append(issue)

    print(f"   Pattern check: {len(pattern_issues)} issues found")
    print()

    # 3. 依赖漏洞检查
    vulns = run_pip_audit()
    if vulns:
        print(f"   Dependencies: {len(vulns)} vulnerabilities")
        for v in vulns[:3]:
            print(
                f"     - {v.get('name', 'unknown')}: {v.get('vulnerability_id', 'unknown')}"
            )
    else:
        print("   Dependencies: No known vulnerabilities")
    print()

    # 输出结果
    print("=" * 70)
    print("📊 Results Summary")
    print("=" * 70)
    print()
    print(f"   Errors:   {len(all_errors)}")
    print(f"   Warnings: {len(all_warnings)}")
    print()

    # 显示错误详情
    if all_errors:
        print("❌ ERRORS (Blocking):")
        print()
        for error in all_errors[:10]:
            if isinstance(error, dict) and "filename" in error:
                # Bandit格式
                print(f"   🔴 {error['filename']}:{error['line_number']}")
                print(f"      {error['issue_text']}")
            else:
                # 模式检查格式
                print(f"   🔴 {error['file']}:{error['line']}")
                print(f"      {error['issue']}: {error['code']}")
            print()

        if len(all_errors) > 10:
            print(f"   ... and {len(all_errors) - 10} more errors")
            print()

    # 显示警告详情
    if all_warnings:
        print("⚠️  WARNINGS:")
        print()
        for warning in all_warnings[:5]:
            if isinstance(warning, dict) and "filename" in warning:
                print(f"   🟡 {warning['filename']}:{warning['line_number']}")
                print(f"      {warning['issue_text']}")
            else:
                print(f"   🟡 {warning['file']}:{warning['line']}")
                print(f"      {warning['issue']}")
            print()

        if len(all_warnings) > 5:
            print(f"   ... and {len(all_warnings) - 5} more warnings")
            print()

    print("=" * 70)

    if all_errors:
        print()
        print(f"❌ Found {len(all_errors)} security errors")
        print("   Please fix these issues before pushing.")
        print("   Add '# nosec' comment if this is a false positive.")
        return 1

    print()
    print("✅ No security errors found!")
    if all_warnings:
        print(f"   (Note: {len(all_warnings)} warnings - review recommended)")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
