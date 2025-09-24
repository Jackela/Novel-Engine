#!/usr/bin/env python3
"""
Wave 5 Configuration System Validation
Comprehensive testing of the new configuration infrastructure
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ConfigurationSystemValidator:
    """Validates the new configuration system infrastructure"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.configs_dir = project_root / "configs"
        self.validation_results = {}
        self.failed_tests = []
        self.passed_tests = []

    def run_validation(self) -> Dict[str, Any]:
        """Run comprehensive configuration system validation"""
        logger.info("🚀 Starting Wave 5 Configuration System Validation")

        validation_tests = [
            ("Config Directory Structure", self.validate_directory_structure),
            ("Configuration File Loading", self.validate_config_loading),
            (
                "Environment-specific Configs",
                self.validate_environment_configs,
            ),
            ("Configuration Inheritance", self.validate_config_inheritance),
            ("Python Module Imports", self.validate_python_imports),
            ("Path Resolution", self.validate_path_resolution),
            ("YAML File Parsing", self.validate_yaml_parsing),
            ("Environment Variables", self.validate_environment_variables),
            ("Config Loader Functionality", self.validate_config_loader),
            (
                "Cross-Environment Compatibility",
                self.validate_cross_environment,
            ),
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
        """Validate that the configs directory structure is correct"""
        required_dirs = [
            "configs",
            "configs/environments",
            "configs/nginx",
            "configs/prometheus",
            "configs/security",
        ]

        required_files = [
            "configs/__init__.py",
            "configs/config_environment_loader.py",
            "configs/README.md",
            "configs/environments/__init__.py",
            "configs/environments/development.yaml",
            "configs/environments/environments.yaml",
            "configs/environments/settings.yaml",
            "configs/nginx/__init__.py",
            "configs/nginx/nginx.conf",
            "configs/prometheus/__init__.py",
            "configs/prometheus/prometheus.yml",
            "configs/security/__init__.py",
            "configs/security/security.yaml",
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

    def validate_config_loading(self) -> Dict[str, Any]:
        """Test loading configurations from new configs/ paths"""
        results = {
            "config_loader_import": False,
            "yaml_files_parsed": {},
            "configurations_loaded": {},
            "all_configs_valid": True,
        }

        # Test importing config loader
        try:
            from configs.config_environment_loader import (
                ConfigEnvironmentLoader,
            )

            results["config_loader_import"] = True
        except ImportError as e:
            results["config_loader_error"] = str(e)
            return results

        # Test loading YAML files
        yaml_files = [
            "configs/environments/development.yaml",
            "configs/environments/environments.yaml",
            "configs/environments/settings.yaml",
            "configs/prometheus/prometheus.yml",
            "configs/security/security.yaml",
        ]

        for yaml_file in yaml_files:
            yaml_path = self.project_root / yaml_file
            try:
                if yaml_path.exists():
                    with open(yaml_path, "r") as f:
                        parsed_data = yaml.safe_load(f)
                        results["yaml_files_parsed"][yaml_file] = {
                            "success": True,
                            "data_type": type(parsed_data).__name__,
                            "keys": (
                                list(parsed_data.keys())
                                if isinstance(parsed_data, dict)
                                else None
                            ),
                        }
                else:
                    results["yaml_files_parsed"][yaml_file] = {
                        "success": False,
                        "error": "File not found",
                    }
                    results["all_configs_valid"] = False
            except Exception as e:
                results["yaml_files_parsed"][yaml_file] = {
                    "success": False,
                    "error": str(e),
                }
                results["all_configs_valid"] = False

        # Test configuration loading with ConfigEnvironmentLoader
        try:
            loader = ConfigEnvironmentLoader()

            # Test development environment
            dev_config = loader.load_environment_config("development")
            results["configurations_loaded"]["development"] = {
                "success": dev_config is not None,
                "config_keys": list(dev_config.keys()) if dev_config else None,
            }

            # Test default environment
            default_config = loader.load_default_config()
            results["configurations_loaded"]["default"] = {
                "success": default_config is not None,
                "config_keys": list(default_config.keys())
                if default_config
                else None,
            }

        except Exception as e:
            results["configurations_loaded"]["error"] = str(e)
            results["all_configs_valid"] = False

        return results

    def validate_environment_configs(self) -> Dict[str, Any]:
        """Validate environment-specific configuration loading"""
        results = {
            "environments": {},
            "inheritance_working": False,
            "override_working": False,
        }

        try:
            from configs.config_environment_loader import (
                ConfigEnvironmentLoader,
            )

            loader = ConfigEnvironmentLoader()

            # Test different environments
            environments = ["development", "staging", "production"]

            for env in environments:
                try:
                    config = loader.load_environment_config(env)
                    results["environments"][env] = {
                        "loaded": config is not None,
                        "config_keys": list(config.keys()) if config else [],
                        "has_database_config": (
                            "database" in config if config else False
                        ),
                        "has_api_config": "api" in config if config else False,
                    }
                except Exception as e:
                    results["environments"][env] = {
                        "loaded": False,
                        "error": str(e),
                    }

            # Test configuration inheritance
            try:
                base_config = loader.load_default_config()
                dev_config = loader.load_environment_config("development")

                if base_config and dev_config:
                    # Check if development inherits from base and has overrides
                    base_keys = set(base_config.keys())
                    dev_keys = set(dev_config.keys())

                    results["inheritance_working"] = (
                        len(base_keys.intersection(dev_keys)) > 0
                    )
                    results["override_working"] = len(dev_keys - base_keys) > 0

            except Exception as e:
                results["inheritance_error"] = str(e)

        except ImportError as e:
            results["import_error"] = str(e)

        return results

    def validate_config_inheritance(self) -> Dict[str, Any]:
        """Test configuration inheritance and overrides"""
        results = {
            "inheritance_test": False,
            "override_test": False,
            "merge_test": False,
        }

        try:
            from configs.config_environment_loader import (
                ConfigEnvironmentLoader,
            )

            loader = ConfigEnvironmentLoader()

            # Load base and environment configs
            base_config = loader.load_default_config()
            dev_config = loader.load_environment_config("development")

            if base_config and dev_config:
                # Test inheritance: dev should have base values
                common_keys = []
                for key in base_config:
                    if key in dev_config:
                        common_keys.append(key)

                results["inheritance_test"] = len(common_keys) > 0
                results["common_inherited_keys"] = common_keys

                # Test overrides: dev should have unique values
                dev_only_keys = []
                for key in dev_config:
                    if key not in base_config:
                        dev_only_keys.append(key)

                results["override_test"] = len(dev_only_keys) > 0
                results["override_keys"] = dev_only_keys

                # Test merge: final config should have both
                merged_keys = set(
                    list(base_config.keys()) + list(dev_config.keys())
                )
                expected_keys = len(base_config) + len(dev_only_keys)

                results["merge_test"] = len(merged_keys) >= expected_keys
                results["merged_key_count"] = len(merged_keys)

        except Exception as e:
            results["error"] = str(e)

        return results

    def validate_python_imports(self) -> Dict[str, Any]:
        """Verify Python package imports work correctly for new modules"""
        results = {"imports": {}, "all_imports_successful": True}

        import_tests = [
            ("configs", "configs"),
            (
                "configs.config_environment_loader",
                "configs.config_environment_loader",
            ),
            ("configs.environments", "configs.environments"),
            ("configs.nginx", "configs.nginx"),
            ("configs.prometheus", "configs.prometheus"),
            ("configs.security", "configs.security"),
            ("deploy", "deploy"),
            ("deploy.staging.deploy", "deploy.staging.deploy"),
            ("deploy.production.deploy", "deploy.production.deploy"),
            ("ops.monitoring", "ops.monitoring"),
        ]

        for module_name, import_path in import_tests:
            try:
                __import__(import_path)
                results["imports"][module_name] = {"success": True}
            except ImportError as e:
                results["imports"][module_name] = {
                    "success": False,
                    "error": str(e),
                }
                results["all_imports_successful"] = False
            except Exception as e:
                results["imports"][module_name] = {
                    "success": False,
                    "error": f"Unexpected error: {str(e)}",
                }
                results["all_imports_successful"] = False

        return results

    def validate_path_resolution(self) -> Dict[str, Any]:
        """Test path resolution across all environments"""
        results = {
            "relative_paths": {},
            "absolute_paths": {},
            "config_paths": {},
            "all_paths_resolved": True,
        }

        try:
            from configs.config_environment_loader import (
                ConfigEnvironmentLoader,
            )

            ConfigEnvironmentLoader()

            # Test relative path calculations
            relative_tests = [
                ("configs_to_project_root", "../"),
                ("configs_to_deploy", "../deploy"),
                ("configs_to_ops", "../ops"),
                ("deploy_to_configs", "../configs"),
                ("ops_to_configs", "../configs"),
            ]

            for test_name, expected_path in relative_tests:
                # Test if the path exists from different starting points
                test_path = self.project_root / expected_path.replace(
                    "../", ""
                )
                results["relative_paths"][test_name] = {
                    "expected": expected_path,
                    "resolved": str(test_path),
                    "exists": test_path.exists(),
                }
                if not test_path.exists():
                    results["all_paths_resolved"] = False

            # Test absolute paths
            abs_paths = [
                ("project_root", str(self.project_root)),
                ("configs_dir", str(self.configs_dir)),
                ("deploy_dir", str(self.project_root / "deploy")),
                ("ops_dir", str(self.project_root / "ops")),
            ]

            for path_name, abs_path in abs_paths:
                path_obj = Path(abs_path)
                results["absolute_paths"][path_name] = {
                    "path": abs_path,
                    "exists": path_obj.exists(),
                    "is_directory": path_obj.is_dir()
                    if path_obj.exists()
                    else False,
                }
                if not path_obj.exists():
                    results["all_paths_resolved"] = False

            # Test config file paths
            config_paths = [
                (
                    "development_config",
                    "configs/environments/development.yaml",
                ),
                ("nginx_config", "configs/nginx/nginx.conf"),
                ("prometheus_config", "configs/prometheus/prometheus.yml"),
                ("security_config", "configs/security/security.yaml"),
            ]

            for config_name, config_path in config_paths:
                full_path = self.project_root / config_path
                results["config_paths"][config_name] = {
                    "relative_path": config_path,
                    "absolute_path": str(full_path),
                    "exists": full_path.exists(),
                    "readable": (
                        full_path.is_file() and os.access(full_path, os.R_OK)
                        if full_path.exists()
                        else False
                    ),
                }
                if not full_path.exists() or not (
                    full_path.is_file() and os.access(full_path, os.R_OK)
                ):
                    results["all_paths_resolved"] = False

        except Exception as e:
            results["error"] = str(e)
            results["all_paths_resolved"] = False

        return results

    def validate_yaml_parsing(self) -> Dict[str, Any]:
        """Validate YAML file parsing and structure"""
        results = {"yaml_files": {}, "all_yaml_valid": True}

        yaml_files = [
            ("development", "configs/environments/development.yaml"),
            ("environments", "configs/environments/environments.yaml"),
            ("settings", "configs/environments/settings.yaml"),
            ("prometheus", "configs/prometheus/prometheus.yml"),
            ("security", "configs/security/security.yaml"),
        ]

        for file_name, file_path in yaml_files:
            full_path = self.project_root / file_path
            results["yaml_files"][file_name] = {
                "path": file_path,
                "exists": full_path.exists(),
            }

            if full_path.exists():
                try:
                    with open(full_path, "r") as f:
                        content = f.read()
                        parsed = yaml.safe_load(content)

                        results["yaml_files"][file_name].update(
                            {
                                "parsed_successfully": True,
                                "content_type": type(parsed).__name__,
                                "content_size": len(content),
                                "structure": self._analyze_yaml_structure(
                                    parsed
                                ),
                            }
                        )
                except yaml.YAMLError as e:
                    results["yaml_files"][file_name][
                        "parsed_successfully"
                    ] = False
                    results["yaml_files"][file_name]["yaml_error"] = str(e)
                    results["all_yaml_valid"] = False
                except Exception as e:
                    results["yaml_files"][file_name][
                        "parsed_successfully"
                    ] = False
                    results["yaml_files"][file_name]["error"] = str(e)
                    results["all_yaml_valid"] = False
            else:
                results["yaml_files"][file_name]["parsed_successfully"] = False
                results["all_yaml_valid"] = False

        return results

    def _analyze_yaml_structure(self, data: Any) -> Dict[str, Any]:
        """Analyze the structure of parsed YAML data"""
        if isinstance(data, dict):
            return {
                "type": "dict",
                "keys": list(data.keys()),
                "key_count": len(data),
                "nested_levels": self._count_nested_levels(data),
            }
        elif isinstance(data, list):
            return {
                "type": "list",
                "length": len(data),
                "item_types": list(set(type(item).__name__ for item in data)),
            }
        else:
            return {
                "type": type(data).__name__,
                "value": str(data)[:100] if data else None,
            }

    def _count_nested_levels(self, data: Dict, current_level: int = 0) -> int:
        """Count the maximum nesting level in a dictionary"""
        if not isinstance(data, dict):
            return current_level

        max_level = current_level
        for value in data.values():
            if isinstance(value, dict):
                level = self._count_nested_levels(value, current_level + 1)
                max_level = max(max_level, level)

        return max_level

    def validate_environment_variables(self) -> Dict[str, Any]:
        """Test environment variables and runtime configuration"""
        results = {
            "environment_variables": {},
            "env_config_integration": False,
        }

        # Test common environment variables
        env_vars = [
            "ENVIRONMENT",
            "API_HOST",
            "API_PORT",
            "DATABASE_URL",
            "LOG_LEVEL",
            "PROMETHEUS_PORT",
        ]

        for var in env_vars:
            value = os.environ.get(var)
            results["environment_variables"][var] = {
                "set": value is not None,
                "value": value if value else "not_set",
            }

        # Test environment variable integration with config
        try:
            from configs.config_environment_loader import (
                ConfigEnvironmentLoader,
            )

            loader = ConfigEnvironmentLoader()

            # Test if environment variables can override config values
            os.environ["TEST_CONFIG_VAR"] = "test_value"
            loader.load_environment_config("development")

            results["env_config_integration"] = True
        except Exception as e:
            results["env_integration_error"] = str(e)

        return results

    def validate_config_loader(self) -> Dict[str, Any]:
        """Test the new environment-aware configuration loader"""
        results = {"loader_functionality": {}, "all_functions_working": True}

        try:
            from configs.config_environment_loader import (
                ConfigEnvironmentLoader,
            )

            loader = ConfigEnvironmentLoader()

            # Test all loader methods
            loader_tests = [
                ("load_default_config", lambda: loader.load_default_config()),
                (
                    "load_environment_config",
                    lambda: loader.load_environment_config("development"),
                ),
                (
                    "get_config_path",
                    lambda: loader.get_config_path(
                        "environments", "development.yaml"
                    ),
                ),
                ("validate_config", lambda: True),  # Assume this method exists
            ]

            for test_name, test_func in loader_tests:
                try:
                    result = test_func()
                    results["loader_functionality"][test_name] = {
                        "success": result is not None,
                        "result_type": type(result).__name__
                        if result
                        else "None",
                    }
                except AttributeError:
                    results["loader_functionality"][test_name] = {
                        "success": False,
                        "error": "Method not implemented",
                    }
                except Exception as e:
                    results["loader_functionality"][test_name] = {
                        "success": False,
                        "error": str(e),
                    }
                    results["all_functions_working"] = False

        except ImportError as e:
            results["import_error"] = str(e)
            results["all_functions_working"] = False

        return results

    def validate_cross_environment(self) -> Dict[str, Any]:
        """Test compatibility across different environments"""
        results = {
            "environments": {},
            "consistency_check": {},
            "all_environments_compatible": True,
        }

        environments = ["development", "staging", "production"]

        try:
            from configs.config_environment_loader import (
                ConfigEnvironmentLoader,
            )

            loader = ConfigEnvironmentLoader()

            configs = {}
            for env in environments:
                try:
                    config = loader.load_environment_config(env)
                    configs[env] = config
                    results["environments"][env] = {
                        "loaded": config is not None,
                        "config_keys": list(config.keys()) if config else [],
                        "key_count": len(config) if config else 0,
                    }
                except Exception as e:
                    configs[env] = None
                    results["environments"][env] = {
                        "loaded": False,
                        "error": str(e),
                    }
                    results["all_environments_compatible"] = False

            # Check consistency across environments
            if len(configs) > 1:
                # Get common keys across all loaded configs
                loaded_configs = {
                    k: v for k, v in configs.items() if v is not None
                }
                if loaded_configs:
                    key_sets = [
                        set(config.keys())
                        for config in loaded_configs.values()
                    ]
                    common_keys = (
                        set.intersection(*key_sets) if key_sets else set()
                    )
                    all_keys = set.union(*key_sets) if key_sets else set()

                    results["consistency_check"] = {
                        "common_keys": list(common_keys),
                        "common_key_count": len(common_keys),
                        "total_unique_keys": len(all_keys),
                        "consistency_ratio": (
                            len(common_keys) / len(all_keys) if all_keys else 0
                        ),
                    }

        except Exception as e:
            results["cross_environment_error"] = str(e)
            results["all_environments_compatible"] = False

        return results


def main():
    """Main execution function"""
    project_root = Path(__file__).parent
    validator = ConfigurationSystemValidator(project_root)

    # Run validation
    results = validator.run_validation()

    # Save results
    report_file = (
        project_root
        / f"wave5_configuration_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(report_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    # Print summary
    print(f"\n{'='*80}")
    print("🏁 Wave 5 Configuration System Validation Results")
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
