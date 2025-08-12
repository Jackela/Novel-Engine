"""
Test Startup Guards for Novel Engine
====================================

Comprehensive test suite for the startup validation and safety guard systems.
Tests ensure that the Novel Engine properly validates its configuration, legal
compliance, and system readiness before allowing operation.

Test Coverage:
- StartupGuard class functionality
- Configuration validation checks
- Legal compliance verification
- File structure validation
- External dependencies checking
- Knowledge base initialization
- API readiness validation
- Error and warning handling
- System status reporting
"""

import os
import sys
import yaml
import json
import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path for imports
sys.path.insert(0, os.path.abspath('.'))

from scripts.build_kb import StartupGuard, KnowledgeBaseBuilder


class TestStartupGuard:
    """Test the StartupGuard validation system."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create basic test structure
        Path("logs").mkdir(exist_ok=True)
        
        self.startup_guard = StartupGuard()
    
    def teardown_method(self):
        """Clean up after each test."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_settings_file(self, content=None):
        """Create a test settings.yaml file."""
        if content is None:
            content = {
                'system': {'name': 'Novel Engine', 'version': '1.0.0'},
                'legal': {'enable_safeguards': True, 'compliance_mode': 'standard'},
                'api': {'host': 'localhost', 'port': 8000},
                'storage': {'kb_path': 'private/knowledge_base/'},
                'ai': {'provider': 'openai'},
                'simulation': {'iron_laws': {'enabled': True}, 'fog_of_war': {'enabled': True}},
                'performance': {'semantic_cache': {'enabled': True}},
                'security': {'strict_validation': True}
            }
        
        with open("settings.yaml", "w", encoding="utf-8") as f:
            yaml.dump(content, f)
    
    def create_test_legal_file(self):
        """Create a test LEGAL.md file."""
        legal_content = """# Legal Notice

## Non-Affiliation Disclaimer
This software is not affiliated with Games Workshop.

## Fan Mode Compliance
When operating in "fan" mode, users must ensure compliance.

## DMCA and Content Removal
If you believe this software infringes your rights...

## Disclaimer of Warranties
This software is provided "as is" without warranty.

## Limitation of Liability
In no event shall the authors be liable...
"""
        with open("LEGAL.md", "w", encoding="utf-8") as f:
            f.write(legal_content)
    
    def create_test_notice_file(self):
        """Create a test NOTICE file."""
        notice_content = """Novel Engine
Copyright (c) 2025

This software contains components from:
FastAPI - MIT License
Pydantic - MIT License
"""
        with open("NOTICE", "w", encoding="utf-8") as f:
            f.write(notice_content)
    
    def test_startup_guard_initialization(self):
        """Test StartupGuard initializes properly."""
        guard = StartupGuard()
        
        assert guard.errors == []
        assert guard.warnings == []
        assert guard.config is None
        assert guard.logger is not None
    
    def test_validate_configuration_success(self):
        """Test configuration validation passes with valid settings."""
        self.create_test_settings_file()
        
        result = self.startup_guard._validate_configuration()
        
        assert result is True
        assert len(self.startup_guard.errors) == 0
        assert self.startup_guard.config is not None
        assert 'system' in self.startup_guard.config
    
    def test_validate_configuration_missing_file(self):
        """Test configuration validation fails when settings.yaml is missing."""
        # Don't create settings file
        
        result = self.startup_guard._validate_configuration()
        
        assert result is False
        assert any("settings.yaml file not found" in error for error in self.startup_guard.errors)
    
    def test_validate_configuration_invalid_yaml(self):
        """Test configuration validation fails with invalid YAML."""
        with open("settings.yaml", "w", encoding="utf-8") as f:
            f.write("invalid: yaml: content: [unclosed")
        
        result = self.startup_guard._validate_configuration()
        
        assert result is False
        assert any("Invalid YAML syntax" in error for error in self.startup_guard.errors)
    
    def test_validate_configuration_missing_sections(self):
        """Test configuration validation fails with missing required sections."""
        incomplete_config = {'system': {'name': 'Test'}}
        self.create_test_settings_file(incomplete_config)
        
        result = self.startup_guard._validate_configuration()
        
        assert result is False
        assert any("Missing configuration section" in error for error in self.startup_guard.errors)
    
    def test_validate_configuration_iron_laws_disabled(self):
        """Test configuration validation fails when Iron Laws are disabled."""
        config_with_disabled_laws = {
            'system': {'name': 'Novel Engine'},
            'legal': {'enable_safeguards': True},
            'api': {'host': 'localhost'},
            'storage': {'kb_path': 'private/kb/'},
            'ai': {'provider': 'openai'},
            'simulation': {'iron_laws': {'enabled': False}},  # Disabled
            'performance': {'semantic_cache': {'enabled': True}},
            'security': {'strict_validation': True}
        }
        self.create_test_settings_file(config_with_disabled_laws)
        
        result = self.startup_guard._validate_configuration()
        
        assert result is False
        assert any("Iron Laws validation must be enabled" in error for error in self.startup_guard.errors)
    
    def test_validate_legal_compliance_success(self):
        """Test legal compliance validation passes with valid files."""
        self.create_test_settings_file()
        self.create_test_legal_file()
        self.create_test_notice_file()
        
        # Load config first
        self.startup_guard._validate_configuration()
        
        result = self.startup_guard._validate_legal_compliance()
        
        assert result is True
        assert len(self.startup_guard.errors) == 0
    
    def test_validate_legal_compliance_missing_legal_file(self):
        """Test legal compliance validation fails when LEGAL.md is missing."""
        self.create_test_settings_file()
        self.create_test_notice_file()
        # Don't create LEGAL.md
        
        self.startup_guard._validate_configuration()
        result = self.startup_guard._validate_legal_compliance()
        
        assert result is False
        assert any("LEGAL.md file not found" in error for error in self.startup_guard.errors)
    
    def test_validate_legal_compliance_missing_notice_file(self):
        """Test legal compliance validation fails when NOTICE is missing."""
        self.create_test_settings_file()
        self.create_test_legal_file()
        # Don't create NOTICE
        
        self.startup_guard._validate_configuration()
        result = self.startup_guard._validate_legal_compliance()
        
        assert result is False
        assert any("NOTICE file not found" in error for error in self.startup_guard.errors)
    
    def test_validate_legal_compliance_fan_mode_registry_creation(self):
        """Test fan mode registry file is created when missing."""
        fan_config = {
            'system': {'name': 'Novel Engine'},
            'legal': {
                'enable_safeguards': True,
                'compliance_mode': 'fan',  # Fan mode
                'registry_file': 'private/registry.yaml'
            },
            'api': {'host': 'localhost'},
            'storage': {'kb_path': 'private/kb/'},
            'ai': {'provider': 'openai'},
            'simulation': {'iron_laws': {'enabled': True}},
            'performance': {'semantic_cache': {'enabled': True}},
            'security': {'strict_validation': True}
        }
        self.create_test_settings_file(fan_config)
        self.create_test_legal_file()
        self.create_test_notice_file()
        
        self.startup_guard._validate_configuration()
        result = self.startup_guard._validate_legal_compliance()
        
        assert result is True
        assert Path("private/registry.yaml").exists()
        
        # Verify registry file content
        with open("private/registry.yaml", "r", encoding="utf-8") as f:
            registry_data = yaml.safe_load(f)
        
        assert 'sources' in registry_data
        assert 'compliance' in registry_data
        assert registry_data['compliance']['non_commercial'] is True
    
    def test_validate_file_structure_creates_directories(self):
        """Test file structure validation creates missing directories."""
        result = self.startup_guard._validate_file_structure()
        
        assert result is True
        
        # Check that required directories were created
        required_dirs = ['src', 'tests', 'docs', 'docs/ADRs', 'scripts', 'private', 'logs', 'evaluation']
        for dir_path in required_dirs:
            assert Path(dir_path).exists(), f"Directory {dir_path} should exist"
    
    def test_validate_file_structure_missing_required_files(self):
        """Test file structure validation fails with missing required files."""
        # Create some but not all required files
        self.create_test_legal_file()
        # Missing: README.md, NOTICE, settings.yaml
        
        result = self.startup_guard._validate_file_structure()
        
        assert result is False
        assert any("Required file not found" in error for error in self.startup_guard.errors)
    
    def test_validate_file_structure_creates_private_gitignore(self):
        """Test file structure validation creates private/.gitignore."""
        self.create_test_settings_file()
        self.create_test_legal_file()
        self.create_test_notice_file()
        
        with open("README.md", "w", encoding="utf-8") as f:
            f.write("# Test README")
        
        result = self.startup_guard._validate_file_structure()
        
        assert result is True
        assert Path("private/.gitignore").exists()
        
        # Verify gitignore content
        with open("private/.gitignore", "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "*" in content  # Should ignore all files
        assert "!.gitignore" in content  # Except .gitignore itself
    
    @patch('scripts.build_kb.__import__')
    def test_validate_external_dependencies_missing_packages(self, mock_import):
        """Test external dependencies validation fails with missing packages."""
        # Mock missing packages
        def side_effect(name):
            if name == 'fastapi':
                raise ImportError(f"No module named '{name}'")
            return Mock()
        
        mock_import.side_effect = side_effect
        
        result = self.startup_guard._validate_external_dependencies()
        
        assert result is False
        assert any("Missing Python packages" in error for error in self.startup_guard.errors)
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'})
    def test_validate_external_dependencies_with_api_keys(self):
        """Test external dependencies validation with available API keys."""
        with patch('scripts.build_kb.__import__') as mock_import:
            mock_import.return_value = Mock()
            
            result = self.startup_guard._validate_external_dependencies()
            
            assert result is True
            # Should log available API keys but not fail
    
    def test_validate_knowledge_base_creates_structure(self):
        """Test knowledge base validation creates KB structure."""
        self.create_test_settings_file()
        self.startup_guard._validate_configuration()
        
        result = self.startup_guard._validate_knowledge_base()
        
        assert result is True
        
        kb_path = Path("private/knowledge_base")
        assert kb_path.exists()
        
        # Check subdirectories
        kb_subdirs = ['characters', 'worlds', 'rules', 'templates']
        for subdir in kb_subdirs:
            subdir_path = kb_path / subdir
            assert subdir_path.exists(), f"KB subdirectory {subdir} should exist"
            assert (subdir_path / 'README.md').exists(), f"README should exist in {subdir}"
    
    def test_validate_api_readiness_success(self):
        """Test API readiness validation passes."""
        self.create_test_settings_file()
        self.startup_guard._validate_configuration()
        
        result = self.startup_guard._validate_api_readiness()
        
        assert result is True
    
    def test_validate_api_readiness_cors_warning(self):
        """Test API readiness validation warns about empty CORS origins."""
        config_with_empty_cors = {
            'system': {'name': 'Novel Engine'},
            'legal': {'enable_safeguards': True},
            'api': {'host': 'localhost', 'port': 8000, 'cors_enabled': True, 'cors_origins': []},
            'storage': {'kb_path': 'private/kb/'},
            'ai': {'provider': 'openai'},
            'simulation': {'iron_laws': {'enabled': True}},
            'performance': {'semantic_cache': {'enabled': True}},
            'security': {'strict_validation': True}
        }
        self.create_test_settings_file(config_with_empty_cors)
        self.startup_guard._validate_configuration()
        
        result = self.startup_guard._validate_api_readiness()
        
        assert result is True
        assert any("CORS enabled but no origins specified" in warning for warning in self.startup_guard.warnings)
    
    def test_validate_all_success(self):
        """Test complete validation passes with all components valid."""
        # Set up complete valid environment
        self.create_test_settings_file()
        self.create_test_legal_file()
        self.create_test_notice_file()
        
        with open("README.md", "w", encoding="utf-8") as f:
            f.write("# Test README")
        
        # Mock successful imports
        with patch('scripts.build_kb.__import__') as mock_import:
            mock_import.return_value = Mock()
            
            result = self.startup_guard.validate_all()
            
            assert result is True
            assert len(self.startup_guard.errors) == 0
            assert self.startup_guard.config is not None
    
    def test_validate_all_failure(self):
        """Test complete validation fails with missing components."""
        # Don't create any required files
        
        result = self.startup_guard.validate_all()
        
        assert result is False
        assert len(self.startup_guard.errors) > 0
    
    def test_get_system_status(self):
        """Test system status reporting."""
        self.create_test_settings_file()
        self.startup_guard._validate_configuration()
        
        status = self.startup_guard.get_system_status()
        
        assert 'timestamp' in status
        assert 'validation_passed' in status
        assert 'errors' in status
        assert 'warnings' in status
        assert 'config_loaded' in status
        assert 'system_ready' in status
        
        assert status['config_loaded'] is True
        assert isinstance(status['errors'], list)
        assert isinstance(status['warnings'], list)


class TestKnowledgeBaseBuilder:
    """Test the KnowledgeBaseBuilder system."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create logs directory
        Path("logs").mkdir(exist_ok=True)
        
        self.test_config = {
            'storage': {'kb_path': 'private/knowledge_base/'}
        }
        
        self.kb_builder = KnowledgeBaseBuilder(self.test_config)
    
    def teardown_method(self):
        """Clean up after each test."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_knowledge_base_builder_initialization(self):
        """Test KnowledgeBaseBuilder initializes properly."""
        builder = KnowledgeBaseBuilder(self.test_config)
        
        assert builder.config == self.test_config
        assert builder.logger is not None
    
    def test_build_kb_success(self):
        """Test knowledge base building succeeds."""
        result = self.kb_builder.build_kb()
        
        assert result is True
        
        kb_path = Path("private/knowledge_base")
        assert kb_path.exists()
        
        # Check structure was created
        expected_structure = {
            'characters': ['templates', 'instances'],
            'worlds': ['templates', 'instances'],
            'rules': ['iron_laws.yaml', 'fog_of_war.yaml'],
            'templates': ['narrative_templates.yaml']
        }
        
        for item, subitems in expected_structure.items():
            item_path = kb_path / item
            assert item_path.exists(), f"KB item {item} should exist"
            
            for subitem in subitems:
                if subitem.endswith('.yaml'):
                    # Check YAML files exist
                    subitem_path = item_path / subitem
                    assert subitem_path.exists(), f"KB file {subitem} should exist"
                else:
                    # Check subdirectories exist
                    subitem_path = item_path / subitem
                    assert subitem_path.exists(), f"KB subdirectory {subitem} should exist"
    
    def test_create_iron_laws_template(self):
        """Test Iron Laws template creation."""
        template = self.kb_builder._create_iron_laws_template()
        
        assert 'iron_laws' in template
        iron_laws = template['iron_laws']
        
        # Check all 5 Iron Laws are defined
        expected_laws = [
            'E001_RESOURCE_NEGATIVE',
            'E002_TARGET_INVALID',
            'E003_ACTION_IMPOSSIBLE',
            'E004_LOGIC_VIOLATION',
            'E005_CANON_BREACH'
        ]
        
        for law in expected_laws:
            assert law in iron_laws
            assert 'description' in iron_laws[law]
            assert 'validation' in iron_laws[law]
            assert 'priority' in iron_laws[law]
    
    def test_create_fog_of_war_template(self):
        """Test Fog of War template creation."""
        template = self.kb_builder._create_fog_of_war_template()
        
        assert 'fog_of_war' in template
        fog_of_war = template['fog_of_war']
        
        assert 'channels' in fog_of_war
        channels = fog_of_war['channels']
        
        # Check all 3 channels are defined
        expected_channels = ['visual', 'radio', 'intel']
        for channel in expected_channels:
            assert channel in channels
            assert 'default_range' in channels[channel]
            assert 'description' in channels[channel]
        
        assert 'filtering_rules' in fog_of_war
    
    def test_create_narrative_templates(self):
        """Test narrative templates creation."""
        template = self.kb_builder._create_narrative_templates()
        
        assert 'narrative_styles' in template
        styles = template['narrative_styles']
        
        # Check narrative styles are defined
        expected_styles = ['grimdark_dramatic', 'tactical', 'heroic']
        for style in expected_styles:
            assert style in styles
            assert 'tone' in styles[style]
            assert 'perspective' in styles[style]
            assert 'focus' in styles[style]


class TestStartupGuardIntegration:
    """Integration tests for startup guard system."""
    
    def setup_method(self):
        """Set up integration test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
    
    def teardown_method(self):
        """Clean up after integration tests."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_complete_test_environment(self):
        """Create a complete test environment for integration testing."""
        # Create all required files and directories
        config = {
            'system': {'name': 'Novel Engine', 'version': '1.0.0'},
            'legal': {
                'enable_safeguards': True,
                'compliance_mode': 'standard',
                'content_filtering': {'enable': True, 'severity': 'moderate'}
            },
            'api': {'host': 'localhost', 'port': 8000, 'cors_enabled': False},
            'storage': {'kb_path': 'private/knowledge_base/'},
            'ai': {'provider': 'openai'},
            'simulation': {
                'iron_laws': {'enabled': True},
                'fog_of_war': {'enabled': True}
            },
            'performance': {'semantic_cache': {'enabled': True}},
            'security': {'strict_validation': True}
        }
        
        with open("settings.yaml", "w", encoding="utf-8") as f:
            yaml.dump(config, f)
        
        legal_content = """# Legal Notice
## Non-Affiliation Disclaimer
This software is not affiliated with Games Workshop.
## Fan Mode Compliance
Fan mode compliance rules here.
## DMCA and Content Removal
DMCA procedures here.
## Disclaimer of Warranties
Warranty disclaimers here.
## Limitation of Liability
Liability limitations here.
"""
        with open("LEGAL.md", "w", encoding="utf-8") as f:
            f.write(legal_content)
        
        notice_content = """Novel Engine
Copyright (c) 2025

FastAPI - MIT License
Pydantic - MIT License
"""
        with open("NOTICE", "w", encoding="utf-8") as f:
            f.write(notice_content)
        
        with open("README.md", "w", encoding="utf-8") as f:
            f.write("# Novel Engine Test")
        
        # Create logs directory
        Path("logs").mkdir(exist_ok=True)
    
    @patch('scripts.build_kb.__import__')
    def test_complete_system_validation(self, mock_import):
        """Test complete system validation with all components."""
        mock_import.return_value = Mock()
        self.create_complete_test_environment()
        
        startup_guard = StartupGuard()
        result = startup_guard.validate_all()
        
        assert result is True
        assert len(startup_guard.errors) == 0
        
        # Verify system status
        status = startup_guard.get_system_status()
        assert status['validation_passed'] is True
        assert status['config_loaded'] is True
        assert status['system_ready'] is True
        
        # Verify knowledge base was created
        kb_path = Path("private/knowledge_base")
        assert kb_path.exists()
    
    def test_system_validation_with_warnings(self):
        """Test system validation that passes with warnings."""
        self.create_complete_test_environment()
        
        # Modify config to generate warnings
        with open("settings.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        config['legal']['enable_safeguards'] = False  # This should generate a warning
        
        with open("settings.yaml", "w", encoding="utf-8") as f:
            yaml.dump(config, f)
        
        with patch('scripts.build_kb.__import__') as mock_import:
            mock_import.return_value = Mock()
            
            startup_guard = StartupGuard()
            result = startup_guard.validate_all()
            
            # Should still pass but with warnings
            assert result is True
            assert len(startup_guard.warnings) > 0
            assert any("Legal safeguards are disabled" in warning for warning in startup_guard.warnings)
    
    def test_startup_guard_error_recovery(self):
        """Test startup guard handles errors gracefully."""
        # Create minimal environment that will have some failures
        Path("logs").mkdir(exist_ok=True)
        
        startup_guard = StartupGuard()
        
        # This should fail but not crash
        result = startup_guard.validate_all()
        
        assert result is False
        assert len(startup_guard.errors) > 0
        
        # Should still be able to get status
        status = startup_guard.get_system_status()
        assert 'timestamp' in status
        assert status['validation_passed'] is False


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])