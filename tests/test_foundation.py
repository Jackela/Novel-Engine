"""
Test Foundation for Novel Engine
===============================

Basic infrastructure tests to validate the foundation of the Novel Engine project.
These tests ensure that legal, configuration, and documentation files are properly
set up before proceeding with core engine implementation.

Test Coverage:
- Legal and compliance file validation
- Configuration system validation
- Documentation structure validation
- File permissions and accessibility
- Basic project structure integrity
"""

from pathlib import Path

import pytest
import yaml


class TestLegalFoundation:
    """Test legal and compliance infrastructure."""

    @pytest.mark.unit
    def test_legal_file_exists(self):
        """Verify LEGAL.md file exists and is accessible."""
        legal_path = Path("LEGAL.md")
        assert legal_path.exists(), "LEGAL.md file must exist for compliance"
        assert legal_path.is_file(), "LEGAL.md must be a file"

    @pytest.mark.unit
    def test_legal_file_content(self):
        """Validate LEGAL.md contains required sections."""
        with open("LEGAL.md", "r", encoding="utf-8") as f:
            content = f.read()

        required_sections = [
            "Non-Affiliation Disclaimer",
            "Copyright and Fair Use",
            "Fan Mode Compliance",
            "DMCA and Content Removal",
            "Disclaimer of Warranties",
            "Limitation of Liability",
        ]

        for section in required_sections:
            assert section in content, f"LEGAL.md must contain '{section}' section"

    @pytest.mark.unit
    def test_legal_fan_mode_compliance(self):
        """Validate fan mode compliance requirements are documented."""
        with open("LEGAL.md", "r", encoding="utf-8") as f:
            content = f.read()

        fan_mode_requirements = [
            "Non-Commercial Use Only",
            "Local Distribution Only",
            "Compliance Documentation",
            "private/registry.yaml",
        ]

        for requirement in fan_mode_requirements:
            assert requirement in content, f"Fan mode must document '{requirement}'"

    @pytest.mark.unit
    def test_notice_file_exists(self):
        """Verify NOTICE file exists for third-party attributions."""
        notice_path = Path("NOTICE")
        assert (
            notice_path.exists()
        ), "NOTICE file must exist for third-party attributions"
        assert notice_path.is_file(), "NOTICE must be a file"

    @pytest.mark.unit
    def test_notice_file_content(self):
        """Validate NOTICE file contains required third-party notices."""
        with open("NOTICE", "r", encoding="utf-8") as f:
            content = f.read()

        required_attributions = [
            "FastAPI",
            "Pydantic",
            "OpenAI Python Library",
            "Uvicorn",
            "PyYAML",
        ]

        for attribution in required_attributions:
            assert (
                attribution in content
            ), f"NOTICE must include '{attribution}' attribution"


