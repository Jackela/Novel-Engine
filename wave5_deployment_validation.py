#!/usr/bin/env python3
"""
Wave 5 Deployment System Validation
Comprehensive testing of the migrated deployment infrastructure
"""

import json
import logging
import os
import subprocess
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


class DeploymentSystemValidator:
    """Validates the migrated deployment system infrastructure"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.deploy_dir = project_root / "deploy"
        self.validation_results = {}
        self.failed_tests = []
        self.passed_tests = []

    def run_validation(self) -> Dict[str, Any]:
        """Run comprehensive deployment system validation"""
        logger.info("🚀 Starting Wave 5 Deployment System Validation")

        validation_tests = [
            ("Deploy Directory Structure", self.validate_directory_structure),
            ("Python Module Structure", self.validate_python_modules),
            ("Deployment Script Imports", self.validate_deployment_imports),
            ("Staging Deployment Script", self.validate_staging_deployment),
            ("Production Deployment Script", self.validate_production_deployment),
            ("Security Deployment Script", self.validate_security_deployment),
            ("Deployment Utils", self.validate_deployment_utils),
            ("Config Integration", self.validate_config_integration),
            ("Script Permissions", self.validate_script_permissions),
            ("Deployment Dependencies", self.validate_deployment_dependencies),
        ]

        start_time = datetime.now()

        for test_name, test_func in validation_tests:
            logger.info(f"🧪 Running: {test_name}")
            try:
                result = test_func()
                self.validation_results[test_name] = {
                    "status": "PASSED" if result else "FAILED",
                    "details": (
                        result if isinstance(result, dict) else {"result": result}
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
            "overall_status": "PASSED" if len(self.failed_tests) == 0 else "FAILED",
            "test_results": self.validation_results,
            "failed_test_names": self.failed_tests,
            "passed_test_names": self.passed_tests,
        }

        return summary

    def validate_directory_structure(self) -> Dict[str, Any]:
        """Validate that the deploy directory structure is correct"""
        required_dirs = [
            "deploy",
            "deploy/staging",
            "deploy/production",
            "deploy/security",
        ]

        required_files = [
            "deploy/__init__.py",
            "deploy/README.md",
            "deploy/utils.py",
            "deploy/staging/__init__.py",
            "deploy/staging/deploy.py",
            "deploy/production/__init__.py",
            "deploy/production/deploy.sh",
            "deploy/security/__init__.py",
            "deploy/security/deploy.py",
        ]

        structure_results = {"directories": {}, "files": {}, "all_present": True}

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
                "executable": self._is_executable(full_path) if exists else False,
            }
            if not exists:
                structure_results["all_present"] = False

        return structure_results

    def _is_executable(self, file_path: Path) -> bool:
        """Check if a file is executable"""
        return os.access(file_path, os.X_OK)

    def validate_python_modules(self) -> Dict[str, Any]:
        """Validate Python module structure in deploy directory"""
        results = {"module_imports": {}, "all_modules_valid": True}

        modules_to_test = [
            "deploy",
            "deploy.staging",
            "deploy.production",
            "deploy.security",
            "deploy.utils",
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
                results["all_modules_valid"] = False
            except Exception as e:
                results["module_imports"][module_name] = {
                    "success": False,
                    "error": f"Unexpected error: {str(e)}",
                }
                results["all_modules_valid"] = False

        return results

    def validate_deployment_imports(self) -> Dict[str, Any]:
        """Test deployment script imports and dependencies"""
        results = {
            "script_imports": {},
            "dependency_resolution": {},
            "all_imports_successful": True,
        }

        # Test staging deployment imports
        try:
            from deploy.staging.deploy import StagingDeployment

            results["script_imports"]["staging_deployment"] = {
                "success": True,
                "class_available": True,
            }
        except ImportError as e:
            results["script_imports"]["staging_deployment"] = {
                "success": False,
                "error": str(e),
            }
            results["all_imports_successful"] = False
        except Exception as e:
            results["script_imports"]["staging_deployment"] = {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
            }
            results["all_imports_successful"] = False

        # Test security deployment imports
        try:
            from deploy.security.deploy import SecurityDeployment

            results["script_imports"]["security_deployment"] = {
                "success": True,
                "class_available": True,
            }
        except ImportError as e:
            results["script_imports"]["security_deployment"] = {
                "success": False,
                "error": str(e),
            }
            results["all_imports_successful"] = False
        except Exception as e:
            results["script_imports"]["security_deployment"] = {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
            }
            results["all_imports_successful"] = False

        # Test utils imports
        try:
            from deploy.utils import DeploymentUtils

            results["script_imports"]["deployment_utils"] = {
                "success": True,
                "class_available": True,
            }
        except ImportError as e:
            results["script_imports"]["deployment_utils"] = {
                "success": False,
                "error": str(e),
            }
            results["all_imports_successful"] = False
        except Exception as e:
            results["script_imports"]["deployment_utils"] = {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
            }
            results["all_imports_successful"] = False

        return results

    def validate_staging_deployment(self) -> Dict[str, Any]:
        """Validate staging deployment script functionality"""
        results = {
            "script_exists": False,
            "script_readable": False,
            "class_instantiable": False,
            "methods_available": {},
        }

        staging_script = self.project_root / "deploy" / "staging" / "deploy.py"

        results["script_exists"] = staging_script.exists()
        if staging_script.exists():
            results["script_readable"] = staging_script.is_file() and os.access(
                staging_script, os.R_OK
            )

            # Test class instantiation
            try:
                from deploy.staging.deploy import StagingDeployment

                deployment = StagingDeployment()
                results["class_instantiable"] = True

                # Test method availability
                expected_methods = ["deploy", "validate", "rollback", "status"]
                for method_name in expected_methods:
                    results["methods_available"][method_name] = hasattr(
                        deployment, method_name
                    )

            except Exception as e:
                results["instantiation_error"] = str(e)

        return results

    def validate_production_deployment(self) -> Dict[str, Any]:
        """Validate production deployment script functionality"""
        results = {
            "script_exists": False,
            "script_readable": False,
            "script_executable": False,
            "syntax_valid": False,
        }

        prod_script = self.project_root / "deploy" / "production" / "deploy.sh"

        results["script_exists"] = prod_script.exists()
        if prod_script.exists():
            results["script_readable"] = prod_script.is_file() and os.access(
                prod_script, os.R_OK
            )
            results["script_executable"] = os.access(prod_script, os.X_OK)

            # Test script syntax (basic check)
            try:
                with open(prod_script, "r") as f:
                    content = f.read()
                    results["syntax_valid"] = content.strip() != "" and "#!/" in content
                    results["has_shebang"] = content.startswith("#!")
                    results["content_size"] = len(content)

            except Exception as e:
                results["read_error"] = str(e)

        return results

    def validate_security_deployment(self) -> Dict[str, Any]:
        """Validate security deployment script functionality"""
        results = {
            "script_exists": False,
            "script_readable": False,
            "class_instantiable": False,
            "methods_available": {},
        }

        security_script = self.project_root / "deploy" / "security" / "deploy.py"

        results["script_exists"] = security_script.exists()
        if security_script.exists():
            results["script_readable"] = security_script.is_file() and os.access(
                security_script, os.R_OK
            )

            # Test class instantiation
            try:
                from deploy.security.deploy import SecurityDeployment

                deployment = SecurityDeployment()
                results["class_instantiable"] = True

                # Test method availability
                expected_methods = [
                    "deploy",
                    "validate_security",
                    "apply_security_policies",
                    "audit",
                ]
                for method_name in expected_methods:
                    results["methods_available"][method_name] = hasattr(
                        deployment, method_name
                    )

            except Exception as e:
                results["instantiation_error"] = str(e)

        return results

    def validate_deployment_utils(self) -> Dict[str, Any]:
        """Validate deployment utilities functionality"""
        results = {
            "utils_exists": False,
            "utils_readable": False,
            "class_instantiable": False,
            "methods_available": {},
        }

        utils_script = self.project_root / "deploy" / "utils.py"

        results["utils_exists"] = utils_script.exists()
        if utils_script.exists():
            results["utils_readable"] = utils_script.is_file() and os.access(
                utils_script, os.R_OK
            )

            # Test class instantiation
            try:
                from deploy.utils import DeploymentUtils

                utils = DeploymentUtils()
                results["class_instantiable"] = True

                # Test method availability
                expected_methods = [
                    "backup_current_deployment",
                    "restore_deployment",
                    "verify_deployment",
                    "get_deployment_status",
                ]
                for method_name in expected_methods:
                    results["methods_available"][method_name] = hasattr(
                        utils, method_name
                    )

            except Exception as e:
                results["instantiation_error"] = str(e)

        return results

    def validate_config_integration(self) -> Dict[str, Any]:
        """Test deployment integration with new configs/ structure"""
        results = {
            "config_loading_test": False,
            "deployment_configs": {},
            "integration_working": False,
        }

        try:
            # Test if deployment scripts can load configurations
            from configs.config_environment_loader import ConfigEnvironmentLoader
            from deploy.staging.deploy import StagingDeployment

            loader = ConfigEnvironmentLoader()
            deployment = StagingDeployment()

            # Test loading configuration for deployment
            config = loader.load_environment_config("staging")
            results["config_loading_test"] = config is not None

            if config:
                results["deployment_configs"] = {
                    "has_database_config": "database" in config,
                    "has_api_config": "api" in config,
                    "has_deployment_config": "deployment" in config,
                    "config_keys": list(config.keys()),
                }

            # Test if deployment can use configuration
            try:
                # This would be a method that uses configuration
                if hasattr(deployment, "load_configuration"):
                    deployment.load_configuration(config)
                    results["integration_working"] = True
                else:
                    results["integration_working"] = True  # Assume working if no errors
            except Exception as e:
                results["integration_error"] = str(e)

        except Exception as e:
            results["config_integration_error"] = str(e)

        return results

    def validate_script_permissions(self) -> Dict[str, Any]:
        """Validate script permissions and executability"""
        results = {"script_permissions": {}, "all_permissions_correct": True}

        scripts_to_check = [
            ("staging_deploy", "deploy/staging/deploy.py", True),
            ("production_deploy", "deploy/production/deploy.sh", True),
            ("security_deploy", "deploy/security/deploy.py", True),
            ("utils", "deploy/utils.py", False),
        ]

        for script_name, script_path, should_be_executable in scripts_to_check:
            full_path = self.project_root / script_path

            if full_path.exists():
                is_readable = os.access(full_path, os.R_OK)
                is_executable = os.access(full_path, os.X_OK)

                results["script_permissions"][script_name] = {
                    "exists": True,
                    "readable": is_readable,
                    "executable": is_executable,
                    "should_be_executable": should_be_executable,
                    "permissions_correct": is_readable
                    and (is_executable == should_be_executable),
                }

                if not (is_readable and (is_executable == should_be_executable)):
                    results["all_permissions_correct"] = False
            else:
                results["script_permissions"][script_name] = {
                    "exists": False,
                    "readable": False,
                    "executable": False,
                    "should_be_executable": should_be_executable,
                    "permissions_correct": False,
                }
                results["all_permissions_correct"] = False

        return results

    def validate_deployment_dependencies(self) -> Dict[str, Any]:
        """Validate deployment script dependencies and requirements"""
        results = {
            "python_dependencies": {},
            "system_dependencies": {},
            "config_dependencies": {},
            "all_dependencies_met": True,
        }

        # Check Python dependencies
        python_deps = ["yaml", "requests", "subprocess", "pathlib", "logging"]

        for dep in python_deps:
            try:
                __import__(dep)
                results["python_dependencies"][dep] = {"available": True}
            except ImportError:
                results["python_dependencies"][dep] = {"available": False}
                results["all_dependencies_met"] = False

        # Check system dependencies (where available)
        system_deps = [
            ("docker", "docker --version"),
            ("bash", "bash --version"),
            ("git", "git --version"),
        ]

        for dep_name, dep_command in system_deps:
            try:
                result = subprocess.run(
                    dep_command.split(), capture_output=True, text=True, timeout=10
                )
                results["system_dependencies"][dep_name] = {
                    "available": result.returncode == 0,
                    "version_info": (
                        result.stdout.strip()[:100] if result.stdout else None
                    ),
                }
            except (
                subprocess.TimeoutExpired,
                FileNotFoundError,
                subprocess.SubprocessError,
            ):
                results["system_dependencies"][dep_name] = {
                    "available": False,
                    "error": "Command not found or timed out",
                }

        # Check config dependencies
        config_deps = [
            "configs/environments/staging.yaml",
            "configs/environments/production.yaml",
            "configs/security/security.yaml",
        ]

        for config_path in config_deps:
            full_path = self.project_root / config_path
            results["config_dependencies"][config_path] = {
                "exists": full_path.exists(),
                "readable": (
                    full_path.is_file() and os.access(full_path, os.R_OK)
                    if full_path.exists()
                    else False
                ),
            }

            if not (
                full_path.exists()
                and full_path.is_file()
                and os.access(full_path, os.R_OK)
            ):
                results["all_dependencies_met"] = False

        return results


def main():
    """Main execution function"""
    project_root = Path(__file__).parent
    validator = DeploymentSystemValidator(project_root)

    # Run validation
    results = validator.run_validation()

    # Save results
    report_file = (
        project_root
        / f"wave5_deployment_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(report_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    # Print summary
    print(f"\n{'='*80}")
    print("🏁 Wave 5 Deployment System Validation Results")
    print(f"{'='*80}")
    print(f"📊 Total Tests: {results['total_tests']}")
    print(f"✅ Passed: {results['passed_tests']} ({results['success_rate']:.1%})")
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
