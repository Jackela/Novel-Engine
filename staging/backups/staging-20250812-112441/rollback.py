#!/usr/bin/env python3
"""
Novel Engine Rollback Script
Generated: 2025-08-12T11:24:48.876865
Deployment ID: staging-20250812-112441
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def rollback():
    project_root = Path(__file__).parent.parent
    backup_dir = project_root / "staging" / "backups" / "staging-20250812-112441"
    
    print(f"🔄 Rolling back deployment: staging-20250812-112441")
    
    # Stop services
    print("⏹️  Stopping services...")
    try:
        subprocess.run(["pkill", "-f", "api_server.py"], check=False)
    except:
        pass
    
    # Restore configuration files
    config_files = ["config.yaml", "settings.yaml", "requirements.txt"]
    
    for config_file in config_files:
        backup_file = backup_dir / config_file
        target_file = project_root / config_file
        
        if backup_file.exists():
            shutil.copy2(backup_file, target_file)
            print(f"📦 Restored: {config_file}")
    
    # Restore directories  
    critical_dirs = ["private", "logs"]
    
    for dir_name in critical_dirs:
        backup_dir_path = backup_dir / dir_name
        target_dir_path = project_root / dir_name
        
        if backup_dir_path.exists():
            if target_dir_path.exists():
                shutil.rmtree(target_dir_path)
            shutil.copytree(backup_dir_path, target_dir_path)
            print(f"📦 Restored directory: {dir_name}")
    
    print("✅ Rollback completed")
    print("💡 Restart services manually if needed")

if __name__ == "__main__":
    rollback()