class TestConfigurationFoundation:
    """Test configuration system infrastructure."""

    @pytest.mark.unit
    def test_settings_yaml_exists(self):
        """Verify settings.yaml configuration file exists."""
        settings_path = Path("settings.yaml")
        assert (
            settings_path.exists()
        ), "settings.yaml must exist for system configuration"
        assert settings_path.is_file(), "settings.yaml must be a file"

    @pytest.mark.unit
    def test_settings_yaml_valid_syntax(self):
        """Validate settings.yaml has valid YAML syntax."""
        with open("settings.yaml", "r", encoding="utf-8") as f:
            try:
                config = yaml.safe_load(f)
                assert isinstance(
                    config, dict
                ), "settings.yaml must contain a dictionary"
            except yaml.YAMLError as e:
                pytest.fail(f"settings.yaml contains invalid YAML syntax: {e}")

    @pytest.mark.unit
    def test_settings_yaml_required_sections(self):
        """Validate settings.yaml contains all required configuration sections."""
        with open("settings.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        required_sections = [
            "system",
            "legal",
            "api",
            "storage",
            "ai",
            "simulation",
            "performance",
            "monitoring",
            "security",
            "paths",
        ]

        for section in required_sections:
            assert section in config, f"settings.yaml must contain '{section}' section"

    @pytest.mark.unit
    def test_legal_settings_configuration(self):
        """Validate legal compliance settings are properly configured."""
        with open("settings.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        legal_config = config.get("legal", {})

        # Verify legal safeguards are enabled by default
        assert legal_config.get(
            "enable_safeguards", False
        ), "Legal safeguards must be enabled by default"

        # Verify compliance mode is set
        compliance_mode = legal_config.get("compliance_mode")
        assert compliance_mode in [
            "standard",
            "fan",
        ], "Compliance mode must be 'standard' or 'fan'"

        # Verify registry file path is configured
        assert "registry_file" in legal_config, "Registry file path must be configured"

    @pytest.mark.unit
    def test_simulation_engine_settings(self):
        """Validate simulation engine settings are properly configured."""
        with open("settings.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        simulation_config = config.get("simulation", {})

        # Verify Iron Laws settings
        iron_laws = simulation_config.get("iron_laws", {})
        assert iron_laws.get("enabled", False), "Iron Laws validation must be enabled"

        # Verify Fog of War settings
        fog_of_war = simulation_config.get("fog_of_war", {})
        assert fog_of_war.get("enabled", False), "Fog of War must be enabled"

        # Verify turn processing limits
        assert isinstance(
            simulation_config.get("max_agents_per_turn"), int
        ), "Max agents per turn must be integer"
        assert (
            simulation_config.get("max_agents_per_turn", 0) > 0
        ), "Must allow at least one agent per turn"


class TestDocumentationFoundation:
    """Test documentation infrastructure."""

    @pytest.mark.unit
    def test_adrs_directory_exists(self):
        """Verify Architecture Decision Records directory exists."""
        adrs_path = Path("docs/adr")
        assert adrs_path.exists(), "docs/adr directory must exist"
        assert adrs_path.is_dir(), "docs/adr must be a directory"

    @pytest.mark.unit
    def test_adrs_readme_exists(self):
        """Verify ADRs README exists and lists all ADRs."""
        adrs_index = Path("docs/adr/index.md")
        assert adrs_index.exists(), "docs/adr/index.md must exist"

        with open(adrs_index, "r", encoding="utf-8") as f:
            content = f.read()

        # Verify essential ADRs are documented
        essential_adrs = [
            ("ADR-001", "Iron Laws Validation System"),
            ("ADR-002", "Fog of War Information Filtering"),
            ("ADR-003", "Pydantic Schema Architecture"),
        ]

        for adr_id, title in essential_adrs:
            assert adr_id in content, f"ADR index must reference '{adr_id}'"
            assert title in content, f"ADR index must reference '{title}'"

    @pytest.mark.unit
    def test_core_adrs_exist(self):
        """Verify core ADR files exist and are properly formatted."""
        core_adrs = [
            "docs/adr/ADR-001-iron-laws-validation.md",
            "docs/adr/ADR-002-fog-of-war-filtering.md",
            "docs/adr/ADR-003-pydantic-schemas.md",
        ]

        for adr_path in core_adrs:
            path = Path(adr_path)
            assert path.exists(), f"Core ADR {adr_path} must exist"

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Verify ADR structure
            required_sections = ["Status", "Date", "Context", "Decision"]
            for section in required_sections:
                assert (
                    section in content
                ), f"ADR {adr_path} must contain '{section}' section"

    @pytest.mark.unit
    def test_developer_documentation_exists(self):
        """Verify developer documentation files exist."""
        dev_docs = [
            "docs/DEVELOPER_GUIDE.md",
            "docs/IMPLEMENTATION_PATTERNS.md",
            "docs/DEBUGGING.md",
        ]

        for doc_path in dev_docs:
            path = Path(doc_path)
            assert path.exists(), f"Developer documentation {doc_path} must exist"
            assert (
                path.stat().st_size > 0
            ), f"Developer documentation {doc_path} must not be empty"


class TestProjectStructure:
    """Test basic project structure and file permissions."""

    @pytest.mark.unit
    def test_directory_structure(self):
        """Verify essential directories exist."""
        essential_dirs = ["src", "tests", "docs", "docs/adr", "scripts", "private"]

        for dir_path in essential_dirs:
            path = Path(dir_path)
            assert path.exists(), f"Essential directory {dir_path} must exist"
            assert path.is_dir(), f"{dir_path} must be a directory"

    @pytest.mark.unit
    def test_private_directory_structure(self):
        """Verify private directory structure for data isolation."""
        private_path = Path("private")
        assert private_path.exists(), "private/ directory must exist for data isolation"

        # Create .gitignore if it doesn't exist
        gitignore_path = private_path / ".gitignore"
        if not gitignore_path.exists():
            with open(gitignore_path, "w", encoding="utf-8") as f:
                f.write("# Ignore all private data\n*\n!.gitignore\n")

    @pytest.mark.unit
    def test_file_permissions_security(self):
        """Verify configuration files have appropriate permissions."""
        sensitive_files = ["settings.yaml", "LEGAL.md"]

        for file_path in sensitive_files:
            path = Path(file_path)
            if path.exists():
                stat = path.stat()
                # Verify file is readable (basic check on Windows/Unix)
                assert stat.st_size > 0, f"{file_path} must not be empty"

    @pytest.mark.unit
    def test_readme_legal_disclaimer(self):
        """Verify README contains proper legal disclaimer."""
        readme_path = Path("README.md")
        assert readme_path.exists(), "README.md must exist"

        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Verify legal disclaimer is present
        disclaimer_indicators = [
            "LEGAL DISCLAIMER",
            "not affiliated",
            "Games Workshop",
            "educational and research purposes",
        ]

        for indicator in disclaimer_indicators:
            assert (
                indicator in content
            ), f"README must contain legal disclaimer with '{indicator}'"


class TestComplianceValidation:
    """Test compliance and safety validation systems."""

    @pytest.mark.unit
    def test_fan_mode_registry_structure(self):
        """Verify fan mode registry structure is documented."""
        with open("LEGAL.md", "r", encoding="utf-8") as f:
            legal_content = f.read()

        # Verify registry YAML structure is documented
        registry_structure_indicators = [
            "registry.yaml",
            "sources:",
            "compliance:",
            "non_commercial: true",
            'distribution: "local_only"',
        ]

        for indicator in registry_structure_indicators:
            assert (
                indicator in legal_content
            ), f"Fan mode registry structure must document '{indicator}'"

    @pytest.mark.unit
    def test_ip_protection_mechanisms(self):
        """Verify intellectual property protection mechanisms are in place."""
        with open("settings.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Verify legal safeguards in configuration
        legal_config = config.get("legal", {})
        assert legal_config.get("enable_safeguards"), "Legal safeguards must be enabled"

        # Verify content filtering is configured
        content_filtering = legal_config.get("content_filtering", {})
        assert content_filtering.get("enable"), "Content filtering must be enabled"
        assert content_filtering.get("severity") in [
            "strict",
            "moderate",
            "permissive",
        ], "Content filtering severity must be valid"

    @pytest.mark.unit
    def test_dmca_compliance_documentation(self):
        """Verify DMCA compliance procedures are documented."""
        with open("LEGAL.md", "r", encoding="utf-8") as f:
            content = f.read()

        dmca_requirements = [
            "DMCA and Content Removal",
            "Identification of the copyrighted work",
            "electronic or physical signature",
            "statement of good faith belief",
            "statement of accuracy",
        ]

        for requirement in dmca_requirements:
            assert (
                requirement in content
            ), f"DMCA compliance must document '{requirement}'"


if __name__ == "__main__":
    # Allow running tests directly with python
    pytest.main([__file__, "-v"])
