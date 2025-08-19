#!/usr/bin/env python3
"""
Simple AI Intelligence Integration Test
======================================

A basic test to validate that the AI intelligence systems integrate properly
with the existing Novel Engine framework.
"""

import asyncio
import tempfile
from pathlib import Path

from src.ai_intelligence.integration_orchestrator import (
    IntegrationOrchestrator,
    IntegrationConfig,
    IntegrationMode
)


async def test_basic_integration():
    """Test basic integration functionality."""
    print("Starting basic AI intelligence integration test...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        # Create integration orchestrator
        config = IntegrationConfig(
            integration_mode=IntegrationMode.AI_ENHANCED,
            ai_feature_gates={
                "agent_coordination": True,
                "story_quality": True,
                "analytics": True,
                "recommendations": True,
                "export_integration": True
            }
        )
        
        orchestrator = IntegrationOrchestrator(
            database_path=db_path,
            integration_config=config
        )
        
        print("✓ Integration orchestrator created")
        
        # Test startup
        startup_result = await orchestrator.startup()
        print(f"Startup result: {startup_result.success}")
        
        if startup_result.success:
            print("✓ Integration orchestrator started successfully")
            print(f"  - Integration mode: {startup_result.data['integration_mode']}")
            print(f"  - Traditional system: {'✓' if startup_result.data['traditional_available'] else '✗'}")
            print(f"  - AI system: {'✓' if startup_result.data.get('ai_available', False) else '✗'}")
            
            # Test character action processing
            print("\nTesting character action processing...")
            action_result = await orchestrator.process_character_action(
                agent_id="test_agent",
                action="speak",
                context={"message": "Hello, Novel Engine AI!"}
            )
            
            if action_result.success:
                print("✓ Character action processed successfully")
            else:
                print(f"✗ Character action failed: {action_result.error.message if action_result.error else 'Unknown error'}")
            
            # Test story generation
            print("\nTesting story generation...")
            story_result = await orchestrator.generate_story_content(
                prompt="Generate a short fantasy story about a brave knight",
                user_id="test_user",
                preferences={"genre": "fantasy", "style": "heroic"}
            )
            
            if story_result.success:
                print("✓ Story generation completed successfully")
                print(f"  - Generation method: {story_result.data.get('generation_method', 'unknown')}")
                print(f"  - Content length: {len(story_result.data.get('content', ''))}")
            else:
                print(f"✗ Story generation failed: {story_result.error.message if story_result.error else 'Unknown error'}")
            
            # Test system status
            print("\nTesting system status...")
            status_result = await orchestrator.get_system_status()
            
            if status_result.success:
                print("✓ System status retrieved successfully")
                print(f"  - Total operations: {status_result.data['total_operations']}")
                print(f"  - Error rate: {status_result.data['error_rate']:.2%}")
                print(f"  - Integration active: {status_result.data['integration_config']['active']}")
            else:
                print(f"✗ System status failed: {status_result.error.message if status_result.error else 'Unknown error'}")
            
            # Test shutdown
            print("\nShutting down...")
            shutdown_result = await orchestrator.shutdown()
            
            if shutdown_result.success:
                print("✓ Integration orchestrator shut down successfully")
                print(f"  - Uptime: {shutdown_result.data['uptime_seconds']:.2f} seconds")
                print(f"  - Total operations: {shutdown_result.data['total_operations']}")
            else:
                print(f"✗ Shutdown failed: {shutdown_result.error.message if shutdown_result.error else 'Unknown error'}")
                
        else:
            print(f"✗ Startup failed: {startup_result.error.message if startup_result.error else 'Unknown error'}")
            
        print("\n" + "="*50)
        print("AI Intelligence Integration Test Completed")
        print("="*50)
        
        return startup_result.success
        
    finally:
        # Cleanup
        Path(db_path).unlink(missing_ok=True)


async def test_traditional_mode():
    """Test traditional mode operation."""
    print("\nTesting traditional-only mode...")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        config = IntegrationConfig(integration_mode=IntegrationMode.TRADITIONAL_ONLY)
        orchestrator = IntegrationOrchestrator(database_path=db_path, integration_config=config)
        
        startup_result = await orchestrator.startup()
        if startup_result.success:
            print("✓ Traditional mode startup successful")
            
            # Test operation in traditional mode
            action_result = await orchestrator.process_character_action(
                agent_id="traditional_agent",
                action="move",
                context={"direction": "north"}
            )
            
            if action_result.success:
                print("✓ Traditional mode operation successful")
            else:
                print(f"✗ Traditional mode operation failed: {action_result.error.message if action_result.error else 'Unknown'}")
            
            await orchestrator.shutdown()
        else:
            print(f"✗ Traditional mode startup failed: {startup_result.error.message if startup_result.error else 'Unknown'}")
            
    finally:
        Path(db_path).unlink(missing_ok=True)


async def main():
    """Run all integration tests."""
    print("Novel Engine AI Intelligence Integration Test Suite")
    print("="*50)
    
    try:
        # Test basic integration
        basic_success = await test_basic_integration()
        
        # Test traditional mode
        await test_traditional_mode()
        
        print(f"\nOverall test result: {'SUCCESS' if basic_success else 'FAILED'}")
        
    except Exception as e:
        print(f"\nTest suite failed with exception: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())