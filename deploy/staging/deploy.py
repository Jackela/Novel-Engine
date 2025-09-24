#!/usr/bin/env python3
"""
Novel Engine Staging Deployment Script
======================================

Comprehensive staging deployment automation with health checks,
rollback capabilities, and deployment validation.

This script handles:
1. Pre-deployment validation
2. Staging environment setup
3. Configuration management
4. Service deployment
5. Health verification
6. Rollback preparation

Usage:
    python deploy/staging/deploy.py [--validate-only] [--rollback]
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
import yaml

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("staging/logs/deployment.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class StagingDeployment:
    """Novel Engine staging deployment manager."""

    def __init__(self):
        self.project_root = project_root
        self.staging_dir = project_root / "staging"
        self.deployment_id = (
            f"staging-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )
        self.backup_dir = (
            project_root / "staging" / "backups" / self.deployment_id
        )
        self.health_check_url = "http://localhost:8000/health"

        # Create necessary directories
        self._ensure_directories()

        logger.info(f"🚀 Staging deployment initialized: {self.deployment_id}")

    def _ensure_directories(self):
        """Create necessary staging directories."""
        directories = [
            "staging/logs",
            "staging/private",
            "staging/private/knowledge_base",
            "staging/private/sessions",
            "staging/evaluation",
            "staging/exports",
            "staging/backups",
            "deployment",
        ]

        for directory in directories:
            (self.project_root / directory).mkdir(parents=True, exist_ok=True)

        logger.info("✅ Staging directories created")

    def validate_system(self) -> bool:
        """Run comprehensive system validation."""
        logger.info("🔍 Running system validation...")

        try:
            # 1. Core imports validation
            logger.info("Validating core imports...")
            import_script = """
import sys
import os
sys.path.append(".")
sys.path.insert(0, os.path.abspath("."))

try:
    from director_agent import DirectorAgent
    from src.persona_agent import PersonaAgent
    from src.caching import StateHasher, SemanticCache, TokenBudgetManager
    from src.shared_types import CharacterData, WorldState, ProposedAction
    from api_server import app
    print("✅ All imports successful")
except ImportError as e:
    print(f"Import error: {e}")
    import sys
    sys.exit(1)
