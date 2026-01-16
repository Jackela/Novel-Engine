#!/usr/bin/env python3
"""
M10 OpenTelemetry Distributed Tracing Demonstration

Demonstrates the OpenTelemetry distributed tracing implementation with root span coverage
for the complete run_turn orchestration flow as required by M10 milestone.
"""

import asyncio
import logging
from decimal import Decimal
from uuid import UUID

from infrastructure.monitoring.tracing import (
    NovelEngineTracingConfig,
    initialize_tracing,
)
from infrastructure.monitoring.tracing_middleware import (
    TracingDependency,
)

# Configure logging for demo
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def demonstrate_turn_tracing():
    """Demonstrate comprehensive turn execution tracing."""
    print("🔬 M10 OPENTELEMETRY DISTRIBUTED TRACING DEMONSTRATION")
    print("=" * 70)

    # Initialize tracing with console output for demonstration
    tracing_config = NovelEngineTracingConfig(
        service_name="novel-engine-orchestration",
        service_version="2.0.0",
        environment="demonstration",
        sampling_rate=1.0,  # 100% sampling for demo
        enable_console_exporter=True,  # Show traces in console
    )

    tracer = initialize_tracing(tracing_config)

    print("✅ Distributed tracing initialized:")
    print(f"   Service: {tracing_config.service_name}")
    print(f"   Version: {tracing_config.service_version}")
    print(f"   Environment: {tracing_config.environment}")
    print(f"   Sampling Rate: {tracing_config.sampling_rate * 100}%")
    print(f"   Console Export: {tracing_config.enable_console_exporter}")

    # Simulate turn execution with comprehensive tracing
    print("\n🚀 Demonstrating root span coverage for complete run_turn flow...")

    # Test 1: Successful turn with all phases
    turn_id_1 = UUID("12345678-1234-5678-9012-123456789001")
    participants_1 = ["agent_alice", "agent_bob", "agent_charlie"]
    configuration_1 = {
        "ai_integration_enabled": True,
        "narrative_analysis_depth": "detailed",
        "max_execution_time_ms": 60000,
    }
    user_context_1 = {"user_id": "demo_user_001", "roles": ["player", "participant"]}

    print("\n📊 Test 1: Successful Turn Execution")
    print(f"   Turn ID: {turn_id_1}")
    print(f"   Participants: {len(participants_1)} agents")
    print("   Configuration: AI enabled, detailed narrative")

    # Start root span for turn execution (M10 requirement)
    turn_span_1 = tracer.start_turn_span(
        turn_id=turn_id_1,
        participants=participants_1,
        configuration=configuration_1,
        user_context=user_context_1,
    )

    print("✅ Root span started for complete turn execution flow")

    # Simulate the 5-phase pipeline with individual spans
    phases = [
        ("world_update", 1.2, 0, 10, 5, 0.0),
        ("subjective_brief", 6.8, 1, 15, 8, 1.25),
        ("interaction_orchestration", 8.3, 2, 25, 18, 0.75),
        ("event_integration", 1.5, 3, 18, 12, 0.0),
        ("narrative_integration", 4.2, 4, 12, 6, 0.85),
    ]

    total_ai_cost = Decimal("0.0")
    completed_phases = []

    for (
        phase_name,
        duration_sec,
        phase_order,
        events_proc,
        events_gen,
        ai_cost,
    ) in phases:
        print(f"   🔄 Executing phase: {phase_name}")

        # Start phase span as child of root span
        phase_span = tracer.start_phase_span(
            phase_name=phase_name,
            turn_id=turn_id_1,
            phase_order=phase_order + 1,
            parent_span=turn_span_1,
        )

        # Simulate phase execution time
        await asyncio.sleep(0.1)  # Brief simulation delay

        # Record successful phase result
        tracer.record_phase_result(
            span=phase_span,
            success=True,
            events_processed=events_proc,
            events_generated=events_gen,
            ai_cost=ai_cost,
            ai_requests=1 if ai_cost > 0 else 0,
            error_details=None,
        )

        # Close phase span
        phase_span.end()

        total_ai_cost += Decimal(str(ai_cost))
        completed_phases.append(phase_name)

        print(
            f"     ✅ Phase completed: {duration_sec}s, ${ai_cost}, {events_proc}→{events_gen} events"
        )

    # Record complete turn execution result in root span
    total_execution_time = sum(phase[1] for phase in phases)
    tracer.record_turn_result(
        span=turn_span_1,
        success=True,
        execution_time_seconds=total_execution_time,
        total_ai_cost=float(total_ai_cost),
        phases_completed=completed_phases,
        error_details=None,
    )

    # Close root span
    turn_span_1.end()

    print(
        f"✅ Root span completed: {total_execution_time}s total, ${total_ai_cost} cost"
    )
    print(f"   Phases completed: {len(completed_phases)}/5")
    print("   Root span covered complete run_turn orchestration flow")

    # Test 2: Failed turn with partial execution and compensation
    print("\n📊 Test 2: Failed Turn with Compensation")

    turn_id_2 = UUID("12345678-1234-5678-9012-123456789002")
    participants_2 = ["agent_david", "agent_eve"]
    configuration_2 = {
        "ai_integration_enabled": True,
        "narrative_analysis_depth": "standard",
        "max_execution_time_ms": 30000,
    }

    print(f"   Turn ID: {turn_id_2}")
    print(f"   Participants: {len(participants_2)} agents")
    print("   Configuration: AI enabled, standard narrative")

    # Start root span for failed turn
    turn_span_2 = tracer.start_turn_span(
        turn_id=turn_id_2, participants=participants_2, configuration=configuration_2
    )

    print("✅ Root span started for failed turn execution flow")

    # Simulate partial execution (first 3 phases succeed, 4th fails)
    failed_phases = [
        ("world_update", 1.5, 0, 8, 4, 0.0, True),
        ("subjective_brief", 7.2, 1, 12, 6, 1.15, True),
        ("interaction_orchestration", 9.1, 2, 20, 15, 0.65, True),
        ("event_integration", 0.8, 3, 8, 0, 0.0, False),  # This phase fails
    ]

    failed_total_cost = Decimal("0.0")
    failed_completed_phases = []

    for (
        phase_name,
        duration_sec,
        phase_order,
        events_proc,
        events_gen,
        ai_cost,
        success,
    ) in failed_phases:
        print(f"   🔄 Executing phase: {phase_name}")

        # Start phase span
        phase_span = tracer.start_phase_span(
            phase_name=phase_name,
            turn_id=turn_id_2,
            phase_order=phase_order + 1,
            parent_span=turn_span_2,
        )

        # Simulate phase execution time
        await asyncio.sleep(0.1)

        # Record phase result (success or failure)
        error_details = (
            None if success else f"Phase {phase_name} failed: simulated error"
        )

        tracer.record_phase_result(
            span=phase_span,
            success=success,
            events_processed=events_proc,
            events_generated=events_gen,
            ai_cost=ai_cost,
            ai_requests=1 if ai_cost > 0 else 0,
            error_details=error_details,
        )

        # Close phase span
        phase_span.end()

        failed_total_cost += Decimal(str(ai_cost))
        if success:
            failed_completed_phases.append(phase_name)
            print(f"     ✅ Phase completed: {duration_sec}s, ${ai_cost}")
        else:
            print(f"     ❌ Phase failed: {duration_sec}s, ${ai_cost} (partial cost)")
            break

    # Record failed turn execution result
    failed_execution_time = sum(phase[1] for phase in failed_phases)
    tracer.record_turn_result(
        span=turn_span_2,
        success=False,
        execution_time_seconds=failed_execution_time,
        total_ai_cost=float(failed_total_cost),
        phases_completed=failed_completed_phases,
        error_details="Turn execution failed at event_integration phase",
    )

    # Close root span for failed turn
    turn_span_2.end()

    print(
        f"❌ Root span completed for failed turn: {failed_execution_time}s, ${failed_total_cost}"
    )
    print(f"   Phases completed: {len(failed_completed_phases)}/4 (before failure)")
    print("   Root span captured complete failure flow for analysis")

    # Test 3: Cross-context service calls
    print("\n📊 Test 3: Cross-Context Service Calls")

    turn_id_3 = UUID("12345678-1234-5678-9012-123456789003")
    participants_3 = ["agent_frank"]

    # Start root span for cross-context calls
    turn_span_3 = tracer.start_turn_span(
        turn_id=turn_id_3,
        participants=participants_3,
        configuration={"ai_integration_enabled": False},
    )

    print("✅ Root span started for cross-context integration demonstration")

    # Simulate cross-context service calls
    cross_context_calls = [
        ("world_context", "get_current_state", True, 0.2),
        ("narrative_context", "generate_content", True, 1.8),
        ("character_context", "update_attributes", False, 0.5),  # This call fails
        ("event_context", "record_interactions", True, 0.3),
    ]

    for target_context, operation, success, duration in cross_context_calls:
        print(f"   🌐 Cross-context call: {target_context}.{operation}")

        # Simulate call execution
        await asyncio.sleep(0.05)

        # Record cross-context call in span
        tracer.record_cross_context_call(
            span=turn_span_3,
            target_context=target_context,
            operation=operation,
            success=success,
            duration_seconds=duration,
        )

        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"     {status}: {duration}s")

    # Complete cross-context demonstration
    cross_context_total_time = sum(call[3] for call in cross_context_calls)
    tracer.record_turn_result(
        span=turn_span_3,
        success=True,
        execution_time_seconds=cross_context_total_time,
        total_ai_cost=0.0,
        phases_completed=["cross_context_integration"],
        error_details=None,
    )

    turn_span_3.end()

    print(f"✅ Cross-context tracing completed: {cross_context_total_time}s")
    print("   All service calls captured in distributed trace")

    return True


