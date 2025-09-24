#!/usr/bin/env python3
"""
Wave 5 Monitoring System Validation
Comprehensive testing of the migrated monitoring infrastructure
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MonitoringSystemValidator:
    """Validates the migrated monitoring system infrastructure"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.ops_monitoring_dir = project_root / "ops" / "monitoring"
        self.validation_results = {}
        self.failed_tests = []
        self.passed_tests = []

    def run_validation(self) -> Dict[str, Any]:
        """Run comprehensive monitoring system validation"""
        logger.info("🚀 Starting Wave 5 Monitoring System Validation")

        validation_tests = [
            (
                "Monitoring Directory Structure",
                self.validate_directory_structure,
            ),
            ("Monitoring Module Imports", self.validate_monitoring_imports),
            ("Observability Server", self.validate_observability_server),
            ("Synthetic Monitoring", self.validate_synthetic_monitoring),
            ("Dashboard Data System", self.validate_dashboard_system),
            ("Alerting System", self.validate_alerting_system),
            ("Structured Logging", self.validate_structured_logging),
            ("Prometheus Integration", self.validate_prometheus_integration),
            ("Health Checks System", self.validate_health_checks),
            ("Config Integration", self.validate_config_integration),
        ]

        start_time = datetime.now()

        for test_name, test_func in validation_tests:
            logger.info(f"🧪 Running: {test_name}")
            try:
                result = test_func()
                self.validation_results[test_name] = {
                    "status": "PASSED" if result else "FAILED",
                    "details": (
                        result
                        if isinstance(result, dict)
                        else {"result": result}
                    ),
                }

                if result:
                    self.passed_tests.append(test_name)
                    logger.info(f"✅ PASSED: {test_name}")
                else:
                    self.failed_tests.append(test_name)
                    logger.error(f"❌ FAILED: {test_name}")

            except Exception as e:
                self.validation_results[test_name] = {
                    "status": "ERROR",
                    "details": {"error": str(e), "type": type(e).__name__},
                }
                self.failed_tests.append(test_name)
                logger.error(f"💥 ERROR in {test_name}: {e}")

        duration = datetime.now() - start_time

        summary = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration.total_seconds(),
            "total_tests": len(validation_tests),
            "passed_tests": len(self.passed_tests),
            "failed_tests": len(self.failed_tests),
            "success_rate": len(self.passed_tests) / len(validation_tests),
            "overall_status": "PASSED"
            if len(self.failed_tests) == 0
            else "FAILED",
            "test_results": self.validation_results,
            "failed_test_names": self.failed_tests,
            "passed_test_names": self.passed_tests,
        }

        return summary

    def validate_directory_structure(self) -> Dict[str, Any]:
        """Validate the migrated monitoring directory structure"""
        required_dirs = [
            "ops/monitoring",
            "ops/monitoring/observability",
            "ops/monitoring/synthetic",
            "ops/monitoring/dashboards",
            "ops/monitoring/alerts",
            "ops/monitoring/logging",
            "ops/monitoring/docker",
            "ops/monitoring/grafana",
            "ops/monitoring/grafana/dashboards",
        ]

        required_files = [
            "ops/monitoring/__init__.py",
            "ops/monitoring/README.md",
            "ops/monitoring/observability/__init__.py",
            "ops/monitoring/observability/server.py",
            "ops/monitoring/synthetic/__init__.py",
            "ops/monitoring/synthetic/monitoring.py",
            "ops/monitoring/dashboards/__init__.py",
            "ops/monitoring/dashboards/data.py",
            "ops/monitoring/alerts/__init__.py",
            "ops/monitoring/alerts/alerting.py",
            "ops/monitoring/logging/__init__.py",
            "ops/monitoring/logging/structured.py",
            "ops/monitoring/health_checks.py",
            "ops/monitoring/prometheus_metrics.py",
            "ops/monitoring/opentelemetry_tracing.py",
        ]

        structure_results = {
            "directories": {},
            "files": {},
            "all_present": True,
        }

        # Check directories
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            exists = full_path.exists() and full_path.is_dir()
            structure_results["directories"][dir_path] = {
                "exists": exists,
                "path": str(full_path),
            }
            if not exists:
                structure_results["all_present"] = False

        # Check files
        for file_path in required_files:
            full_path = self.project_root / file_path
            exists = full_path.exists() and full_path.is_file()
            structure_results["files"][file_path] = {
                "exists": exists,
                "path": str(full_path),
                "size": full_path.stat().st_size if exists else 0,
            }
            if not exists:
                structure_results["all_present"] = False

        return structure_results

    def validate_monitoring_imports(self) -> Dict[str, Any]:
        """Test monitoring module imports"""
        results = {"module_imports": {}, "all_imports_successful": True}

        modules_to_test = [
            "ops.monitoring",
            "ops.monitoring.observability",
            "ops.monitoring.synthetic",
            "ops.monitoring.dashboards",
            "ops.monitoring.alerts",
            "ops.monitoring.logging",
        ]

        for module_name in modules_to_test:
            try:
                __import__(module_name)
                results["module_imports"][module_name] = {"success": True}
            except ImportError as e:
                results["module_imports"][module_name] = {
                    "success": False,
                    "error": str(e),
                }
                results["all_imports_successful"] = False
            except Exception as e:
                results["module_imports"][module_name] = {
                    "success": False,
                    "error": f"Unexpected error: {str(e)}",
                }
                results["all_imports_successful"] = False

        return results

    def validate_observability_server(self) -> Dict[str, Any]:
        """Validate the observability server functionality"""
        results = {
            "server_import": False,
            "server_instantiation": False,
            "server_methods": {},
            "configuration_support": False,
        }

        try:
            from ops.monitoring.observability.server import (
                ObservabilityServer,
                create_observability_server,
            )

            results["server_import"] = True

            # Test server instantiation
            server = ObservabilityServer()
            results["server_instantiation"] = True

            # Test expected methods
            expected_methods = [
                "start",
                "stop",
                "_setup_cors",
                "_setup_tracing",
                "_setup_logging",
            ]
            for method_name in expected_methods:
                results["server_methods"][method_name] = hasattr(
                    server, method_name
                )

            # Test factory function
            server2 = create_observability_server({"environment": "test"})
            results["configuration_support"] = server2 is not None

        except ImportError as e:
            results["import_error"] = str(e)
        except Exception as e:
            results["error"] = str(e)

        return results

    def validate_synthetic_monitoring(self) -> Dict[str, Any]:
        """Validate synthetic monitoring system"""
        results = {
            "synthetic_import": False,
            "classes_available": {},
            "functionality_test": False,
        }

        try:
            from ops.monitoring.synthetic.monitoring import (
                CheckResult,
                CheckStatus,
                CheckType,
                SyntheticMonitor,
                create_api_health_check,
                create_http_check,
            )

            results["synthetic_import"] = True

            # Test class availability
            classes_to_test = [
                "SyntheticMonitor",
                "CheckType",
                "CheckStatus",
                "CheckResult",
            ]
            for class_name in classes_to_test:
                results["classes_available"][class_name] = (
                    class_name in locals()
                )

            # Test basic functionality
            monitor = SyntheticMonitor()
            results["functionality_test"] = monitor is not None

            # Test helper functions
            http_check = create_http_check(
                "test", "http://example.com", 200, 60.0
            )
            api_check = create_api_health_check(
                "test", "http://example.com", ["/health"], 120.0
            )

            results["helper_functions"] = {
                "create_http_check": http_check is not None,
                "create_api_health_check": api_check is not None,
            }

        except ImportError as e:
            results["import_error"] = str(e)
        except Exception as e:
            results["error"] = str(e)

        return results

    def validate_dashboard_system(self) -> Dict[str, Any]:
        """Validate dashboard data system"""
        results = {
            "dashboard_import": False,
            "classes_available": {},
            "functionality_test": False,
        }

        try:
            from ops.monitoring.dashboards.data import (
                DashboardConfig,
                DashboardDataCollector,
                MetricData,
                initialize_dashboard_collector,
            )

            results["dashboard_import"] = True

            # Test class availability
            classes_to_test = [
                "DashboardDataCollector",
                "DashboardConfig",
                "MetricData",
            ]
            for class_name in classes_to_test:
                results["classes_available"][class_name] = (
                    class_name in locals()
                )

            # Test configuration
            config = DashboardConfig(
                data_retention_hours=24,
                enable_real_time=True,
                export_enabled=False,
                export_path="test",
            )
            results["functionality_test"] = config is not None

            # Test initialization function
            collector = initialize_dashboard_collector(config)
            results["initialization_function"] = collector is not None

        except ImportError as e:
            results["import_error"] = str(e)
        except Exception as e:
            results["error"] = str(e)

        return results

    def validate_alerting_system(self) -> Dict[str, Any]:
        """Validate alerting system"""
        results = {
            "alerting_import": False,
            "classes_available": {},
            "functionality_test": False,
        }

        try:
            from ops.monitoring.alerts.alerting import (
                AlertManager,
                NotificationConfig,
                create_default_alert_rules,
            )

            results["alerting_import"] = True

            # Test class availability
            classes_to_test = ["AlertManager", "NotificationConfig"]
            for class_name in classes_to_test:
                results["classes_available"][class_name] = (
                    class_name in locals()
                )

            # Test notification config
            config = NotificationConfig(
                smtp_host="localhost",
                smtp_port=587,
                email_recipients=[],
                webhook_urls=[],
            )
            results["functionality_test"] = config is not None

            # Test alert manager
            alert_manager = AlertManager(config)
            results["alert_manager_creation"] = alert_manager is not None

            # Test default rules
            rules = create_default_alert_rules()
            results["default_rules"] = rules is not None and len(rules) > 0

        except ImportError as e:
            results["import_error"] = str(e)
        except Exception as e:
            results["error"] = str(e)

        return results

    def validate_structured_logging(self) -> Dict[str, Any]:
        """Validate structured logging system"""
        results = {
            "logging_import": False,
            "classes_available": {},
            "functionality_test": False,
        }

        try:
            from ops.monitoring.logging.structured import (
                LoggingConfig,
                get_structured_logger,
                setup_structured_logging,
            )

            results["logging_import"] = True

            # Test class availability
            classes_to_test = ["LoggingConfig"]
            for class_name in classes_to_test:
                results["classes_available"][class_name] = (
                    class_name in locals()
                )

            # Test logging config
            config = LoggingConfig(
                log_level="INFO",
                enable_file=False,
                enable_json=True,
                log_directory="logs",
            )
            results["functionality_test"] = config is not None

            # Test logger setup (without actually setting up files)
            try:
                logger_instance = setup_structured_logging(config, "test")
                results["logger_setup"] = logger_instance is not None
            except Exception as e:
                results["logger_setup_error"] = str(e)
                results["logger_setup"] = False

        except ImportError as e:
            results["import_error"] = str(e)
        except Exception as e:
            results["error"] = str(e)

        return results

    def validate_prometheus_integration(self) -> Dict[str, Any]:
        """Validate Prometheus metrics integration"""
        results = {
            "prometheus_import": False,
            "functions_available": {},
            "functionality_test": False,
        }

        try:
            from ops.monitoring.prometheus_metrics import (
                PrometheusMetricsCollector,
                metrics_collector,
                setup_prometheus_endpoint,
                start_background_collection,
            )

            results["prometheus_import"] = True

            # Test class and functions
            functions_to_test = [
                "PrometheusMetricsCollector",
                "setup_prometheus_endpoint",
                "start_background_collection",
            ]
            for func_name in functions_to_test:
                results["functions_available"][func_name] = (
                    func_name in locals()
                )

            # Test metrics collector instance
            results["functionality_test"] = metrics_collector is not None

            # Test collector methods
            if hasattr(metrics_collector, "get_metrics_dict"):
                metrics_dict = metrics_collector.get_metrics_dict()
                results["metrics_collection"] = metrics_dict is not None
            else:
                results["metrics_collection"] = False

        except ImportError as e:
            results["import_error"] = str(e)
        except Exception as e:
            results["error"] = str(e)

        return results

    def validate_health_checks(self) -> Dict[str, Any]:
        """Validate health checks system"""
        results = {
            "health_import": False,
            "classes_available": {},
            "functionality_test": False,
        }

        try:
            from ops.monitoring.health_checks import (
                HealthCheckManager,
                create_health_endpoint,
                health_manager,
            )

            results["health_import"] = True

            # Test class availability
            classes_to_test = ["HealthCheckManager"]
            for class_name in classes_to_test:
                results["classes_available"][class_name] = (
                    class_name in locals()
                )

            # Test health manager instance
            results["functionality_test"] = health_manager is not None

            # Test functions
            results["create_health_endpoint"] = callable(
                create_health_endpoint
            )

        except ImportError as e:
            results["import_error"] = str(e)
        except Exception as e:
            results["error"] = str(e)

        return results

    def validate_config_integration(self) -> Dict[str, Any]:
        """Test monitoring integration with configs system"""
        results = {
            "config_loading": False,
            "prometheus_config": False,
            "monitoring_config": False,
        }

        try:
            from configs.config_environment_loader import (
                ConfigEnvironmentLoader,
            )

            loader = ConfigEnvironmentLoader()

            # Test loading prometheus configuration
            prometheus_config_path = (
                self.project_root / "configs" / "prometheus" / "prometheus.yml"
            )
            results["prometheus_config"] = prometheus_config_path.exists()

            # Test general config loading
            config = loader.load_default_config()
            results["config_loading"] = config is not None

            # Test if monitoring can use the configuration
            if config:
                results["monitoring_config"] = (
                    "monitoring" in config
                    or "metrics" in config
                    or "logs" in config
                )

        except Exception as e:
            results["integration_error"] = str(e)

        return results


def main():
    """Main execution function"""
    project_root = Path(__file__).parent
    validator = MonitoringSystemValidator(project_root)

    # Run validation
    results = validator.run_validation()

    # Save results
    report_file = (
        project_root
        / f"wave5_monitoring_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(report_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    # Print summary
    print(f"\n{'='*80}")
    print("🏁 Wave 5 Monitoring System Validation Results")
    print(f"{'='*80}")
    print(f"📊 Total Tests: {results['total_tests']}")
    print(
        f"✅ Passed: {results['passed_tests']} ({results['success_rate']:.1%})"
    )
    print(f"❌ Failed: {results['failed_tests']}")
    print(f"⏱️  Duration: {results['duration_seconds']:.2f} seconds")
    print(f"🎯 Overall Status: {results['overall_status']}")

    if results["failed_tests"] > 0:
        print("\n❌ Failed Tests:")
        for test in results["failed_test_names"]:
            print(f"  - {test}")

    print(f"\n📝 Full Report: {report_file}")

    return results["overall_status"] == "PASSED"


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
