#!/usr/bin/env python3
"""
Prometheus Integration Tests

Tests for M10 Prometheus metrics collection and endpoint functionality.
Validates that core KPIs are properly collected and exposed.
"""

import asyncio
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from uuid import uuid4
from fastapi.testclient import TestClient

# Import the FastAPI app with M10 enhancements
from ..api.turn_api import app, prometheus_collector, enhanced_performance_tracker
from ..infrastructure.monitoring import PrometheusMetricsCollector
from ..domain.value_objects import TurnId, TurnConfiguration


class TestPrometheusIntegration:
    """Test suite for Prometheus metrics integration."""
    
    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        return TestClient(app)
    
    @pytest.fixture
    def metrics_collector(self):
        """Create test metrics collector."""
        return PrometheusMetricsCollector()
    
    def test_metrics_endpoint_exists(self, client):
        """Test that /metrics endpoint is accessible."""
        response = client.get("/metrics")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        
        # Check for basic Prometheus format
        content = response.text
        assert content is not None
        assert len(content) > 0
        
        # Should contain some basic metrics
        # (even if no turns executed, middleware metrics should be present)
        assert "# HELP" in content or "# TYPE" in content
    
    def test_core_kpi_metrics_structure(self, client):
        """Test that core KPI metrics are properly defined."""
        response = client.get("/metrics")
        assert response.status_code == 200
        
        content = response.text
        
        # Check for core KPI metrics (requested in M10)
        assert "novel_engine_llm_cost_per_request_dollars" in content
        assert "novel_engine_turn_duration_seconds" in content
        
        # Check for extended business metrics
        assert "novel_engine_turns_total" in content
        assert "novel_engine_turns_active" in content
    
    def test_business_kpis_endpoint(self, client):
        """Test the business KPIs summary endpoint."""
        response = client.get("/v1/metrics/business-kpis")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "business_kpis" in data
        assert "timestamp" in data
        
        kpis = data["business_kpis"]
        # Should contain core KPI fields (even if no data)
        assert "llm_cost_per_request_avg" in kpis
        assert "turn_duration_seconds_avg" in kpis
        assert "success_rate" in kpis
        assert "total_turns" in kpis
    
    def test_metrics_collector_functionality(self, metrics_collector):
        """Test that metrics collector records data correctly."""
        # Test turn start recording
        test_turn_id = uuid4()
        
        metrics_collector.record_turn_start(
            turn_id=test_turn_id,
            participants_count=2,
            ai_enabled=True,
            configuration={'narrative_depth': 'standard'}
        )
        
        # Test turn completion recording
        metrics_collector.record_turn_completion(
            turn_id=test_turn_id,
            participants_count=2,
            ai_enabled=True,
            success=True,
            execution_time_seconds=15.5,
            total_ai_cost=Decimal('1.25'),
            phase_results={
                'world_update': {
                    'success': True,
                    'execution_time_ms': 1000,
                    'events_processed': 5,
                    'events_generated': 3,
                    'ai_cost': 0.0
                }
            }
        )
        
        # Get metrics data
        metrics_data = metrics_collector.get_metrics_data()
        
        # Verify metrics are recorded
        assert "novel_engine_llm_cost_per_request_dollars" in metrics_data
        assert "novel_engine_turn_duration_seconds" in metrics_data
        assert "1.25" in metrics_data  # AI cost should be recorded
        assert "15.5" in metrics_data  # Duration should be recorded
    
    def test_phase_metrics_recording(self, metrics_collector):
        """Test that phase-level metrics are recorded."""
        metrics_collector.record_phase_execution(
            phase_name="subjective_brief",
            participants_count=3,
            success=True,
            execution_time_seconds=2.5,
            events_processed=8,
            events_generated=4,
            ai_cost=Decimal('0.75'),
            ai_requests=2,
            ai_tokens=150
        )
        
        metrics_data = metrics_collector.get_metrics_data()
        
        # Verify phase metrics
        assert "novel_engine_phase_duration_seconds" in metrics_data
        assert "novel_engine_phase_events_processed_total" in metrics_data
        assert "novel_engine_ai_cost_total_dollars" in metrics_data
        assert "subjective_brief" in metrics_data
    
    def test_error_metrics_recording(self, metrics_collector):
        """Test that error metrics are properly recorded."""
        metrics_collector.record_error(
            error_type="validation_error",
            severity="medium",
            component="turn_orchestrator",
            recovery_attempted=True,
            recovery_success=True
        )
        
        metrics_data = metrics_collector.get_metrics_data()
        
        # Verify error metrics
        assert "novel_engine_errors_total" in metrics_data
        assert "novel_engine_error_recovery_attempts_total" in metrics_data
        assert "validation_error" in metrics_data
    
    def test_compensation_metrics_recording(self, metrics_collector):
        """Test saga compensation metrics recording."""
        metrics_collector.record_compensation_execution(
            compensation_type="world_state_rollback",
            success=True,
            execution_time_seconds=1.2,
            rollback_reason="phase_failure"
        )
        
        metrics_data = metrics_collector.get_metrics_data()
        
        # Verify compensation metrics
        assert "novel_engine_compensations_total" in metrics_data
        assert "novel_engine_compensation_duration_seconds" in metrics_data
        assert "world_state_rollback" in metrics_data
    
    def test_enhanced_performance_tracker_integration(self):
        """Test that enhanced performance tracker integrates with Prometheus."""
        tracker = enhanced_performance_tracker
        
        # Test business KPI summary
        kpi_summary = tracker.get_business_kpi_summary()
        
        assert isinstance(kpi_summary, dict)
        assert "llm_cost_per_request_avg" in kpi_summary
        assert "turn_duration_seconds_avg" in kpi_summary
        assert "success_rate" in kpi_summary
        
        # Test Prometheus integration
        assert tracker.prometheus_collector is not None
        assert callable(tracker.get_prometheus_metrics)
        assert callable(tracker.get_prometheus_content_type)
    
    def test_http_middleware_metrics(self, client):
        """Test that HTTP middleware is collecting request metrics."""
        # Make some requests to generate metrics
        client.get("/v1/health")
        client.get("/v1/turns")  # This should generate metrics
        
        response = client.get("/metrics")
        assert response.status_code == 200
        
        content = response.text
        
        # Check for HTTP metrics from middleware
        assert "novel_engine_orchestration_http_requests_total" in content
        assert "novel_engine_orchestration_http_request_duration_seconds" in content
    
    def test_metrics_content_type(self, client):
        """Test that metrics endpoint returns correct content type."""
        response = client.get("/metrics")
        
        assert response.status_code == 200
        
        content_type = response.headers.get("content-type")
        assert content_type == "text/plain; version=0.0.4; charset=utf-8"
    
    def test_concurrent_metrics_collection(self, metrics_collector):
        """Test that metrics collection works under concurrent access."""
        import threading
        import time
        
        def record_metrics(thread_id):
            for i in range(10):
                turn_id = uuid4()
                metrics_collector.record_turn_start(
                    turn_id=turn_id,
                    participants_count=2,
                    ai_enabled=True,
                    configuration={}
                )
                
                time.sleep(0.01)  # Small delay
                
                metrics_collector.record_turn_completion(
                    turn_id=turn_id,
                    participants_count=2,
                    ai_enabled=True,
                    success=True,
                    execution_time_seconds=1.0,
                    total_ai_cost=Decimal('0.50'),
                    phase_results={}
                )
        
        # Run concurrent threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=record_metrics, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify metrics were recorded
        metrics_data = metrics_collector.get_metrics_data()
        assert "novel_engine_turns_total" in metrics_data
        assert "novel_engine_llm_cost_per_request_dollars" in metrics_data


if __name__ == "__main__":
    # Simple test runner for development
    import sys
    
    test_instance = TestPrometheusIntegration()
    
    # Create test client
    client = TestClient(app)
    
    # Run basic tests
    try:
        print("Testing metrics endpoint accessibility...")
        test_instance.test_metrics_endpoint_exists(client)
        print("✅ Metrics endpoint test passed")
        
        print("Testing core KPI metrics structure...")
        test_instance.test_core_kpi_metrics_structure(client)
        print("✅ Core KPI metrics test passed")
        
        print("Testing business KPIs endpoint...")
        test_instance.test_business_kpis_endpoint(client)
        print("✅ Business KPIs endpoint test passed")
        
        print("Testing metrics collector functionality...")
        collector = PrometheusMetricsCollector()
        test_instance.test_metrics_collector_functionality(collector)
        print("✅ Metrics collector test passed")
        
        print("\n🎉 All basic Prometheus integration tests passed!")
        print("M10 Wave 2: Prometheus Metrics Implementation successful")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)