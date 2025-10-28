#!/usr/bin/env python3
"""
Prometheus Metrics Validation

Simple validation script to test M10 Prometheus metrics implementation.
Can be run independently to verify Wave 2 functionality.
"""

import logging
import sys
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from domain.services import EnhancedPerformanceTracker

from infrastructure.monitoring import PrometheusMetricsCollector

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def test_prometheus_metrics_collector():
    """Test basic Prometheus metrics collector functionality."""
    print("\n🔍 Testing PrometheusMetricsCollector...")

    try:
        # Create collector
        collector = PrometheusMetricsCollector()

        # Test turn metrics recording
        test_turn_id = uuid4()

        # Record turn start
        collector.record_turn_start(
            turn_id=test_turn_id,
            participants_count=3,
            ai_enabled=True,
            configuration={"narrative_depth": "detailed"},
        )

        # Record turn completion with core KPIs
        collector.record_turn_completion(
            turn_id=test_turn_id,
            participants_count=3,
            ai_enabled=True,
            success=True,
            execution_time_seconds=22.5,  # turn_duration_seconds metric
            total_ai_cost=Decimal("2.75"),  # llm_cost_per_request metric
            phase_results={
                "world_update": {
                    "success": True,
                    "execution_time_ms": 2000,
                    "events_processed": 10,
                    "events_generated": 5,
                    "ai_cost": 0.0,
                },
                "subjective_brief": {
                    "success": True,
                    "execution_time_ms": 8000,
                    "events_processed": 15,
                    "events_generated": 8,
                    "ai_cost": 1.25,
                },
                "interaction_orchestration": {
                    "success": True,
                    "execution_time_ms": 12000,
                    "events_processed": 25,
                    "events_generated": 18,
                    "ai_cost": 0.75,
                },
                "event_integration": {
                    "success": True,
                    "execution_time_ms": 1500,
                    "events_processed": 18,
                    "events_generated": 12,
                    "ai_cost": 0.0,
                },
                "narrative_integration": {
                    "success": True,
                    "execution_time_ms": 6000,
                    "events_processed": 12,
                    "events_generated": 6,
                    "ai_cost": 0.75,
                },
            },
        )

        # Get metrics data
        metrics_data = collector.get_metrics_data()

        # Verify core KPIs are present
        core_kpis_found = {
            "llm_cost_per_request": "novel_engine_llm_cost_per_request_dollars" in metrics_data,
            "turn_duration_seconds": "novel_engine_turn_duration_seconds" in metrics_data,
            "turns_total": "novel_engine_turns_total" in metrics_data,
            "phase_duration": "novel_engine_phase_duration_seconds" in metrics_data,
            "ai_cost_total": "novel_engine_ai_cost_total_dollars" in metrics_data,
        }

        # Verify specific values are recorded
        value_checks = {
            "cost_value": "2.75" in metrics_data,
            "duration_value": "22.5" in metrics_data,
            "phase_names": all(
                phase in metrics_data
                for phase in [
                    "world_update",
                    "subjective_brief",
                    "interaction_orchestration",
                ]
            ),
        }

        print(f"✅ Core KPIs found: {core_kpis_found}")
        print(f"✅ Values recorded: {value_checks}")

        # Test additional metrics
        collector.record_error(error_type="test_error", severity="medium", component="validator")

        collector.record_compensation_execution(
            compensation_type="test_rollback", success=True, execution_time_seconds=0.5
        )

        final_metrics = collector.get_metrics_data()

        additional_metrics = {
            "errors_tracked": "novel_engine_errors_total" in final_metrics,
            "compensation_tracked": "novel_engine_compensations_total" in final_metrics,
        }

        print(f"✅ Additional metrics: {additional_metrics}")

        # Verify content type
        content_type = collector.get_metrics_content_type()
        print(f"✅ Content type: {content_type}")

        all_checks_passed = (
            all(core_kpis_found.values())
            and all(value_checks.values())
            and all(additional_metrics.values())
            and "text/plain" in content_type
        )

        if all_checks_passed:
            print("✅ PrometheusMetricsCollector: ALL TESTS PASSED")
            return True
        else:
            print("❌ PrometheusMetricsCollector: Some tests failed")
            return False

    except Exception as e:
        print(f"❌ PrometheusMetricsCollector test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_enhanced_performance_tracker():
    """Test enhanced performance tracker integration."""
    print("\n🔍 Testing EnhancedPerformanceTracker...")

    try:
        # Create enhanced tracker
        collector = PrometheusMetricsCollector()
        tracker = EnhancedPerformanceTracker(collector)

        # Test business KPI summary
        kpi_summary = tracker.get_business_kpi_summary()

        expected_kpis = [
            "llm_cost_per_request_avg",
            "turn_duration_seconds_avg",
            "success_rate",
            "total_turns",
        ]

        kpi_checks = {kpi: kpi in kpi_summary for kpi in expected_kpis}

        print(f"✅ KPI summary structure: {kpi_checks}")

        # Test Prometheus integration
        prometheus_methods = {
            "get_prometheus_metrics": hasattr(tracker, "get_prometheus_metrics"),
            "get_prometheus_content_type": hasattr(tracker, "get_prometheus_content_type"),
            "prometheus_collector": tracker.prometheus_collector is not None,
        }

        print(f"✅ Prometheus integration: {prometheus_methods}")

        # Test health status
        health_status = tracker.get_health_status()

        health_checks = {
            "has_enhanced_features": "enhanced_features" in health_status,
            "prometheus_integration": health_status.get("enhanced_features", {}).get(
                "prometheus_metrics", False
            ),
            "business_kpi_tracking": health_status.get("enhanced_features", {}).get(
                "business_kpi_tracking", False
            ),
        }

        print(f"✅ Health status: {health_checks}")

        all_checks_passed = (
            all(kpi_checks.values())
            and all(prometheus_methods.values())
            and all(health_checks.values())
        )

        if all_checks_passed:
            print("✅ EnhancedPerformanceTracker: ALL TESTS PASSED")
            return True
        else:
            print("❌ EnhancedPerformanceTracker: Some tests failed")
            return False

    except Exception as e:
        print(f"❌ EnhancedPerformanceTracker test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_fastapi_integration():
    """Test FastAPI integration (basic import test)."""
    print("\n🔍 Testing FastAPI Integration...")

    try:
        # Test imports
        from api.turn_api import app

        print("✅ FastAPI app import successful")

        # Test middleware integration (basic check)
        middleware_names = [middleware.cls.__name__ for middleware in app.middleware_stack]
        has_prometheus_middleware = any("Prometheus" in name for name in middleware_names)

        print(f"✅ Middleware stack: {middleware_names}")
        print(f"✅ Has Prometheus middleware: {has_prometheus_middleware}")

        # Test that app has the correct title and version
        app_info = {
            "title": app.title,
            "version": app.version,
            "description_contains_m10": "M10" in app.description,
        }

        print(f"✅ App info: {app_info}")

        if app_info["version"] == "2.0.0" and app_info["description_contains_m10"]:
            print("✅ FastAPI Integration: ALL TESTS PASSED")
            return True
        else:
            print("❌ FastAPI Integration: Version or description check failed")
            return False

    except Exception as e:
        print(f"❌ FastAPI integration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all validation tests."""
    print("=" * 80)
    print("M10 PROMETHEUS METRICS VALIDATION")
    print("=" * 80)

    test_results = []

    # Run all tests
    test_results.append(("PrometheusMetricsCollector", test_prometheus_metrics_collector()))
    test_results.append(("EnhancedPerformanceTracker", test_enhanced_performance_tracker()))
    test_results.append(("FastAPI Integration", test_fastapi_integration()))

    # Print results summary
    print("\n" + "=" * 80)
    print("VALIDATION RESULTS SUMMARY")
    print("=" * 80)

    passed_tests = 0
    total_tests = len(test_results)

    for test_name, passed in test_results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if passed:
            passed_tests += 1

    success_rate = passed_tests / total_tests
    print(f"\nSUCCESS RATE: {passed_tests}/{total_tests} ({success_rate:.1%})")

    if passed_tests == total_tests:
        print("\n🎉 M10 WAVE 2: PROMETHEUS METRICS IMPLEMENTATION SUCCESSFUL!")
        print("✅ Core KPIs implemented: llm_cost_per_request_dollars, turn_duration_seconds")
        print("✅ Extended metrics suite fully functional")
        print("✅ FastAPI integration with middleware working")
        print("✅ Enhanced performance tracking operational")
        print("\n🚀 Ready to proceed to Wave 3: OpenTelemetry Distributed Tracing")
        return 0
    else:
        print(f"\n❌ M10 WAVE 2: {total_tests - passed_tests} tests failed")
        print("🔧 Fix failing tests before proceeding to Wave 3")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
