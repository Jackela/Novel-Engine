#!/usr/bin/env python3
"""
Apply comprehensive fixes and validate the results
This script will fix all issues and achieve 100% validation success
"""

import os
import sys
import time
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def print_header(title):
    """Print a formatted header"""
    width = 70
    print("\n" + "=" * width)
    print(f"🎯 {title}".center(width))
    print("=" * width)

def run_command(command, description):
    """Run a command and display results"""
    print(f"\n📌 {description}")
    print(f"   Command: {command}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print(f"   ✅ Success")
            if result.stdout:
                print(f"   Output: {result.stdout[:200]}...")
            return True
        else:
            print(f"   ❌ Failed with code {result.returncode}")
            if result.stderr:
                print(f"   Error: {result.stderr[:200]}...")
            return False
    except subprocess.TimeoutExpired:
        print(f"   ⏱️ Command timed out")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

async def check_service_health(port, service_name):
    """Check if a service is healthy"""
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"http://localhost:{port}/health")
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                print(f"   ✅ {service_name}: {status}")
                return status in ['healthy', 'ready']
            else:
                print(f"   ❌ {service_name}: HTTP {response.status_code}")
                return False
    except Exception as e:
        print(f"   ❌ {service_name}: Not responding")
        return False

async def verify_services():
    """Verify all services are running"""
    print("\n🔍 Verifying Services")
    
    services = [
        (8000, "Master Orchestrator"),
        (8001, "Browser Automation"),
        (8002, "API Testing"),
        (8003, "AI Quality"),
        (8004, "Results Aggregation"),
        (8005, "Notification Service")
    ]
    
    results = []
    for port, name in services:
        result = await check_service_health(port, name)
        results.append(result)
    
    return all(results)

def apply_fixes():
    """Apply the comprehensive fixes"""
    print_header("Applying Comprehensive Fixes")
    
    script_path = Path(__file__).parent / "comprehensive_fix.py"
    
    if not script_path.exists():
        print("❌ comprehensive_fix.py not found!")
        return False
    
    print(f"Running {script_path}")
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(result.stdout)
        
        if result.returncode == 0:
            print("✅ Fixes applied successfully!")
            return True
        else:
            print(f"❌ Fix script failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error running fix script: {e}")
        return False

def run_validation():
    """Run the validation script"""
    print_header("Running Validation")
    
    validation_script = Path(__file__).parent / "validate_deployment.py"
    
    if not validation_script.exists():
        print("❌ validate_deployment.py not found!")
        return False
    
    print(f"Running validation script...")
    
    try:
        result = subprocess.run(
            [sys.executable, str(validation_script)],
            capture_output=False,  # Let it print directly
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            print("\n✅ VALIDATION PASSED!")
            return True
        else:
            print("\n❌ Validation failed")
            return False
            
    except Exception as e:
        print(f"❌ Error running validation: {e}")
        return False

async def main():
    """Main execution flow"""
    print_header("AI Testing Framework Fix & Validation")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Check if services are running
    print_header("Step 1: Check Services")
    services_running = await verify_services()
    
    if not services_running:
        print("\n⚠️ Some services are not running.")
        print("Please start services first using:")
        print("  - Windows: ai_testing\\scripts\\start_services.bat")
        print("  - Linux/Mac: ai_testing/scripts/start_services.sh")
        return False
    
    # Step 2: Apply fixes
    print_header("Step 2: Apply Fixes")
    fixes_applied = apply_fixes()
    
    if not fixes_applied:
        print("\n❌ Failed to apply fixes")
        return False
    
    # Step 3: Restart services (optional)
    print_header("Step 3: Service Restart")
    print("Services may need to be restarted to apply fixes.")
    response = input("Restart services now? (y/n): ")
    
    if response.lower() == 'y':
        print("Stopping services...")
        
        # Stop services
        if sys.platform == "win32":
            run_command("taskkill /F /IM python.exe", "Stopping Python processes")
        else:
            run_command("pkill -f 'python.*ai_testing'", "Stopping AI testing services")
        
        time.sleep(3)
        
        # Start services
        print("Starting services...")
        start_script = Path(__file__).parent / ("start_services.bat" if sys.platform == "win32" else "start_services.sh")
        
        if start_script.exists():
            subprocess.Popen(str(start_script), shell=True)
            print("Waiting for services to start...")
            time.sleep(15)
        else:
            print("⚠️ Start script not found. Please restart services manually.")
            return False
        
        # Verify services are running
        services_running = await verify_services()
        if not services_running:
            print("❌ Services failed to start properly")
            return False
    
    # Step 4: Run validation
    print_header("Step 4: Run Validation")
    validation_passed = run_validation()
    
    # Step 5: Summary
    print_header("Summary")
    
    if validation_passed:
        print("🎉 SUCCESS! All validation tests passed!")
        print("✅ The AI Testing Framework is now fully operational")
        print("📊 Success Rate: 100%")
    else:
        print("❌ Validation did not pass completely")
        print("Please review the output above for details")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return validation_passed

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)