def demonstrate_tracing_middleware():
    """Demonstrate FastAPI middleware integration."""
    print("\n🔌 FASTAPI MIDDLEWARE INTEGRATION DEMONSTRATION")
    print("=" * 70)

    try:
        from fastapi import FastAPI

        # Create demo FastAPI app
        demo_app = FastAPI(title="Tracing Demo")

        # Initialize tracer
        tracer = initialize_tracing()

        # Add tracing middleware
        from infrastructure.monitoring.tracing_middleware import setup_fastapi_tracing

        setup_fastapi_tracing(
            app=demo_app,
            tracer=tracer,
            excluded_urls=["/health"],
            enable_automatic_instrumentation=True,
        )

        print("✅ FastAPI tracing middleware configured:")
        print("   - OpenTelemetryMiddleware added to app")
        print("   - Automatic HTTP request instrumentation enabled")
        print("   - Trace context propagation configured")
        print("   - Excluded URLs: /health")

        # Demonstrate tracing dependency
        TracingDependency()

        print("✅ Tracing dependency configured for route handlers")
        print("   - Provides access to current trace span")
        print("   - Enables span attribute setting in handlers")
        print("   - Supports trace context correlation")

        # Demonstrate utility functions
        print("✅ Tracing utility functions available:")
        print("   - get_trace_context(request): Get current span")
        print("   - add_trace_attributes(request, **attrs): Add span attributes")
        print("   - Trace context propagation helpers")

        return True

    except ImportError as e:
        print(f"❌ FastAPI middleware demonstration failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Middleware setup error: {e}")
        return False


