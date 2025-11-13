#!/usr/bin/env python3
"""
Knowledge Base Builder for Novel Engine
========================================

This script builds and validates the knowledge base required for the Novel Engine.
It includes startup guards to ensure the system is properly configured before operation.

Features:
- Configuration validation and startup guards
- Knowledge base initialization and validation
- Legal compliance verification
- Dependency checking and system readiness validation
- Safe mode and error recovery mechanisms

Startup Guards:
1. Configuration file validation (settings.yaml)
2. Legal compliance verification (LEGAL.md, fan mode registry)
3. Required directories and file structure validation
4. API key and external dependency verification
5. Knowledge base integrity checking
"""

import argparse
import json
import logging
import os
import sys

# Expose builtin __import__ for tests that patch scripts.build_kb.__import__
from builtins import __import__ as _builtin_import
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import yaml

__import__ = _builtin_import


class StartupGuard:
    """Startup validation and safety guard system."""

    def __init__(self):
        self.logger = self._setup_logging()
        self.errors = []
        self.warnings = []
        self.config = None

    def _setup_logging(self) -> logging.Logger:
        """Initialize logging system."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler("logs/startup.log", mode="a"),
            ],
        )
        return logging.getLogger("StartupGuard")

    def validate_all(self) -> bool:
        """
        Run all startup validation checks.

        Returns:
            bool: True if all validations pass, False otherwise
        """
        self.logger.info("🚀 Starting Novel Engine startup validation...")

        validation_checks = [
            ("Configuration System", self._validate_configuration),
            ("Legal Compliance", self._validate_legal_compliance),
            ("File Structure", self._validate_file_structure),
            ("External Dependencies", self._validate_external_dependencies),
            ("Knowledge Base", self._validate_knowledge_base),
            ("API Readiness", self._validate_api_readiness),
        ]

        all_passed = True

        for check_name, check_function in validation_checks:
            self.logger.info(f"🔍 Validating {check_name}...")
            try:
                if not check_function():
                    all_passed = False
                    self.logger.error(f"❌ {check_name} validation failed")
                else:
                    self.logger.info(f"✅ {check_name} validation passed")
            except Exception as e:
                all_passed = False
                self.errors.append(f"{check_name}: {str(e)}")
                self.logger.error(f"❌ {check_name} validation error: {e}")

        self._report_results(all_passed)
        return all_passed

    def _validate_configuration(self) -> bool:
        """Validate system configuration files."""
        try:
            # Check settings.yaml exists and is valid
            settings_path = Path("settings.yaml")
            if not settings_path.exists():
                self.errors.append("settings.yaml file not found")
                return False

            with open(settings_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)

            # Validate required configuration sections
            required_sections = [
                "system",
                "legal",
                "api",
                "storage",
                "ai",
                "simulation",
                "performance",
                "security",
            ]

            for section in required_sections:
                if section not in self.config:
                    self.errors.append(f"Missing configuration section: {section}")
                    return False

            # Validate legal configuration
            legal_config = self.config.get("legal", {})
            if not legal_config.get("enable_safeguards", False):
                self.warnings.append(
                    "Legal safeguards are disabled - this may cause compliance issues"
                )

            # Validate simulation configuration
            simulation_config = self.config.get("simulation", {})
            if not simulation_config.get("iron_laws", {}).get("enabled", False):
                self.errors.append(
                    "Iron Laws validation must be enabled for safe operation"
                )
                return False

            return True

        except yaml.YAMLError as e:
            self.errors.append(f"Invalid YAML syntax in settings.yaml: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Configuration validation error: {e}")
            return False

    def _validate_legal_compliance(self) -> bool:
        """Validate legal compliance requirements."""
        try:
            # Check LEGAL.md exists
            legal_path = Path("LEGAL.md")
            if not legal_path.exists():
                self.errors.append(
                    "LEGAL.md file not found - legal compliance documentation required"
                )
                return False

            # Check NOTICE file exists
            notice_path = Path("NOTICE")
            if not notice_path.exists():
                self.errors.append(
                    "NOTICE file not found - third-party attribution required"
                )
                return False

            # Validate fan mode compliance if enabled
            if (
                self.config
                and self.config.get("legal", {}).get("compliance_mode") == "fan"
            ):
                registry_file = self.config.get("legal", {}).get(
                    "registry_file", "private/registry.yaml"
                )
                registry_path = Path(registry_file)

                if not registry_path.exists():
                    self.warnings.append(
                        f"Fan mode enabled but registry file {registry_file} not found"
                    )
                    # Create directory structure if needed
                    registry_path.parent.mkdir(parents=True, exist_ok=True)

                    # Create template registry file
                    template_registry = {
                        "sources": [],
                        "compliance": {
                            "non_commercial": True,
                            "distribution": "local_only",
                        },
                    }

                    with open(registry_path, "w", encoding="utf-8") as f:
                        yaml.dump(template_registry, f, default_flow_style=False)

                    self.logger.info(
                        f"📝 Created template registry file: {registry_file}"
                    )

            return True

        except Exception as e:
            self.errors.append(f"Legal compliance validation error: {e}")
            return False

    def _validate_file_structure(self) -> bool:
        """Validate required file and directory structure."""
        try:
            # Required directories
            required_dirs = [
                "src",
                "tests",
                "docs",
                "docs/ADRs",
                "scripts",
                "private",
                "logs",
                "evaluation",
            ]

            for dir_path in required_dirs:
                path = Path(dir_path)
                if not path.exists():
                    path.mkdir(parents=True, exist_ok=True)
                    self.logger.info(f"📁 Created directory: {dir_path}")

            # Required files
            required_files = ["README.md", "LEGAL.md", "NOTICE", "settings.yaml"]

            for file_path in required_files:
                if not Path(file_path).exists():
                    self.errors.append(f"Required file not found: {file_path}")
                    return False

            # Ensure private directory has proper .gitignore
            private_gitignore = Path("private/.gitignore")
            if not private_gitignore.exists():
                with open(private_gitignore, "w", encoding="utf-8") as f:
                    f.write("# Ignore all private data\n*\n!.gitignore\n")
                self.logger.info("📝 Created private/.gitignore for data protection")

            return True

        except Exception as e:
            self.errors.append(f"File structure validation error: {e}")
            return False

    def _validate_external_dependencies(self) -> bool:
        """Validate external dependencies and API keys."""
        try:
            # Check Python dependencies
            required_packages = ["fastapi", "uvicorn", "pydantic", "yaml", "requests"]

            missing_packages = []
            for package in required_packages:
                try:
                    __import__(package)
                except ImportError:
                    missing_packages.append(package)

            if missing_packages:
                self.errors.append(
                    f"Missing Python packages: {', '.join(missing_packages)}"
                )
                return False

            # Check API key configuration (optional but recommended)
            api_keys = ["OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"]
            available_keys = [key for key in api_keys if os.getenv(key)]

            if not available_keys:
                self.warnings.append(
                    "No AI API keys found - system will run in offline mode"
                )
            else:
                self.logger.info(f"📡 Available API keys: {len(available_keys)}")

            return True

        except Exception as e:
            self.errors.append(f"External dependencies validation error: {e}")
            return False

    def _validate_knowledge_base(self) -> bool:
        """Validate knowledge base structure and content."""
        try:
            if not self.config:
                self.errors.append(
                    "Configuration not loaded - cannot validate knowledge base"
                )
                return False

            # Get KB configuration
            storage_config = self.config.get("storage", {})
            kb_path = Path(storage_config.get("kb_path", "private/knowledge_base/"))

            # Ensure KB directory exists
            kb_path.mkdir(parents=True, exist_ok=True)

            # Create basic KB structure if empty
            kb_subdirs = ["characters", "worlds", "rules", "templates"]
            for subdir in kb_subdirs:
                subdir_path = kb_path / subdir
                subdir_path.mkdir(exist_ok=True)

                # Create README for each subdirectory
                readme_path = subdir_path / "README.md"
                if not readme_path.exists():
                    with open(readme_path, "w", encoding="utf-8") as f:
                        f.write(f"# {subdir.title()} Knowledge Base\n\n")
                        f.write(
                            f"This directory contains {subdir} data for the Novel Engine.\n"
                        )

            self.logger.info(f"📚 Knowledge base initialized at: {kb_path}")
            return True

        except Exception as e:
            self.errors.append(f"Knowledge base validation error: {e}")
            return False

    def _validate_api_readiness(self) -> bool:
        """Validate API server readiness."""
        try:
            # Check if API server files exist
            api_files = ["api_server.py"]
            for file_path in api_files:
                if not Path(file_path).exists():
                    self.warnings.append(f"API file not found: {file_path}")

            # Validate API configuration
            if self.config:
                api_config = self.config.get("api", {})

                # Check port availability (basic check)
                port = api_config.get("port", 8000)
                host = api_config.get("host", "localhost")

                self.logger.info(f"🌐 API configured for {host}:{port}")

                # Validate CORS configuration
                if api_config.get("cors_enabled", False):
                    cors_origins = api_config.get("cors_origins", [])
                    if not cors_origins:
                        self.warnings.append("CORS enabled but no origins specified")

            return True

        except Exception as e:
            self.errors.append(f"API readiness validation error: {e}")
            return False

    def _report_results(self, all_passed: bool):
        """Report validation results."""
        self.logger.info("=" * 60)
        self.logger.info("🏁 STARTUP VALIDATION SUMMARY")
        self.logger.info("=" * 60)

        if all_passed:
            self.logger.info("✅ ALL VALIDATIONS PASSED - System ready for startup")
        else:
            self.logger.error("❌ VALIDATION FAILURES DETECTED - System not ready")

        if self.errors:
            self.logger.error(f"🚨 ERRORS ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                self.logger.error(f"  {i}. {error}")

        if self.warnings:
            self.logger.warning(f"⚠️  WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                self.logger.warning(f"  {i}. {warning}")

        self.logger.info("=" * 60)

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        return {
            "timestamp": datetime.now().isoformat(),
            "validation_passed": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "config_loaded": self.config is not None,
            "system_ready": len(self.errors) == 0,
        }


class KnowledgeBaseBuilder:
    """Knowledge base construction and management."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("KnowledgeBaseBuilder")

    def build_kb(self) -> bool:
        """Build and validate knowledge base."""
        try:
            self.logger.info("🔨 Building knowledge base...")

            storage_config = self.config.get("storage", {})
            kb_path = Path(storage_config.get("kb_path", "private/knowledge_base/"))

            # Create advanced KB structure
            kb_structure = {
                "characters": {
                    "templates": ["base_character.yaml", "faction_templates.yaml"],
                    "instances": [],
                },
                "worlds": {"templates": ["base_world.yaml"], "instances": []},
                "rules": {
                    "iron_laws.yaml": self._create_iron_laws_template(),
                    "fog_of_war.yaml": self._create_fog_of_war_template(),
                },
                "templates": {
                    "narrative_templates.yaml": self._create_narrative_templates()
                },
            }

            self._create_kb_structure(kb_path, kb_structure)

            self.logger.info("✅ Knowledge base built successfully")
            return True

        except Exception as e:
            self.logger.error(f"Knowledge base building error: {e}")
            return False

    def _create_kb_structure(self, kb_path: Path, structure: Dict[str, Any]):
        """Create knowledge base directory structure."""
        for item_name, item_content in structure.items():
            item_path = kb_path / item_name

            if isinstance(item_content, dict):
                item_path.mkdir(exist_ok=True)

                # Handle nested structure
                for sub_name, sub_content in item_content.items():
                    if isinstance(sub_content, list):
                        # Create subdirectory
                        sub_path = item_path / sub_name
                        sub_path.mkdir(exist_ok=True)

                        # Create template files
                        for template_file in sub_content:
                            template_path = sub_path / template_file
                            if not template_path.exists():
                                with open(template_path, "w", encoding="utf-8") as f:
                                    f.write(
                                        f"# {template_file}\n\n# Template content\n"
                                    )

                    elif isinstance(sub_content, dict):
                        # Create file with content
                        file_path = item_path / sub_name
                        if not file_path.exists():
                            with open(file_path, "w", encoding="utf-8") as f:
                                yaml.dump(sub_content, f, default_flow_style=False)

    def _create_iron_laws_template(self) -> Dict[str, Any]:
        """Create Iron Laws validation template."""
        return {
            "iron_laws": {
                "E001_RESOURCE_NEGATIVE": {
                    "description": "Resource Conservation - Actions cannot result in negative resource values",
                    "validation": "arithmetic",
                    "priority": 1,
                },
                "E002_TARGET_INVALID": {
                    "description": "Information Limit - Actions can only target entities visible to the actor",
                    "validation": "visibility_check",
                    "priority": 2,
                },
                "E003_ACTION_IMPOSSIBLE": {
                    "description": "State Consistency - Actions must be permitted for current entity state",
                    "validation": "state_check",
                    "priority": 3,
                },
                "E004_LOGIC_VIOLATION": {
                    "description": "Rule Adherence - Actions cannot contradict established world rules",
                    "validation": "rule_check",
                    "priority": 4,
                },
                "E005_CANON_BREACH": {
                    "description": "Canon Preservation - Actions cannot violate canonical source material",
                    "validation": "canon_check",
                    "priority": 5,
                },
            }
        }

    def _create_fog_of_war_template(self) -> Dict[str, Any]:
        """Create Fog of War template."""
        return {
            "fog_of_war": {
                "channels": {
                    "visual": {
                        "default_range": 10,
                        "description": "Direct line-of-sight observation",
                    },
                    "radio": {
                        "default_range": 50,
                        "description": "Communication-based information sharing",
                    },
                    "intel": {
                        "default_range": 100,
                        "description": "Intelligence gathering and faction sharing",
                    },
                },
                "filtering_rules": {
                    "entity_visibility": "Only entities within scope are visible",
                    "fact_filtering": "Only facts about visible entities are included",
                    "provenance_tracking": "All information includes source attribution",
                },
            }
        }

    def _create_narrative_templates(self) -> Dict[str, Any]:
        """Create narrative generation templates."""
        return {
            "narrative_styles": {
                "grimdark_dramatic": {
                    "tone": "dark, foreboding",
                    "perspective": "omniscient",
                    "focus": "character psychology and atmosphere",
                },
                "tactical": {
                    "tone": "analytical, strategic",
                    "perspective": "military briefing",
                    "focus": "tactics and decision-making",
                },
                "heroic": {
                    "tone": "inspiring, epic",
                    "perspective": "hero-focused",
                    "focus": "courage and sacrifice",
                },
            }
        }


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Novel Engine Knowledge Base Builder")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only run validation checks, do not build KB",
    )
    parser.add_argument(
        "--force-build",
        action="store_true",
        help="Force KB rebuild even if validation fails",
    )
    parser.add_argument(
        "--config", default="settings.yaml", help="Configuration file path"
    )

    args = parser.parse_args()

    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)

    # Initialize startup guard
    startup_guard = StartupGuard()

    # Run validation
    validation_passed = startup_guard.validate_all()

    if args.validate_only:
        sys.exit(0 if validation_passed else 1)

    if not validation_passed and not args.force_build:
        logging.error("🚨 Validation failed. Use --force-build to proceed anyway.")
        sys.exit(1)

    # Build knowledge base if validation passed or forced
    if startup_guard.config:
        kb_builder = KnowledgeBaseBuilder(startup_guard.config)
        kb_success = kb_builder.build_kb()

        if not kb_success:
            logging.error("❌ Knowledge base building failed")
            sys.exit(1)

    logging.info("🎉 Novel Engine startup preparation complete!")

    # Output system status
    status = startup_guard.get_system_status()
    status_file = Path("logs/system_status.json")
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2)

    logging.info(f"📊 System status saved to: {status_file}")

    return 0 if validation_passed else 1


if __name__ == "__main__":
    sys.exit(main())
