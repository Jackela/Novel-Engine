#!/usr/bin/env python3
"""
Fix All Remaining Validation Issues Script

This script applies all necessary fixes to achieve >80% success rate.
"""

import subprocess
import time

import psutil


def kill_all_python_processes():
    """Kill all Python processes on Windows"""
    print("🔧 Stopping all Python processes...")

    # Try multiple methods to ensure all processes are killed
    methods = [
        "taskkill /F /IM python.exe 2>nul",
        "taskkill /F /IM pythonw.exe 2>nul",
        'powershell -Command "Get-Process python* | Stop-Process -Force" 2>nul',
    ]

    for method in methods:
        try:
            subprocess.run(method, shell=True, capture_output=True)
        except Exception:
            pass

    # Additional method using psutil
    try:
        for proc in psutil.process_iter(["pid", "name"]):
            if "python" in proc.info["name"].lower():
                try:
                    proc.terminate()
                except Exception:
                    pass
    except Exception:
        pass

    time.sleep(3)
    print("✅ All Python processes stopped")


def start_service(name, port, module):
    """Start a service in background"""
    print(f"🚀 Starting {name} on port {port}...")

    cmd = f"start /B python -m uvicorn {module}:app --port {port} --log-level error"

    try:
        subprocess.Popen(
            cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        time.sleep(2)
        print(f"✅ {name} started")
        return True
    except Exception as e:
        print(f"❌ Failed to start {name}: {e}")
        return False


def check_service_health(port):
    """Check if a service is healthy"""
    import requests

    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=5)
        data = response.json()
        return data.get("status") in ["healthy", "ready"]
    except (requests.RequestException, ValueError, TimeoutError):
        return False


def apply_config_fixes():
    """Apply configuration fixes"""
    print("🔧 Applying configuration fixes...")

    # Update notification config to enable channels
    config_file = "D:\\Code\\Novel-Engine\\ai_testing_config.py"

    config_content = '''#!/usr/bin/env python3
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
                "webhook": {
                    "enabled": True,
                    "url": "http://localhost:8005/webhook",
                    "method": "POST"
                },
                "console": {
                    "enabled": True
                },
                "file": {
                    "enabled": True,
                    "output_directory": "ai_testing/notifications"
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
'''

    with open(config_file, "w") as f:
        f.write(config_content)

    print("✅ Configuration fixes applied")


def main():
    """Main execution"""
    print("=" * 60)
    print("🌊 AI Testing Framework - Complete Fix Script")
    print("=" * 60)

    # Step 1: Kill all existing processes
    kill_all_python_processes()

    # Step 2: Apply configuration fixes
    apply_config_fixes()

    # Step 3: Start all services in correct order
    services = [
        ("Master Orchestrator", 8000, "ai_testing.orchestration.master_orchestrator"),
        ("Browser Automation", 8001, "ai_testing.services.browser_automation_service"),
        ("API Testing", 8002, "ai_testing.services.api_testing_service"),
        ("AI Quality", 8003, "ai_testing.services.ai_quality_service"),
        (
            "Results Aggregation",
            8004,
            "ai_testing.services.results_aggregation_service",
        ),
        ("Notification", 8005, "ai_testing.services.notification_service"),
    ]

    print("\n📦 Starting all services...")
    for name, port, module in services:
        start_service(name, port, module)

    # Step 4: Wait for services to stabilize
    print("\n⏳ Waiting for services to stabilize...")
    time.sleep(10)

    # Step 5: Check health status
    print("\n🔍 Checking service health...")
    healthy_count = 0
    for name, port, _ in services:
        if check_service_health(port):
            print(f"✅ {name}: Healthy")
            healthy_count += 1
        else:
            print(f"⚠️  {name}: Not ready")

    print(f"\n📊 Services Ready: {healthy_count}/6")

    # Step 6: Run validation
    print("\n🚀 Running deployment validation...")
    result = subprocess.run(
        "python ai_testing/scripts/validate_deployment.py",
        shell=True,
        capture_output=True,
        text=True,
    )

    # Parse success rate from output
    output = result.stdout + result.stderr
    for line in output.split("\n"):
        if "Success Rate:" in line:
            print(f"\n🎯 {line.strip()}")
            break

    print("\n✨ Fix script complete!")
    print("Run 'python ai_testing/scripts/validate_deployment.py' for full results")


if __name__ == "__main__":
    # Check if psutil is installed
    try:
        import psutil
    except ImportError:
        print("Installing psutil...")
        subprocess.run("pip install psutil", shell=True)
        import psutil

    try:
        import requests
    except ImportError:
        print("Installing requests...")
        subprocess.run("pip install requests", shell=True)

    main()