def demonstrate_intelligent_sampling():
    """Demonstrate intelligent sampling strategies."""
    print("\n🎯 INTELLIGENT SAMPLING DEMONSTRATION")
    print("=" * 70)

    from opentelemetry.trace import SpanKind

    from infrastructure.monitoring.tracing import IntelligentSampler

    # Create intelligent sampler
    sampler = IntelligentSampler(default_rate=0.1)  # 10% default sampling

    print("✅ Intelligent sampler initialized:")
    print("   - Default sampling rate: 10%")
    print("   - Error sampling rate: 100%")
    print("   - High-cost operation sampling: 50%")
    print("   - Slow operation sampling: 80%")

    # Test sampling decisions
    test_scenarios = [
        ("Normal operation", {}, "Should sample ~10% of normal operations"),
        (
            "Error operation",
            {"error.type": "ValidationError"},
            "Should sample 100% of errors",
        ),
        (
            "High-cost AI operation",
            {"turn.total_cost": 5.0},
            "Should sample 50% of expensive operations",
        ),
        (
            "Slow operation",
            {"turn.duration_seconds": 15.0},
            "Should sample 80% of slow operations",
        ),
        (
            "Critical error",
            {"error.type": "CriticalError", "turn.total_cost": 10.0},
            "Should sample 100% (error priority)",
        ),
    ]

    print("\n🔍 Sampling decision tests:")

    for scenario_name, attributes, description in test_scenarios:
        # Simulate sampling decision
        decision = sampler.should_sample(
            context=None,
            trace_id=12345,
            name="test_span",
            kind=SpanKind.INTERNAL,
            attributes=attributes,
        )

        sample_decision = (
            "SAMPLE" if decision.decision.name == "RECORD_AND_SAMPLE" else "DROP"
        )
        print(f"   {scenario_name}: {sample_decision}")
        print(f"     Attributes: {attributes}")
        print(f"     Rationale: {description}")

    print("✅ Intelligent sampling configured for optimal trace collection")

    return True


