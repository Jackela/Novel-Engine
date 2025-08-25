#!/usr/bin/env python3
"""
AI Testing Framework Configuration Override

Provides configuration structure specifically for AI testing services
that's compatible with the existing Novel-Engine config system.
"""

import os
from typing import Dict, Any

def get_ai_testing_config() -> Dict[str, Any]:
    """Get AI testing specific configuration"""
    return {
        "ai_testing": {
            "browser_automation": {
                "max_concurrent_contexts": 10,
                "default_timeout_ms": 30000,
                "screenshots_dir": "ai_testing/screenshots",
                "videos_dir": "ai_testing/videos",
                "browser_types": ["chromium"],
                "headless": True,
                "slow_mo_ms": 0,
                "browser_args": [],
                "visual_threshold": 0.1,
                "accessibility_standards": ["WCAG2A"],
                "performance_thresholds": {
                    "load_time_ms": 3000,
                    "fcp_ms": 1800,
                    "lcp_ms": 2500,
                    "cls": 0.1
                }
            },
            "api_testing": {
                "default_timeout_seconds": 30,
                "max_retries": 3,
                "retry_delay_seconds": 1,
                "default_max_response_time_ms": 2000,
                "enable_load_testing": True,
                "max_concurrent_requests": 100
            },
            "ai_quality": {
                "llm_judge": {
                    "default_models": ["gpt-4", "gemini-pro"],
                    "timeout_seconds": 60,
                    "max_retries": 2,
                    "enable_ensemble": True,
                    "quality_threshold": 0.7
                }
            },
            "results_aggregation": {
                "enable_real_time_aggregation": True,
                "auto_generate_reports": True,
                "report_formats": ["json", "html", "markdown"],
                "cleanup_interval_hours": 24,
                "max_stored_results": 10000
            },
            "notification": {
                "enable_notifications": True,
                "notification_channels": ["console", "file"],
                "alert_thresholds": {
                    "failure_rate": 0.2,
                    "response_time_ms": 5000,
                    "error_count": 10
                },
                "email": {
                    "enabled": False,
                    "smtp_server": "localhost",
                    "smtp_port": 587,
                    "use_tls": True
                },
                "slack": {
                    "enabled": False,
                    "webhook_url": "",
                    "default_channel": "#alerts"
                },
                "webhook": {
                    "enabled": True,
                    "webhook_url": "http://localhost:9999/webhook",
                    "method": "POST"
                },
                "alert_detection": {
                    "enabled": True,
                    "min_quality_score": 0.7,
                    "max_failure_rate": 0.3
                }
            }
        },
        "orchestration": {
            "services_base_port": 8000,
            "health_check_interval_seconds": 30,
            "health_cache_ttl_seconds": 60,
            "max_concurrent_sessions": 10,
            "default_timeout_minutes": 60
        }
    }

def get_ai_testing_service_config(service_name: str) -> Dict[str, Any]:
    """Get configuration for a specific AI testing service"""
    config = get_ai_testing_config()
    
    if service_name == "browser_automation":
        return config["ai_testing"]["browser_automation"]
    elif service_name == "api_testing":
        return config["ai_testing"]["api_testing"]
    elif service_name == "ai_quality":
        return config["ai_testing"]["ai_quality"]
    elif service_name == "results_aggregation":
        return config["ai_testing"]["results_aggregation"]
    elif service_name == "notification":
        return config["ai_testing"]["notification"]
    elif service_name == "orchestration":
        return config["orchestration"]
    else:
        return {}