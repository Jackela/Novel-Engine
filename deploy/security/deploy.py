#!/usr/bin/env python3
"""
Secure Deployment Script
=======================

Production deployment script with comprehensive security hardening,
SSL/TLS configuration, and enterprise-grade protection systems.

Professional secure deployment implementation.

Architecture: Automated secure deployment with validation
Security Level: Enterprise Grade Production Deployment
Author: Novel Engine Development Team
Professional deployment script for enterprise security.
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.security.auth_system import AuthenticationManager
from src.security.ssl_config import (
    SSLCertificateManager,
)

# Sacred logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("deployment.log")],
)
logger = logging.getLogger(__name__)


class SecureDeploymentManager:
    """Secure Deployment Manager"""

    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.config_path = Path("configs/security/security.yaml")
        self.cert_manager = SSLCertificateManager()
        self.deployment_config: Dict[str, Any] = {}

        logger.info(f"Secure deployment manager initialized for {environment.upper()}")

    def load_security_config(self) -> Dict[str, Any]:
        """Security Configuration Loading"""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r") as f:
                    config = yaml.safe_load(f)

                # Apply environment-specific overrides
                if (
                    "environments" in config
                    and self.environment in config["environments"]
                ):
                    env_config = config["environments"][self.environment]
                    self._deep_merge_config(config, env_config)

                logger.info("Security configuration loaded successfully")
                return config
            else:
                logger.warning("Security configuration file not found - using defaults")
                return self._get_default_config()

        except Exception as e:
            logger.error(f"Security configuration loading error: {e}")
            return self._get_default_config()

    def _deep_merge_config(self, base: Dict, override: Dict):
        """Deep merge configuration dictionaries"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge_config(base[key], value)
            else:
                base[key] = value

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default security configuration"""
        return {
            "authentication": {"enabled": False},
            "rate_limiting": {"enabled": True},
            "ssl": {"enabled": False},
            "security_headers": {"enabled": True},
            "input_validation": {"enabled": True},
            "monitoring": {"enabled": True},
        }

    def setup_ssl_certificates(self, config: Dict[str, Any]) -> Optional[tuple]:
        """SSL Certificate Setup"""
        ssl_config = config.get("ssl", {})

        if not ssl_config.get("enabled", False):
            logger.info("SSL/TLS disabled - skipping certificate setup")
            return None

        try:
            if self.environment == "development":
                # Generate self-signed certificates for development
                dev_config = ssl_config.get("development", {})
                domain = dev_config.get("domain", "localhost")
                alt_names = dev_config.get("alt_names", ["localhost", "127.0.0.1"])

                cert_file, key_file = self.cert_manager.generate_self_signed_cert(
                    domain=domain, alt_names=alt_names
                )

                logger.info(
                    f"Development SSL certificates generated: {cert_file}, {key_file}"
                )
                return cert_file, key_file

            else:
                # Use provided certificates for production
                cert_file = ssl_config.get("cert_file")
                key_file = ssl_config.get("key_file")

                if not cert_file or not key_file:
                    logger.error("Production SSL certificates not configured")
                    return None

                # Validate certificates
                if not self.cert_manager.validate_certificate(cert_file, key_file):
                    logger.error("SSL certificate validation failed")
                    return None

                logger.info(
                    f"Production SSL certificates validated: {cert_file}, {key_file}"
                )
                return cert_file, key_file

        except Exception as e:
            logger.error(f"SSL certificate setup error: {e}")
            return None

    def setup_database_security(self, config: Dict[str, Any]):
        """Database Security Setup"""
        db_config = config.get("database", {})

        try:
            # Ensure data directory exists with secure permissions
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True, mode=0o700)

            # Set secure permissions on existing database files
            for db_file in data_dir.glob("*.db"):
                os.chmod(db_file, 0o600)
                logger.info(f"Secured database file: {db_file}")

            # Set up backup directory with secure permissions
            backup_dir = Path(
                db_config.get("backup", {}).get("secure_location", "data/backups")
            )
            backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

            logger.info("Database security configuration applied")

        except Exception as e:
            logger.error(f"Database security setup error: {e}")

    def setup_authentication_system(self, config: Dict[str, Any]) -> bool:
        """Authentication System Setup"""
        auth_config = config.get("authentication", {})

        if not auth_config.get("enabled", False):
            logger.info("Authentication system disabled")
            return False

        try:
            # Set up JWT secret
            jwt_secret = os.getenv("JWT_SECRET")
            if not jwt_secret:
                import secrets

                jwt_secret = secrets.token_urlsafe(32)
                logger.warning(
                    "JWT secret auto-generated - set JWT_SECRET environment variable"
                )

            # Initialize authentication manager
            AuthenticationManager(
                database_path="data/api_server.db", jwt_secret=jwt_secret
            )

            # This would be called during application startup
            logger.info("Authentication system configured")
            return True

        except Exception as e:
            logger.error(f"Authentication system setup error: {e}")
            return False

    def validate_security_configuration(self, config: Dict[str, Any]) -> bool:
        """Security Configuration Validation"""
        validation_errors = []

        # Validate SSL configuration
        ssl_config = config.get("ssl", {})
        if ssl_config.get("enabled") and self.environment == "production":
            if not ssl_config.get("cert_file") or not ssl_config.get("key_file"):
                validation_errors.append(
                    "SSL enabled but certificate files not specified"
                )

        # Validate authentication configuration
        auth_config = config.get("authentication", {})
        if auth_config.get("enabled"):
            if not os.getenv("JWT_SECRET"):
                validation_errors.append(
                    "Authentication enabled but JWT_SECRET not set"
                )

        # Validate rate limiting configuration
        rate_config = config.get("rate_limiting", {})
        if rate_config.get("enabled"):
            global_config = rate_config.get("global", {})
            if not global_config:
                validation_errors.append(
                    "Rate limiting enabled but no global configuration"
                )

        if validation_errors:
            logger.error("Security configuration validation errors")
            for error in validation_errors:
                logger.error(f"  - {error}")
            return False

        logger.info("Security configuration validation passed")
        return True

    def setup_environment_variables(self, config: Dict[str, Any]):
        """Environment Variables Setup"""
        env_vars = {
            "DEBUG": "false" if self.environment == "production" else "true",
            "ENABLE_DOCS": "false" if self.environment == "production" else "true",
            "LOG_LEVEL": "WARNING" if self.environment == "production" else "INFO",
            "ENABLE_RATE_LIMITING": str(
                config.get("rate_limiting", {}).get("enabled", True)
            ).lower(),
            "ENABLE_AUTH": str(
                config.get("authentication", {}).get("enabled", False)
            ).lower(),
        }

        # SSL configuration
        ssl_config = config.get("ssl", {})
        if ssl_config.get("enabled"):
            env_vars["ENABLE_HTTPS"] = "true"
            if ssl_config.get("cert_file"):
                env_vars["SSL_CERT_FILE"] = ssl_config["cert_file"]
            if ssl_config.get("key_file"):
                env_vars["SSL_KEY_FILE"] = ssl_config["key_file"]

        # Set environment variables
        for key, value in env_vars.items():
            os.environ[key] = value
            logger.info(f"Set environment variable: {key}={value}")

    def generate_deployment_report(
        self, config: Dict[str, Any], ssl_setup: Optional[tuple]
    ) -> str:
        """Deployment Report Generation"""
        timestamp = datetime.now().isoformat()

        report = f"""