"""

            result = subprocess.run(
                [sys.executable, "-c", import_script],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            if result.returncode != 0:
                logger.error(f"❌ Import validation failed: {result.stderr}")
                return False

            logger.info("✅ Core imports validated")

            # 2. Configuration validation
            logger.info("Validating staging configuration...")
            staging_config = self.staging_dir / "settings_staging.yaml"
            if not staging_config.exists():
                logger.error(
                    f"❌ Staging configuration not found: {staging_config}"
                )
                return False

            with open(staging_config) as f:
                config = yaml.safe_load(f)
                if config.get("system", {}).get("environment") != "staging":
                    logger.error(
                        "❌ Configuration not set to staging environment"
                    )
                    return False

            logger.info("✅ Configuration validated")

            # 3. Dependencies check
            logger.info("Validating dependencies...")
            requirements_file = self.project_root / "requirements.txt"
            if requirements_file.exists():
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "check"],
                    capture_output=True,
                    text=True,
                )

                if result.returncode != 0:
                    logger.warning(
                        f"⚠️  Dependency issues detected: {result.stderr}"
                    )

            logger.info("✅ Dependencies checked")

            # 4. Startup guards validation
            logger.info("Running startup validation guards...")
            result = subprocess.run(
                [sys.executable, "scripts/build_kb.py"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            if result.returncode != 0:
                logger.error(f"❌ Startup validation failed: {result.stderr}")
                return False

            logger.info("✅ Startup validation passed")

            return True

        except Exception as e:
            logger.error(f"❌ System validation failed: {e}")
            return False

    def create_backup(self) -> bool:
        """Create backup of current system state."""
        logger.info("📦 Creating system backup...")

        try:
            # Create backup directory
            self.backup_dir.mkdir(parents=True, exist_ok=True)

            # Backup configuration files
            config_files = [
                "configs/environments/development.yaml",
                "configs/environments/settings.yaml",
                "requirements.txt",
            ]

            for config_file in config_files:
                src = self.project_root / config_file
                if src.exists():
                    shutil.copy2(src, self.backup_dir / config_file)
                    logger.info(f"📦 Backed up: {config_file}")

            # Backup critical directories
            critical_dirs = ["private", "logs", "characters"]

            for dir_name in critical_dirs:
                src_dir = self.project_root / dir_name
                if src_dir.exists():
                    dst_dir = self.backup_dir / dir_name
                    try:
                        shutil.copytree(src_dir, dst_dir)
                        logger.info(f"📦 Backed up directory: {dir_name}")
                    except Exception as e:
                        logger.warning(f"⚠️ Partial backup of {dir_name}: {e}")
                        continue

            # Create backup manifest
            manifest = {
                "deployment_id": self.deployment_id,
                "timestamp": datetime.now().isoformat(),
                "backed_up_files": config_files,
                "backed_up_directories": critical_dirs,
                "backup_path": str(self.backup_dir),
            }

            with open(self.backup_dir / "manifest.json", "w") as f:
                json.dump(manifest, f, indent=2)

            logger.info(f"✅ Backup created: {self.backup_dir}")
            return True

        except Exception as e:
            logger.error(f"❌ Backup creation failed: {e}")
            return False

    def deploy_configuration(self) -> bool:
        """Deploy staging configuration."""
        logger.info("⚙️ Deploying staging configuration...")

        try:
            # Copy staging settings to active configuration
            staging_settings = self.staging_dir / "settings_staging.yaml"
            active_settings = (
                self.project_root / "configs/environments/settings.yaml"
            )

            # Backup current settings
            if active_settings.exists():
                shutil.copy2(
                    active_settings, self.backup_dir / "settings_original.yaml"
                )

            # Deploy staging settings
            shutil.copy2(staging_settings, active_settings)
            logger.info("⚙️ Staging configuration deployed")

            # Validate configuration deployment
            with open(active_settings) as f:
                config = yaml.safe_load(f)
                env = config.get("system", {}).get("environment")
                if env != "staging":
                    raise ValueError(
                        f"Configuration deployment failed - environment: {env}"
                    )

            logger.info("✅ Configuration deployment validated")
            return True

        except Exception as e:
            logger.error(f"❌ Configuration deployment failed: {e}")
            return False

    def start_services(self) -> bool:
        """Start Novel Engine services."""
        logger.info("🚀 Starting Novel Engine services...")

        try:
            # Start API server in background
            server_log = self.staging_dir / "logs" / "api_server.log"

            # Use subprocess to start server
            self.server_process = subprocess.Popen(
                [sys.executable, "api_server.py"],
                cwd=self.project_root,
                stdout=open(server_log, "w"),
                stderr=subprocess.STDOUT,
            )

            # Wait for server startup
            logger.info("⏳ Waiting for server startup...")
            time.sleep(10)  # Give server time to start

            # Check if process is still running
            if self.server_process.poll() is not None:
                logger.error("❌ Server process terminated during startup")
                return False

            logger.info("✅ API server started")
            return True

        except Exception as e:
            logger.error(f"❌ Service startup failed: {e}")
            return False

    def run_health_checks(self) -> bool:
        """Run comprehensive health checks."""
        logger.info("🏥 Running health checks...")

        max_attempts = 12  # 2 minutes with 10s intervals
        attempt = 0

        while attempt < max_attempts:
            try:
                # Basic health check
                response = requests.get(
                    self.health_check_url,
                    timeout=5,
                    headers={"User-Agent": "Novel-Engine-Deployment/1.0"},
                )

                if response.status_code == 200:
                    health_data = response.json()
                    logger.info(
                        f"✅ Health check passed: {health_data.get('status', 'unknown')}"
                    )

                    # Extended health checks
                    return self._extended_health_checks()

                logger.warning(
                    f"⚠️ Health check attempt {attempt + 1} failed - Status: {response.status_code}"
                )

            except requests.exceptions.ConnectionError:
                logger.warning(
                    f"⚠️ Health check attempt {attempt + 1} - Connection refused"
                )
            except requests.exceptions.Timeout:
                logger.warning(
                    f"⚠️ Health check attempt {attempt + 1} - Timeout"
                )
            except Exception as e:
                logger.warning(
                    f"⚠️ Health check attempt {attempt + 1} failed: {e}"
                )

            attempt += 1
            if attempt < max_attempts:
                time.sleep(10)

        logger.error("❌ Health checks failed after maximum attempts")
        return False

    def _extended_health_checks(self) -> bool:
        """Run extended health validation."""
        logger.info("🔍 Running extended health checks...")

        try:
            # Test endpoints
            endpoints = [
                "/",
                "/characters",
                "/campaigns",
                "/meta/system-status",
            ]

            base_url = "http://localhost:8000"

            for endpoint in endpoints:
                response = requests.get(f"{base_url}{endpoint}", timeout=10)
                if response.status_code not in [
                    200,
                    404,
                ]:  # 404 acceptable for empty lists
                    logger.warning(
                        f"⚠️ Endpoint {endpoint} returned {response.status_code}"
                    )
                else:
                    logger.info(f"✅ Endpoint {endpoint} responding")

            # Test system status endpoint specifically
            try:
                response = requests.get(
                    f"{base_url}/meta/system-status", timeout=10
                )
                if response.status_code == 200:
                    status_data = response.json()
                    logger.info(f"✅ System status: {status_data}")
                else:
                    logger.warning(
                        f"⚠️ System status endpoint returned {response.status_code}"
                    )
            except Exception as e:
                logger.warning(f"⚠️ System status check failed: {e}")

            logger.info("✅ Extended health checks completed")
            return True

        except Exception as e:
            logger.error(f"❌ Extended health checks failed: {e}")
            return False

    def create_rollback_script(self) -> bool:
        """Create rollback script for easy recovery."""
        logger.info("📜 Creating rollback script...")

        try:
            rollback_script = f"""#!/usr/bin/env python3
