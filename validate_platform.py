#!/usr/bin/env python3
"""
Novel Engine Platform Validation Runner
=======================================

Simple script to run end-to-end platform validation for M2: Platform Foundation milestone.

Usage:
    python validate_platform.py

This script validates:
- Configuration loading and environment settings
- Database connectivity and operations
- Messaging system (Kafka) functionality
- Security framework (RBAC, JWT authentication)
- Event sourcing and outbox pattern
- Cross-service integration

Requirements:
- Docker services running (docker-compose up -d)
- Python dependencies installed
- Environment variables configured
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to Python path and handle platform name conflict
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import with explicit path to avoid standard library platform module conflict
import importlib.util

spec = importlib.util.spec_from_file_location(
    "platform_validation",
    project_root / "platform" / "validation" / "e2e_platform_validator.py",
)
platform_validation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(platform_validation)

PlatformValidator = platform_validation.PlatformValidator


def setup_logging():
    """Setup logging for validation runner."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("platform_validation.log"),
        ],
    )


async def main():
    """Main validation runner."""
    print("🚀 Novel Engine Platform Validation")
    print("M2: Platform Foundation Milestone")
    print("=" * 50)

    setup_logging()
    logger = logging.getLogger(__name__)

    # Check if Docker services are likely running
    logger.info("Checking environment prerequisites...")

    # Run platform validation
    validator = PlatformValidator()

    try:
        logger.info("Starting comprehensive platform validation...")
        report = await validator.run_full_validation()

        # Save report to file
        import json

        report_file = "platform_validation_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Validation report saved to: {report_file}")

        # Print summary
        print("\n" + "=" * 50)
        print("VALIDATION SUMMARY")
        print("=" * 50)
        print(f"Status: {report['overall_status'].upper()}")
        print(
            f"Tests: {report['summary']['tests_passed']}/{report['summary']['total_tests']} passed"
        )
        print(f"Success Rate: {report['summary']['success_rate']:.1f}%")
        print(f"Duration: {report['summary']['duration_ms']:.1f}ms")
        print(f"Platform Ready: {'YES' if report['platform_ready'] else 'NO'}")

        if report["platform_ready"]:
            print("\n✅ PLATFORM FOUNDATION IS OPERATIONAL!")
            print("🎉 M2: Platform Foundation milestone COMPLETED successfully")
            return 0
        else:
            print("\n❌ Platform has issues requiring attention")
            print("📋 Check the detailed report for specific failures")
            return 1

    except KeyboardInterrupt:
        logger.info("Validation cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        print(f"\n❌ Validation failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
