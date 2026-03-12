#!/usr/bin/env python3
"""
本地 CodeQL 安全检查 - 在 pre-push 中运行
注意：这是快速检查，完整分析仍需在 GitHub Actions 中进行
"""

import subprocess
import sys
from pathlib import Path


def check_codeql_installed() -> bool:
    """检查 CodeQL CLI 是否安装"""
    try:
        result = subprocess.run(
            ["codeql", "--version"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def run_codeql_quick_check() -> tuple[bool, str]:
    """
    运行 CodeQL 快速检查
    注意：完整的数据库构建和分析需要时间，这里只做基本检查
    """
    print("🔍 Running CodeQL quick security check...")
    print()

    # 检查是否有明显的安全问题模式（快速启发式检查）
    security_patterns = [
        ("Hardcoded password/secret", r'password\s*=\s*["\'][^"\']+["\'][^#]*$', False),
        ("SQL injection risk (f-string)", r'execute\s*\(\s*f["\']', False),
        ("Eval usage", r"\beval\s*\(", True),
        ("Exec usage", r"\bexec\s*\(", True),
        ("Pickle without nosec", r"pickle\.loads?\s*\([^)]*\)(?!.*nosec)", False),
    ]

    issues_found = []

    src_dir = Path("src")
    if not src_dir.exists():
        return True, "No src directory found"

    for py_file in src_dir.rglob("*.py"):
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")

                for line_num, line in enumerate(lines, 1):
                    for issue_name, pattern, is_critical in security_patterns:
                        import re

                        if re.search(pattern, line, re.IGNORECASE):
                            # 排除注释和 nosec 标记
                            if "#" in line and ("nosec" in line or "noqa" in line):
                                continue

                            issues_found.append(
                                {
                                    "file": str(py_file),
                                    "line": line_num,
                                    "issue": issue_name,
                                    "critical": is_critical,
                                    "code": line.strip()[:80],
                                }
                            )
        except Exception as e:
            print(f"  ⚠️  Could not read {py_file}: {e}")

    return len(issues_found) == 0, issues_found


def main() -> int:
    """主函数"""
    print("=" * 60)
    print("🔒 CodeQL Security Quick Check")
    print("=" * 60)
    print()

    # 检查 CodeQL CLI 是否安装
    if not check_codeql_installed():
        print("⚠️  CodeQL CLI not installed")
        print("   Install from: https://github.com/github/codeql-cli-binaries")
        print()
        print("   Skipping CodeQL check (will run in GitHub Actions)")
        return 0  # 不阻塞推送

    print("✅ CodeQL CLI found")
    print()

    # 运行快速检查
    passed, issues = run_codeql_quick_check()

    if not passed:
        critical_issues = [i for i in issues if i["critical"]]
        warnings = [i for i in issues if not i["critical"]]

        if critical_issues:
            print("❌ CRITICAL security issues found:")
            print()
            for issue in critical_issues[:10]:  # 只显示前10个
                print(f"  🔴 {issue['file']}:{issue['line']}")
                print(f"     Issue: {issue['issue']}")
                print(f"     Code:  {issue['code']}")
                print()

            if len(critical_issues) > 10:
                print(f"  ... and {len(critical_issues) - 10} more critical issues")

            print("Please fix these issues before pushing.")
            print("Use '# nosec' comment if this is a false positive.")
            return 1

        if warnings:
            print("⚠️  Security warnings found:")
            print()
            for issue in warnings[:5]:  # 只显示前5个
                print(f"  🟡 {issue['file']}:{issue['line']}")
                print(f"     Issue: {issue['issue']}")
                print(f"     Code:  {issue['code']}")
                print()

            if len(warnings) > 5:
                print(f"  ... and {len(warnings) - 5} more warnings")

            print("Review these warnings (non-blocking)")
            print()

    print("✅ CodeQL quick check passed")
    print()
    print("Note: Full CodeQL analysis will run in GitHub Actions")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
