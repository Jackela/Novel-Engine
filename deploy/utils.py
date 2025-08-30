#!/usr/bin/env python3
"""
Deployment Utilities
===================

Helper utilities for deployment operations, validation, and common tasks.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent

def validate_environment_variables(required_vars: List[str]) -> Dict[str, bool]:
    """Validate that required environment variables are set."""
    results = {}
    for var in required_vars:
        results[var] = bool(os.getenv(var))
    return results

def load_config(config_path: Union[str, Path]) -> Optional[Dict]:
    """Load YAML configuration file."""
    config_path = Path(config_path)
    if not config_path.exists():
        return None
    
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config {config_path}: {e}")
        return None

def check_deployment_prerequisites() -> Dict[str, bool]:
    """Check common deployment prerequisites."""
    checks = {}
    project_root = get_project_root()
    
    # Check required directories
    required_dirs = [
        'configs/environments',
        'configs/security', 
        'staging',
        'data'
    ]
    
    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        checks[f"directory_{dir_name}"] = dir_path.exists()
    
    # Check required files
    required_files = [
        'configs/environments/development.yaml',
        'configs/environments/settings.yaml',
        'configs/security/security.yaml',
        'requirements.txt'
    ]
    
    for file_name in required_files:
        file_path = project_root / file_name
        checks[f"file_{file_name}"] = file_path.exists()
    
    return checks

def run_command(command: List[str], cwd: Optional[Path] = None, timeout: int = 300) -> subprocess.CompletedProcess:
    """Run a command with proper error handling."""
    try:
        result = subprocess.run(
            command,
            cwd=cwd or get_project_root(),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Command timed out after {timeout} seconds: {' '.join(command)}")

def validate_python_environment() -> Dict[str, bool]:
    """Validate Python environment for deployment."""
    checks = {}
    
    # Check Python version
    py_version = sys.version_info
    checks['python_version_ok'] = py_version >= (3, 9)
    
    # Check required modules
    required_modules = [
        'yaml',
        'requests',
        'pathlib',
        'subprocess',
        'datetime'
    ]
    
    for module in required_modules:
        try:
            __import__(module)
            checks[f'module_{module}'] = True
        except ImportError:
            checks[f'module_{module}'] = False
    
    return checks

def get_deployment_info() -> Dict[str, str]:
    """Get deployment environment information."""
    project_root = get_project_root()
    info = {}
    
    # Get git information if available
    try:
        result = run_command(['git', 'rev-parse', 'HEAD'])
        if result.returncode == 0:
            info['git_commit'] = result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        info['git_commit'] = 'unknown'
    
    try:
        result = run_command(['git', 'branch', '--show-current'])
        if result.returncode == 0:
            info['git_branch'] = result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        info['git_branch'] = 'unknown'
    
    # Environment detection
    info['environment'] = os.getenv('NOVEL_ENGINE_ENV', 'development')
    info['project_root'] = str(project_root)
    
    return info

def print_deployment_status(checks: Dict[str, bool], title: str = "Deployment Prerequisites") -> bool:
    """Print deployment status in a formatted way."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")
    
    all_passed = True
    
    for check_name, passed in checks.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        formatted_name = check_name.replace('_', ' ').title()
        print(f" {status} | {formatted_name}")
        if not passed:
            all_passed = False
    
    print(f"{'='*60}")
    overall_status = "✅ ALL CHECKS PASSED" if all_passed else "❌ SOME CHECKS FAILED"
    print(f" Overall Status: {overall_status}")
    print(f"{'='*60}\n")
    
    return all_passed

def main():
    """Main utility function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Deployment utilities for Novel Engine")
    parser.add_argument('--check', action='store_true', help='Run deployment prerequisite checks')
    parser.add_argument('--info', action='store_true', help='Show deployment information')
    parser.add_argument('--validate-config', type=str, help='Validate a specific configuration file')
    
    args = parser.parse_args()
    
    if args.check:
        env_checks = validate_python_environment()
        print_deployment_status(env_checks, "Python Environment")
        
        prereq_checks = check_deployment_prerequisites()
        print_deployment_status(prereq_checks, "Deployment Prerequisites")
    
    if args.info:
        info = get_deployment_info()
        print(f"\n{'='*60}")
        print(" Deployment Information")
        print(f"{'='*60}")
        for key, value in info.items():
            formatted_key = key.replace('_', ' ').title()
            print(f" {formatted_key}: {value}")
        print(f"{'='*60}\n")
    
    if args.validate_config:
        config = load_config(args.validate_config)
        if config is None:
            print(f"❌ Failed to load configuration: {args.validate_config}")
            sys.exit(1)
        else:
            print(f"✅ Configuration loaded successfully: {args.validate_config}")
            print(f"   Keys found: {list(config.keys())}")

if __name__ == "__main__":
    main()