\"\"\"
Novel Engine Rollback Script
Generated: {datetime.now().isoformat()}
Deployment ID: {self.deployment_id}
\"\"\"

import os
import sys
import shutil
import subprocess
from pathlib import Path

def rollback():
    deployment_id = "{self.deployment_id}"
    project_root = Path(__file__).parent.parent
    backup_dir = project_root / "staging" / "backups" / deployment_id

    print(f"🔄 Rolling back deployment: {{deployment_id}}")

    # Stop services
    print("⏹️  Stopping services...")
    try:
        subprocess.run(["pkill", "-f", "api_server.py"], check=False)
    except (FileNotFoundError, OSError, shutil.Error) as e:
        print(f"⚠️ Warning: Failed to stop services: {{e}}")

    # Restore configuration files
    config_files = ["configs/environments/development.yaml", "configs/environments/settings.yaml", "requirements.txt"]

    for config_file in config_files:
        backup_file = backup_dir / config_file
        target_file = project_root / config_file

        if backup_file.exists():
            shutil.copy2(backup_file, target_file)
            print(f"📦 Restored: {{config_file}}")

    # Restore directories
    critical_dirs = ["private", "logs"]

    for dir_name in critical_dirs:
        backup_dir_path = backup_dir / dir_name
        target_dir_path = project_root / dir_name

        if backup_dir_path.exists():
            if target_dir_path.exists():
                shutil.rmtree(target_dir_path)
            shutil.copytree(backup_dir_path, target_dir_path)
            print(f"📦 Restored directory: {{dir_name}}")

    print("✅ Rollback completed")
    print("💡 Restart services manually if needed")

if __name__ == "__main__":
    rollback()
"""

            rollback_file = self.backup_dir / "rollback.py"
            with open(rollback_file, "w") as f:
                f.write(rollback_script)

            # Make executable
            os.chmod(rollback_file, 0o755)

            logger.info(f"✅ Rollback script created: {rollback_file}")
            return True

        except Exception as e:
            logger.error(f"❌ Rollback script creation failed: {e}")
            return False

    def deploy(self, validate_only: bool = False) -> bool:
        """Execute complete staging deployment."""
        logger.info(
            f"🚀 Starting Novel Engine staging deployment: {self.deployment_id}"
        )

        # Step 1: System validation
        if not self.validate_system():
            logger.error("❌ System validation failed - deployment aborted")
            return False

        if validate_only:
            logger.info("✅ Validation complete - stopping here as requested")
            return True

        # Step 2: Create backup
        if not self.create_backup():
            logger.error("❌ Backup creation failed - deployment aborted")
            return False

        # Step 3: Create rollback script
        if not self.create_rollback_script():
            logger.warning(
                "⚠️ Rollback script creation failed - continuing anyway"
            )

        # Step 4: Deploy configuration
        if not self.deploy_configuration():
            logger.error(
                "❌ Configuration deployment failed - deployment aborted"
            )
            return False

        # Step 5: Start services
        if not self.start_services():
            logger.error("❌ Service startup failed - deployment aborted")
            return False

        # Step 6: Health checks
        if not self.run_health_checks():
            logger.error("❌ Health checks failed - deployment failed")
            logger.info("💡 Use rollback script to restore previous state")
            return False

        # Step 7: Final validation
        logger.info("🎉 Staging deployment completed successfully!")
        logger.info(f"📊 Deployment ID: {self.deployment_id}")
        logger.info(f"🔄 Rollback available: {self.backup_dir / 'rollback.py'}")
        logger.info("🌐 API Server: http://localhost:8000")
        logger.info(f"📊 Health Status: {self.health_check_url}")

        return True

    def rollback(self) -> bool:
        """Execute rollback to previous state."""
        logger.info(f"🔄 Rolling back deployment: {self.deployment_id}")

        try:
            # Stop current services
            if hasattr(self, "server_process"):
                self.server_process.terminate()
                self.server_process.wait(timeout=10)

            # Execute rollback script if it exists
            rollback_script = self.backup_dir / "rollback.py"
            if rollback_script.exists():
                result = subprocess.run([sys.executable, str(rollback_script)])
                if result.returncode == 0:
                    logger.info("✅ Rollback completed successfully")
                    return True
                else:
                    logger.error("❌ Rollback script execution failed")
                    return False
            else:
                logger.error("❌ Rollback script not found")
                return False

        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Novel Engine Staging Deployment"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only run validation, don't deploy",
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback the most recent deployment",
    )

    args = parser.parse_args()

    deployment = StagingDeployment()

    if args.rollback:
        success = deployment.rollback()
    else:
        success = deployment.deploy(validate_only=args.validate_only)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
