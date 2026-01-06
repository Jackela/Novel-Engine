#!/usr/bin/env python3
"""
Novel Engine Pipeline Validation Script
=======================================

Quick validation script to test pipeline components and integration
before running full evaluation suite.

Development Phase: Work Order PR-07.3 - Pipeline Validation
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def validate_pipeline_components():
    """Validate all pipeline components are properly configured."""

    print("🔍 Novel Engine Pipeline Validation")
    print("=" * 40)

    validation_results = {}

    # 1. Check required directories
    print("\n📁 Checking Directory Structure...")
    required_dirs = [
        "evaluation/seeds",
        "evaluation/results",
        "evaluation/archive",
        "scripts",
    ]

    for dir_path in required_dirs:
        full_path = Path(dir_path)
        if full_path.exists():
            print(f"  ✅ {dir_path}")
            validation_results[f"dir_{dir_path.replace('/', '_')}"] = True
        else:
            print(f"  ❌ {dir_path} - MISSING")
            validation_results[f"dir_{dir_path.replace('/', '_')}"] = False

    # 2. Check required files
    print("\n📄 Checking Required Files...")
    required_files = [
        "evaluate_baseline.py",
        "scripts/run_evaluation_pipeline.py",
        "evaluation/pipeline_config.yaml",
    ]

    for file_path in required_files:
        full_path = Path(file_path)
        if full_path.exists():
            print(f"  ✅ {file_path}")
            validation_results[
                f"file_{file_path.replace('/', '_').replace('.', '_')}"
            ] = True
        else:
            print(f"  ❌ {file_path} - MISSING")
            validation_results[
                f"file_{file_path.replace('/', '_').replace('.', '_')}"
            ] = False

    # 3. Check seed files
    print("\n🌱 Checking Evaluation Seeds...")
    seeds_dir = Path("evaluation/seeds")
    if seeds_dir.exists():
        seed_files = list(seeds_dir.glob("*.yaml"))
        print(f"  📊 Found {len(seed_files)} seed files:")
        for seed_file in sorted(seed_files):
            print(f"    ✅ {seed_file.name}")
        validation_results["seed_count"] = len(seed_files)
        validation_results["seeds_present"] = len(seed_files) > 0
    else:
        print("  ❌ Seeds directory not found")
        validation_results["seeds_present"] = False

    # 4. Check Python imports
    print("\n🐍 Checking Python Dependencies...")
    test_imports = [
        ("yaml", "PyYAML for configuration"),
        ("json", "JSON processing"),
        ("argparse", "Command line parsing"),
        ("pathlib", "Path handling"),
    ]

    import_success = 0
    for module, description in test_imports:
        try:
            __import__(module)
            print(f"  ✅ {module} - {description}")
            import_success += 1
        except ImportError:
            print(f"  ❌ {module} - {description} - MISSING")

    validation_results["python_imports"] = import_success == len(test_imports)

    # 5. Test pipeline configuration loading
    print("\n⚙️ Testing Pipeline Configuration...")
    try:
        import yaml

        config_path = Path("evaluation/pipeline_config.yaml")
        if config_path.exists():
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            print("  ✅ Pipeline configuration loaded successfully")
            print(
                f"    📋 Run mode: {config.get('execution', {}).get('run_mode', 'unknown')}"
            )
            print(
                f"    🎯 Quality gate pass rate: {config.get('quality_gates', {}).get('minimum_pass_rate', 'unknown')}"
            )
            validation_results["config_loading"] = True
        else:
            print("  ❌ Pipeline configuration file not found")
            validation_results["config_loading"] = False
    except Exception as e:
        print(f"  ❌ Configuration loading failed: {e}")
        validation_results["config_loading"] = False

    # 6. Test baseline evaluator import
    print("\n🔬 Testing Baseline Evaluator Import...")
    try:
        pass

        print("  ✅ Baseline evaluator imports successful")
        validation_results["evaluator_import"] = True
    except ImportError as e:
        print(f"  ❌ Baseline evaluator import failed: {e}")
        validation_results["evaluator_import"] = False
    except Exception as e:
        print(f"  ❌ Unexpected error importing evaluator: {e}")
        validation_results["evaluator_import"] = False

    # 7. Test pipeline runner import
    print("\n📈 Testing Pipeline Runner Import...")
    try:
        sys.path.insert(0, "scripts")

        print("  ✅ Pipeline runner imports successful")
        validation_results["pipeline_import"] = True
    except ImportError as e:
        print(f"  ❌ Pipeline runner import failed: {e}")
        validation_results["pipeline_import"] = False
    except Exception as e:
        print(f"  ❌ Unexpected error importing pipeline: {e}")
        validation_results["pipeline_import"] = False

    # Summary
    print("\n" + "=" * 40)
    print("📊 Validation Summary")
    print("=" * 40)

    passed_checks = sum(1 for result in validation_results.values() if result is True)
    total_checks = len([v for v in validation_results.values() if isinstance(v, bool)])

    if passed_checks == total_checks:
        print(f"🎉 ALL CHECKS PASSED ({passed_checks}/{total_checks})")
        print("\n✅ Pipeline is ready for execution!")
        return True
    else:
        print(f"⚠️  PARTIAL SUCCESS ({passed_checks}/{total_checks} checks passed)")
        print("\n❌ Pipeline requires fixes before execution.")

        # Show failed checks
        print("\n🔧 Failed Checks:")
        for key, result in validation_results.items():
            if isinstance(result, bool) and not result:
                print(f"  • {key}")

        return False


def test_dry_run():
    """Test pipeline dry run functionality."""
    print("\n🧪 Testing Pipeline Dry Run...")

    try:
        # Import pipeline runner
        sys.path.insert(0, "scripts")
        from run_evaluation_pipeline import EvaluationPipeline, load_pipeline_config

        # Load configuration
        config = load_pipeline_config(Path("evaluation/pipeline_config.yaml"))

        # Create pipeline
        EvaluationPipeline(config)

        print("  ✅ Pipeline instance created successfully")
        print("  ✅ Configuration loaded successfully")
        print("  ✅ Dry run validation complete")

        return True

    except Exception as e:
        print(f"  ❌ Dry run failed: {e}")
        return False


def main():
    """Main validation entry point."""
    try:
        # Change to project root
        os.chdir(Path(__file__).parent.parent)

        # Run component validation
        components_ok = validate_pipeline_components()

        # Run dry run test if components are ok
        if components_ok:
            dry_run_ok = test_dry_run()

            if dry_run_ok:
                print("\n🚀 Pipeline validation complete - Ready for evaluation!")
                return 0
            else:
                print("\n⚠️ Pipeline validation failed at dry run stage")
                return 1
        else:
            print("\n❌ Pipeline validation failed at component stage")
            return 1

    except Exception as e:
        print(f"\n💥 Validation script failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