Deployment Report
======================================================

Deployment Environment: {self.environment.upper()}
Deployment Time: {timestamp}

SECURITY CONFIGURATION:
- Authentication: {'ENABLED' if config.get('authentication', {}).get('enabled') else 'DISABLED'}
- Rate Limiting: {'ENABLED' if config.get('rate_limiting', {}).get('enabled') else 'DISABLED'}
- Input Validation: {'ENABLED' if config.get('input_validation', {}).get('enabled') else 'DISABLED'}
- Security Headers: {'ENABLED' if config.get('security_headers', {}).get('enabled') else 'DISABLED'}
- SSL/TLS: {'ENABLED' if ssl_setup else 'DISABLED'}
- Monitoring: {'ENABLED' if config.get('monitoring', {}).get('enabled') else 'DISABLED'}

SSL/TLS CONFIGURATION:
"""
        if ssl_setup:
            cert_file, key_file = ssl_setup
            cert_info = self.cert_manager.get_certificate_info(cert_file)
            report += f"""- Certificate File: {cert_file}
- Private Key File: {key_file}
- Subject: {cert_info.get('subject', 'Unknown')}
- Issuer: {cert_info.get('issuer', 'Unknown')}
- Valid Until: {cert_info.get('not_valid_after', 'Unknown')}
- Key Size: {cert_info.get('public_key_size', 'Unknown')} bits
- Fingerprint (SHA256): {cert_info.get('fingerprint_sha256', 'Unknown')}
"""
        else:
            report += "- SSL/TLS: Not configured\n"

        report += f"""
DEPLOYMENT STATUS: {'SUCCESS' if self.validate_security_configuration(config) else 'FAILED'}

Secure Deployment Complete
"""
        return report

    async def deploy(self) -> bool:
        """Deployment Execution"""
        try:
            logger.info(f"Starting secure deployment for {self.environment.upper()}")

            # Load security configuration
            config = self.load_security_config()

            # Validate configuration
            if not self.validate_security_configuration(config):
                logger.error("Deployment failed - configuration validation errors")
                return False

            # Setup environment variables
            self.setup_environment_variables(config)

            # Setup SSL certificates
            ssl_setup = self.setup_ssl_certificates(config)

            # Setup database security
            self.setup_database_security(config)

            # Setup authentication system
            self.setup_authentication_system(config)

            # Generate deployment report
            report = self.generate_deployment_report(config, ssl_setup)

            # Save deployment report
            report_file = f"deployment_report_{self.environment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(report_file, "w") as f:
                f.write(report)

            logger.info(f"Deployment report saved: {report_file}")
            print(report)

            logger.info("Secure deployment completed successfully")
            return True

        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            return False


def main():
    """Main Deployment Function"""
    parser = argparse.ArgumentParser(
        description="Secure deployment script for Novel Engine"
    )
    parser.add_argument(
        "--environment",
        choices=["development", "staging", "production"],
        default="production",
        help="Deployment environment",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate configuration without deploying",
    )
    parser.add_argument(
        "--generate-ssl",
        action="store_true",
        help="Generate self-signed SSL certificates for development",
    )

    args = parser.parse_args()

    # Create deployment manager
    deployment_manager = SecureDeploymentManager(args.environment)

    if args.generate_ssl:
        logger.info("Generating SSL certificates")
        cert_file, key_file = (
            deployment_manager.cert_manager.generate_self_signed_cert()
        )
        logger.info(f"SSL certificates generated: {cert_file}, {key_file}")
        return

    if args.validate_only:
        logger.info("Validating configuration only")
        config = deployment_manager.load_security_config()
        is_valid = deployment_manager.validate_security_configuration(config)
        if is_valid:
            logger.info("Configuration validation passed")
            sys.exit(0)
        else:
            logger.error("Configuration validation failed")
            sys.exit(1)

    # Run deployment
    success = asyncio.run(deployment_manager.deploy())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
