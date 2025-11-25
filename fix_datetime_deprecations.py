#!/usr/bin/env python3
"""Fix datetime.utcnow() deprecations across all Python files."""

import re
from pathlib import Path

# List of files to fix
FILES_TO_FIX = [
    "tests/security/test_comprehensive_security.py",
    "scripts/reporting/cache_savings_report.py",
    "director_agent_extended_components.py",
    "ai_testing/services/orchestrator_service.py",
    "ai_testing/framework/scenario_manager.py",
    "ai_testing/services/results_aggregation_service.py",
    "ai_testing/services/notification_service.py",
    "ai_testing/services/ai_quality_service.py",
    "ai_testing/orchestration/master_orchestrator.py",
    "ops/monitoring/synthetic/monitoring.py",
    "ops/monitoring/prometheus_metrics.py",
    "ops/monitoring/observability/server.py",
    "ops/monitoring/dashboards/data.py",
    "ops/monitoring/alerts/alerting.py",
    "monitoring/synthetic_monitoring.py",
    "monitoring/prometheus_metrics.py",
    "monitoring/observability_server.py",
    "monitoring/health_checks.py",
    "monitoring/dashboard_data.py",
    "monitoring/alerting.py",
]


def fix_file(filepath: Path) -> tuple[bool, int]:
    """Fix datetime.utcnow() in a file.

    Returns:
        (modified, count) where modified is True if file was changed, count is number of replacements
    """
    if not filepath.exists():
        return False, 0

    content = filepath.read_text()
    original_content = content

    # Count replacements
    count = len(re.findall(r'datetime\.utcnow\(\)', content))

    if count == 0:
        return False, 0

    # Fix import statement - add timezone if not present
    if 'from datetime import' in content:
        # Check if timezone is already imported
        if not re.search(r'from datetime import.*timezone', content):
            # Add timezone to existing import
            content = re.sub(
                r'(from datetime import [^;\n]+)',
                lambda m: m.group(1) + ', timezone' if 'timezone' not in m.group(1) else m.group(1),
                content
            )

    # Replace datetime.utcnow() with datetime.now(timezone.utc)
    content = re.sub(r'datetime\.utcnow\(\)', 'datetime.now(timezone.utc)', content)

    if content != original_content:
        filepath.write_text(content)
        return True, count

    return False, 0


def main():
    """Main function to fix all files."""
    total_files = 0
    total_replacements = 0

    base_path = Path("/mnt/d/Code/novel-engine")

    for file_path_str in FILES_TO_FIX:
        filepath = base_path / file_path_str
        modified, count = fix_file(filepath)

        if modified:
            total_files += 1
            total_replacements += count
            print(f"✓ Fixed {filepath.relative_to(base_path)}: {count} replacements")
        elif filepath.exists():
            print(f"- Skipped {filepath.relative_to(base_path)}: already fixed or no occurrences")
        else:
            print(f"✗ Not found: {filepath.relative_to(base_path)}")

    print(f"\n✓ Total: Fixed {total_files} files with {total_replacements} replacements")


if __name__ == "__main__":
    main()
