#!/usr/bin/env python3
"""
完整的本地 CodeQL 安全检查
创建数据库并运行完整的安全分析（类似GitHub Actions）"""

import json
import os
import shutil
import subprocess
import sys
import tempfile


def run_command(cmd, cwd=None, timeout=300):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"


def check_codeql_installed() -> bool:
    """检查 CodeQL CLI 是否安装"""
    try:
        result = subprocess.run(
            ["codeql", "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print(f"✅ CodeQL CLI: {result.stdout.strip()}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return False


def create_codeql_database(db_path: str) -> bool:
    """创建CodeQL数据库"""
    print(f"\n📦 Creating CodeQL database at {db_path}...")
    print("   This may take a few minutes...")

    cmd = [
        "codeql",
        "database",
        "create",
        db_path,
        "--language=python",
        "--source-root=.",
        "--no-run-unnecessary-builds",
    ]

    returncode, stdout, stderr = run_command(cmd, timeout=600)

    if returncode != 0:
        print("❌ Database creation failed:")
        print(f"   {stderr}")
        return False

    print("✅ Database created successfully")
    return True


def analyze_database(db_path: str, output_file: str) -> tuple[bool, list]:
    """分析数据库并返回结果"""
    print("\n🔍 Analyzing database with security queries...")
    print("   Running: security-extended, security-and-quality")

    # 使用标准安全查询包
    cmd = [
        "codeql",
        "database",
        "analyze",
        db_path,
        "--format=sarifv2.1.0",
        f"--output={output_file}",
        "--sarif-add-snippets",
        "codeql/python-queries:codeql-suites/python-security-extended.qls",
        "--threads=4",
    ]

    returncode, stdout, stderr = run_command(cmd, timeout=600)

    if returncode != 0:
        print("❌ Analysis failed:")
        print(f"   {stderr}")
        return False, []

    # 解析SARIF结果
    alerts = parse_sarif(output_file)
    return True, alerts


def parse_sarif(sarif_file: str) -> list:
    """解析SARIF结果文件"""
    alerts = []

    try:
        with open(sarif_file, "r") as f:
            data = json.load(f)

        runs = data.get("runs", [])
        for run in runs:
            # tool = run.get('tool', {}).get('driver', {}).get('name', 'Unknown')
            results = run.get("results", [])

            for result in results:
                rule_id = result.get("ruleId", "unknown")
                message = result.get("message", {}).get("text", "")
                level = result.get("level", "warning")

                # 获取位置信息
                locations = result.get("locations", [])
                for location in locations:
                    physical = location.get("physicalLocation", {})
                    artifact = physical.get("artifactLocation", {})
                    region = physical.get("region", {})

                    file_path = artifact.get("uri", "unknown")
                    line = region.get("startLine", 0)

                    alerts.append(
                        {
                            "rule": rule_id,
                            "message": message,
                            "level": level,
                            "file": file_path,
                            "line": line,
                        }
                    )
    except Exception as e:
        print(f"⚠️  Could not parse SARIF: {e}")

    return alerts


def categorize_alerts(alerts: list) -> dict:
    """分类警报"""
    categories = {"error": [], "warning": [], "note": []}

    for alert in alerts:
        level = alert.get("level", "warning")
        if level in categories:
            categories[level].append(alert)

    return categories


def main() -> int:
    """主函数"""
    print("=" * 70)
    print("🔒 CodeQL Full Security Analysis (Local)")
    print("=" * 70)
    print()

    # 检查CodeQL CLI
    if not check_codeql_installed():
        print("❌ CodeQL CLI not installed")
        print()
        print("Install from: https://github.com/github/codeql-cli-binaries")
        print()
        print("Quick install:")
        print(
            "  wget https://github.com/github/codeql-cli-binaries/releases/download/v2.20.3/codeql-linux64.zip"
        )
        print("  unzip codeql-linux64.zip -d ~/.local/bin/")
        print("  export PATH=$PATH:~/.local/bin/codeql")
        return 1

    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="codeql_db_")
    db_path = os.path.join(temp_dir, "python-db")
    output_file = os.path.join(temp_dir, "results.sarif")

    try:
        # 创建数据库
        if not create_codeql_database(db_path):
            return 1

        # 分析数据库
        success, alerts = analyze_database(db_path, output_file)
        if not success:
            return 1

        # 分类结果
        categories = categorize_alerts(alerts)

        # 输出结果
        print("\n" + "=" * 70)
        print("📊 Analysis Results")
        print("=" * 70)
        print()

        total_errors = len(categories["error"])
        total_warnings = len(categories["warning"])
        total_notes = len(categories["note"])

        print(f"   Errors:   {total_errors}")
        print(f"   Warnings: {total_warnings}")
        print(f"   Notes:    {total_notes}")
        print()

        # 显示错误（阻塞性问题）
        if categories["error"]:
            print("❌ ERRORS (Blocking):")
            print()
            for alert in categories["error"][:10]:
                print(f"   🔴 {alert['file']}:{alert['line']}")
                print(f"      Rule: {alert['rule']}")
                print(f"      {alert['message'][:100]}")
                print()

            if len(categories["error"]) > 10:
                print(f"   ... and {len(categories['error']) - 10} more errors")
                print()

        # 显示警告
        if categories["warning"]:
            print("⚠️  WARNINGS:")
            print()
            for alert in categories["warning"][:5]:
                print(f"   🟡 {alert['file']}:{alert['line']}")
                print(f"      Rule: {alert['rule']}")
                print(f"      {alert['message'][:80]}")
                print()

            if len(categories["warning"]) > 5:
                print(f"   ... and {len(categories['warning']) - 5} more warnings")
                print()

        print("=" * 70)

        # 如果有错误，返回非零状态码
        if total_errors > 0:
            print()
            print(f"❌ Found {total_errors} security errors")
            print("   Please fix these issues before pushing.")
            print("   Use '# nosec' comment if this is a false positive.")
            return 1

        print()
        print("✅ No security errors found!")

        if total_warnings > 0:
            print(f"   (Note: {total_warnings} warnings - review recommended)")

        print()
        print("Full results saved to:")
        print(f"   {output_file}")
        print()
        print("View with: codeql interpret-results --format=markdown")
        print("=" * 70)
        return 0

    finally:
        # 清理临时目录
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