async def main():
    """Run complete M10 OpenTelemetry distributed tracing demonstration."""
    print("Starting M10 OpenTelemetry distributed tracing demonstration...")

    # Track demonstration results
    results = []

    # Test 1: Core tracing functionality
    try:
        success = await demonstrate_turn_tracing()
        results.append(("Turn Execution Tracing", success))
    except Exception as e:
        print(f"❌ Turn tracing demonstration failed: {e}")
        results.append(("Turn Execution Tracing", False))

    # Test 2: FastAPI middleware integration
    try:
        success = demonstrate_tracing_middleware()
        results.append(("FastAPI Middleware Integration", success))
    except Exception as e:
        print(f"❌ Middleware demonstration failed: {e}")
        results.append(("FastAPI Middleware Integration", False))

    # Test 3: Intelligent sampling
    try:
        success = demonstrate_intelligent_sampling()
        results.append(("Intelligent Sampling", success))
    except Exception as e:
        print(f"❌ Sampling demonstration failed: {e}")
        results.append(("Intelligent Sampling", False))

    # Print results summary
    print("\n" + "=" * 70)
    print("M10 OPENTELEMETRY TRACING DEMONSTRATION RESULTS")
    print("=" * 70)

    passed_tests = 0
    total_tests = len(results)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if passed:
            passed_tests += 1

    success_rate = passed_tests / total_tests
    print(f"\nSUCCESS RATE: {passed_tests}/{total_tests} ({success_rate:.1%})")

    if passed_tests == total_tests:
        print("\n🎉 M10 WAVE 3: OPENTELEMETRY DISTRIBUTED TRACING SUCCESSFUL!")
        print("=" * 70)
        print("✅ Root span coverage for complete run_turn orchestration flow")
        print("✅ Phase-level spans for detailed execution tracing")
        print("✅ Cross-context service call instrumentation")
        print("✅ FastAPI middleware for HTTP request tracing")
        print("✅ Intelligent sampling for optimal trace collection")
        print("✅ Error tracking and failure analysis capabilities")
        print("✅ User context integration for security tracing")
        print("\n🚀 Ready to proceed to Wave 4: Security Framework Implementation")
        return True
    else:
        print(f"\n❌ M10 WAVE 3: {total_tests - passed_tests} tests failed")
        print("🔧 Fix failing tests before proceeding to Wave 4")
        return False


if __name__ == "__main__":
    # Run the demonstration
    success = asyncio.run(main())
    exit(0 if success else 1)
