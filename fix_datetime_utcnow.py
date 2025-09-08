#!/usr/bin/env python3
"""
Fix all datetime.utcnow() deprecation warnings in the codebase.
Python 3.12+ deprecates datetime.utcnow() in favor of timezone-aware datetime.
"""

import os
import re
from pathlib import Path


def fix_datetime_in_file(file_path):
    """Fix datetime.utcnow() in a single file"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original = content

        # Check if we need to add timezone import
        has_datetime_import = (
            "from datetime import" in content or "import datetime" in content
        )
        has_timezone_import = "timezone" in content and has_datetime_import

        if has_datetime_import and not has_timezone_import:
            # Add timezone to existing datetime import
            if "from datetime import" in content:
                # Find the import line and add timezone if not present
                import_pattern = r"(from datetime import[^;\n]+)"

                def add_timezone(match):
                    imports = match.group(1)
                    if "timezone" not in imports:
                        # Add timezone to the imports
                        if "(" in imports:
                            # Multi-line import
                            return imports.rstrip(")") + ", timezone)"
                        else:
                            # Single line import
                            return imports + ", timezone"
                    return imports

                content = re.sub(import_pattern, add_timezone, content)

        # Replace datetime.utcnow() with datetime.now(timezone.utc)
        content = content.replace("datetime.utcnow()", "datetime.now(timezone.utc)")

        # Also handle cases where datetime is imported as a module
        content = content.replace(
            "datetime.datetime.utcnow()", "datetime.datetime.now(datetime.timezone.utc)"
        )

        if content != original:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Fix all datetime.utcnow() occurrences in Python files"""

    # List of all files that need fixing
    files_to_fix = [
        "ai_testing/framework/scenario_manager.py",
        "ai_testing/orchestration/master_orchestrator.py",
        "ai_testing/services/ai_quality_service.py",
        "ai_testing/services/notification_service.py",
        "ai_testing/services/orchestrator_service.py",
        "ai_testing/services/results_aggregation_service.py",
        "contexts/character/infrastructure/repositories/character_repository.py",
        "core_platform/messaging/outbox.py",
        "core_platform/persistence/models.py",
        "monitoring/synthetic_monitoring.py",
        "monitoring/prometheus_metrics.py",
        "monitoring/observability_server.py",
        "monitoring/dashboard_data.py",
        "monitoring/alerting.py",
        "monitoring/health_checks.py",
        "ops/monitoring/synthetic/monitoring.py",
        "ops/monitoring/prometheus_metrics.py",
        "ops/monitoring/observability/server.py",
        "ops/monitoring/health_checks.py",
        "ops/monitoring/dashboards/data.py",
        "ops/monitoring/alerts/alerting.py",
        "production_security_implementation.py",
        "production_api_server.py",
        "security_middleware.py",
        "src/security/ssl_config.py",
        "tests/security/test_comprehensive_security.py",
        "tests/unit/contexts/character/application/services/test_context_loader.py",
    ]

    fixed_count = 0
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            if fix_datetime_in_file(file_path):
                print(f"✅ Fixed {file_path}")
                fixed_count += 1
        else:
            print(f"⚠️ File not found: {file_path}")

    print(f"\n✅ Fixed {fixed_count} files")

    # Also search for any remaining occurrences
    print("\n🔍 Checking for any remaining datetime.utcnow() occurrences...")
    remaining = []
    for root, dirs, files in os.walk("."):
        # Skip .trunk and other build directories
        if ".trunk" in root or "node_modules" in root or "__pycache__" in root:
            continue

        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        if "datetime.utcnow()" in f.read():
                            remaining.append(file_path)
                except:
                    pass

    if remaining:
        print(f"⚠️ Found {len(remaining)} files still containing datetime.utcnow():")
        for path in remaining[:10]:  # Show first 10
            print(f"  - {path}")
    else:
        print("✅ No remaining datetime.utcnow() found!")


if __name__ == "__main__":
    main()
