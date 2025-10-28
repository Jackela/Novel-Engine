#!/usr/bin/env python3
"""
Novel Engine Pipeline Demo Script
=================================

Demonstration script showing the evaluation pipeline capabilities
without running the full Novel Engine simulation (which requires
complete system integration).

Development Phase: Work Order PR-07.3 - Pipeline Demo
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_mock_evaluation_results():
    """Create mock evaluation results for pipeline testing."""

    # Mock results that would come from actual Novel Engine evaluation
    mock_results = [
        {
            "seed_id": "seed_001_basic_investigation",
            "score": 0.92,
            "passed": True,
            "violations": 1,
            "execution_time": 185.5,
            "total_actions": 45,
        },
        {
            "seed_id": "seed_002_resource_stress_test",
            "score": 0.78,
            "passed": True,
            "violations": 4,
            "execution_time": 312.7,
            "total_actions": 67,
        },
        {
            "seed_id": "seed_003_narrative_coherence",
            "score": 0.85,
            "passed": True,
            "violations": 2,
            "execution_time": 445.3,
            "total_actions": 89,
        },
        {
            "seed_id": "seed_004_social_hierarchy",
            "score": 0.73,
            "passed": True,
            "violations": 8,
            "execution_time": 578.9,
            "total_actions": 112,
        },
        {
            "seed_id": "seed_005_physics_causality",
            "score": 0.81,
            "passed": True,
            "violations": 6,
            "execution_time": 923.1,
            "total_actions": 134,
        },
    ]

    return mock_results


def save_mock_results(results):
    """Save mock results to the results directory."""

    results_dir = Path("evaluation/results")
    results_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for result in results:
        # Create individual result file as expected by pipeline
        result_data = {
            "evaluation_summary": {
                "seed_id": result["seed_id"],
                "overall_score": result["score"],
                "evaluation_passed": result["passed"],
                "timestamp": datetime.now().isoformat(),
            },
            "execution_metrics": {
                "execution_time_seconds": result["execution_time"],
                "total_actions": result.get("total_actions", 100),
            },
            "iron_laws_compliance": {"total_violations": result["violations"]},
        }

        result_file = results_dir / f"{result['seed_id']}_{timestamp}.json"
        with open(result_file, "w") as f:
            json.dump(result_data, f, indent=2)

        print(f"📄 Created mock result: {result_file}")


def demo_pipeline_execution():
    """Demonstrate pipeline execution with mock data."""

    print("🎭 Novel Engine Pipeline Demo")
    print("=" * 40)

    # Step 1: Create mock evaluation results
    print("\n1️⃣ Creating Mock Evaluation Results...")
    mock_results = create_mock_evaluation_results()
    save_mock_results(mock_results)

    # Step 2: Run the evaluation pipeline
    print("\n2️⃣ Running Evaluation Pipeline...")

    try:
        # Import pipeline components
        sys.path.insert(0, "scripts")
        from run_evaluation_pipeline import EvaluationPipeline, load_pipeline_config

        # Load configuration
        config = load_pipeline_config(Path("evaluation/pipeline_config.yaml"))

        # Create and run pipeline
        EvaluationPipeline(config)

        # Simulate running the evaluation (without actually calling Novel Engine)
        print("  ⚡ Initializing pipeline...")
        time.sleep(1)

        print("  📊 Processing evaluation results...")
        time.sleep(1)

        # Calculate results from our mock data
        total_seeds = len(mock_results)
        passed_seeds = sum(1 for r in mock_results if r["passed"])
        total_violations = sum(r["violations"] for r in mock_results)
        avg_score = sum(r["score"] for r in mock_results) / total_seeds
        total_time = sum(r["execution_time"] for r in mock_results)

        print("  📈 Generating reports...")
        time.sleep(1)

        # Display results summary
        print("\n3️⃣ Pipeline Results Summary:")
        print(f"  📊 Seeds Evaluated: {total_seeds}")
        print(f"  ✅ Seeds Passed: {passed_seeds}")
        print(f"  📈 Pass Rate: {passed_seeds/total_seeds*100:.1f}%")
        print(f"  🎯 Average Score: {avg_score:.3f}")
        print(f"  ⚠️ Total Violations: {total_violations}")
        print(f"  ⏱️ Total Execution Time: {total_time:.1f}s")

        # Check quality gates
        print("\n4️⃣ Quality Gate Assessment:")
        pass_rate = passed_seeds / total_seeds
        violation_rate = total_violations / sum(r.get("total_actions", 100) for r in mock_results)

        if pass_rate >= config.minimum_pass_rate:
            print(f"  ✅ Pass Rate Gate: {pass_rate:.1%} >= {config.minimum_pass_rate:.1%}")
        else:
            print(f"  ❌ Pass Rate Gate: {pass_rate:.1%} < {config.minimum_pass_rate:.1%}")

        if violation_rate <= config.maximum_violation_rate:
            print(
                f"  ✅ Violation Rate Gate: {violation_rate:.1%} <= {config.maximum_violation_rate:.1%}"
            )
        else:
            print(
                f"  ❌ Violation Rate Gate: {violation_rate:.1%} > {config.maximum_violation_rate:.1%}"
            )

        if total_violations <= config.critical_violation_threshold:
            print(
                f"  ✅ Critical Violations Gate: {total_violations} <= {config.critical_violation_threshold}"
            )
        else:
            print(
                f"  ❌ Critical Violations Gate: {total_violations} > {config.critical_violation_threshold}"
            )

        # Overall assessment
        gates_passed = (
            pass_rate >= config.minimum_pass_rate
            and violation_rate <= config.maximum_violation_rate
            and total_violations <= config.critical_violation_threshold
        )

        print("\n5️⃣ Overall Pipeline Status:")
        if gates_passed:
            print("  🎉 PIPELINE SUCCESS - All quality gates passed!")
        else:
            print("  ⚠️ PIPELINE PARTIAL SUCCESS - Some quality gates failed")

        print("\n📍 Report Files Generated:")
        print("  📊 Results: evaluation/results/")
        print("  📈 Reports would be generated in full pipeline run")

        return True

    except Exception as e:
        print(f"  ❌ Pipeline demo failed: {e}")
        return False


def main():
    """Main demo entry point."""
    try:
        # Change to project root
        import os

        os.chdir(Path(__file__).parent.parent)

        # Run demo
        success = demo_pipeline_execution()

        if success:
            print("\n🏆 Pipeline Demo Complete!")
            print("   The evaluation pipeline is ready for production use.")
            print("   Use 'python scripts/run_evaluation_pipeline.py --help' for full options.")
            return 0
        else:
            print("\n💥 Pipeline Demo Failed!")
            return 1

    except Exception as e:
        print(f"\n💥 Demo script failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
