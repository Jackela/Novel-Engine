#!/usr/bin/env python3
"""
Enhanced Multi-Agent Simulation Runner
=====================================

Production-ready drop-in replacement for run_simulation.py that integrates
all 5 waves of multi-agent enhancement while maintaining full backward
compatibility with existing Novel Engine workflows.

This script provides seamless upgrade path from single-agent to advanced
multi-agent simulations with enterprise-grade capabilities.

Features:
- Backward compatibility with existing character sheets and configurations
- All 5 waves of multi-agent enhancement integrated
- Enterprise-grade monitoring and optimization
- Advanced emergent narrative capabilities
- Production-ready error handling and logging

Usage:
    # Classic mode (backward compatible)
    python run_enhanced_simulation.py --mode classic
    
    # Enhanced mode with multi-agent bridge
    python run_enhanced_simulation.py --mode enhanced
    
    # Full enterprise mode with all capabilities
    python run_enhanced_simulation.py --mode enterprise
    
    # Adaptive mode selection
    python run_enhanced_simulation.py --mode hybrid

Output:
    - Enhanced campaign logs with multi-agent coordination
    - Enterprise dashboards and monitoring reports
    - Emergent narrative analysis and character development tracking
    - Comprehensive performance metrics and optimization reports
"""

import asyncio
import logging
import sys
import os
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# Import the enhanced simulation orchestrator
from enhanced_simulation_orchestrator import (
    EnhancedSimulationOrchestrator,
    SimulationMode,
    IntegrationLevel,
    SimulationConfig,
    run_enhanced_simulation
)

# Import existing Novel Engine components for compatibility
try:
    from config_loader import get_config, get_simulation_turns, get_default_character_sheets
    NOVEL_ENGINE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Novel Engine config system not fully available: {e}")
    NOVEL_ENGINE_AVAILABLE = False

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('enhanced_simulation.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def display_banner():
    """Display enhanced simulation banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                   ENHANCED NOVEL ENGINE                      ║
║              Multi-Agent Simulation System                   ║
║                                                              ║
║  🏢 Enterprise-Grade Multi-Agent Orchestration              ║
║  🎭 Emergent Narrative Intelligence                         ║
║  ⚡ Parallel Agent Coordination                             ║
║  📊 Real-time Monitoring & Optimization                     ║
║  🔗 Full Novel Engine Compatibility                         ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def parse_command_line_arguments():
    """Parse command line arguments for enhanced simulation."""
    parser = argparse.ArgumentParser(
        description="Enhanced Multi-Agent Novel Engine Simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Simulation Modes:
  classic    - Original DirectorAgent workflow (backward compatible)
  enhanced   - Multi-agent bridge with AI integration
  enterprise - Full 5-wave orchestration with all capabilities
  hybrid     - Adaptive mode selection based on scenario complexity

Integration Levels:
  minimal      - Basic compatibility mode
  standard     - Full feature integration
  comprehensive - All advanced features
  enterprise    - Production deployment ready

Examples:
  python run_enhanced_simulation.py --mode enterprise --turns 15
  python run_enhanced_simulation.py --mode classic --characters trooper.yaml ork.yaml
  python run_enhanced_simulation.py --compatibility-test
        """
    )
    
    # Simulation configuration
    parser.add_argument(
        "--mode", 
        choices=["classic", "enhanced", "enterprise", "hybrid"],
        default="enterprise",
        help="Simulation execution mode (default: enterprise)"
    )
    
    parser.add_argument(
        "--integration-level",
        choices=["minimal", "standard", "comprehensive", "enterprise"],
        default="enterprise",
        help="Level of integration with existing systems (default: enterprise)"
    )
    
    parser.add_argument(
        "--turns", 
        type=int,
        default=None,
        help="Number of simulation turns (default: from config or 10)"
    )
    
    # Character and campaign configuration
    parser.add_argument(
        "--characters",
        nargs="*",
        help="Character sheet files to use (default: from config)"
    )
    
    parser.add_argument(
        "--campaign",
        help="Campaign brief file for narrative context"
    )
    
    parser.add_argument(
        "--max-agents",
        type=int,
        default=10,
        help="Maximum number of agents to coordinate (default: 10)"
    )
    
    # Enterprise features
    parser.add_argument(
        "--enable-monitoring",
        action="store_true",
        default=True,
        help="Enable real-time monitoring and dashboards"
    )
    
    parser.add_argument(
        "--enable-optimization",
        action="store_true", 
        default=True,
        help="Enable performance optimization"
    )
    
    parser.add_argument(
        "--enable-emergent-narrative",
        action="store_true",
        default=True,
        help="Enable emergent narrative intelligence"
    )
    
    parser.add_argument(
        "--enable-parallel-processing",
        action="store_true",
        default=True,
        help="Enable parallel agent coordination"
    )
    
    # Output configuration
    parser.add_argument(
        "--output-dir",
        default="enhanced_simulation_output",
        help="Output directory for reports and logs"
    )
    
    parser.add_argument(
        "--generate-reports",
        action="store_true",
        default=True,
        help="Generate comprehensive simulation reports"
    )
    
    parser.add_argument(
        "--save-dashboards",
        action="store_true",
        default=True,
        help="Save enterprise monitoring dashboards"
    )
    
    # Testing and validation
    parser.add_argument(
        "--compatibility-test",
        action="store_true",
        help="Run compatibility test with existing Novel Engine"
    )
    
    parser.add_argument(
        "--validate-integration",
        action="store_true",
        help="Validate integration with existing systems"
    )
    
    parser.add_argument(
        "--benchmark-performance",
        action="store_true",
        help="Run performance benchmarking"
    )
    
    # Debug and development
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true", 
        help="Enable debug mode with detailed output"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Initialize systems without running simulation"
    )
    
    return parser.parse_args()


def configure_logging(verbose: bool = False, debug: bool = False):
    """Configure logging based on command line options."""
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING
    
    # Update existing loggers
    logging.getLogger().setLevel(level)
    
    # Configure enhanced simulation logger specifically
    logger.setLevel(level)
    
    if debug:
        logger.info("Debug logging enabled")
    elif verbose:
        logger.info("Verbose logging enabled")


def load_novel_engine_config(args) -> Dict[str, Any]:
    """Load Novel Engine configuration if available."""
    config_data = {}
    
    if NOVEL_ENGINE_AVAILABLE:
        try:
            novel_config = get_config()
            config_data["novel_engine_config"] = novel_config
            
            # Get simulation turns from config if not specified
            if args.turns is None:
                args.turns = get_simulation_turns(novel_config)
                logger.info(f"Using turns from config: {args.turns}")
            
            # Get default character sheets if not specified
            if args.characters is None:
                args.characters = get_default_character_sheets(novel_config)
                logger.info(f"Using default characters: {args.characters}")
            
            config_data["config_loaded"] = True
            
        except Exception as e:
            logger.warning(f"Could not load Novel Engine config: {e}")
            config_data["config_loaded"] = False
            
            # Set fallback defaults
            if args.turns is None:
                args.turns = 10
            if args.characters is None:
                args.characters = ["demo_character_1", "demo_character_2"]
    
    else:
        logger.warning("Novel Engine config system not available, using defaults")
        config_data["config_loaded"] = False
        
        # Set fallback defaults
        if args.turns is None:
            args.turns = 10
        if args.characters is None:
            args.characters = ["demo_character_1", "demo_character_2"]
    
    return config_data


def create_simulation_config(args, config_data: Dict[str, Any]) -> SimulationConfig:
    """Create simulation configuration from arguments and loaded config."""
    # Map string values to enums
    mode_mapping = {
        "classic": SimulationMode.CLASSIC,
        "enhanced": SimulationMode.ENHANCED,
        "enterprise": SimulationMode.ENTERPRISE,
        "hybrid": SimulationMode.HYBRID
    }
    
    integration_mapping = {
        "minimal": IntegrationLevel.MINIMAL,
        "standard": IntegrationLevel.STANDARD,
        "comprehensive": IntegrationLevel.COMPREHENSIVE,
        "enterprise": IntegrationLevel.ENTERPRISE
    }
    
    return SimulationConfig(
        mode=mode_mapping[args.mode],
        integration_level=integration_mapping[args.integration_level],
        num_turns=args.turns,
        enable_logging=True,
        enable_monitoring=args.enable_monitoring,
        enable_optimization=args.enable_optimization,
        max_agents=args.max_agents,
        enable_parallel_processing=args.enable_parallel_processing,
        enable_emergent_narrative=args.enable_emergent_narrative,
        enable_relationship_tracking=True,
        output_directory=args.output_dir,
        generate_comprehensive_reports=args.generate_reports,
        save_enterprise_dashboards=args.save_dashboards
    )


async def run_compatibility_test(args) -> bool:
    """Run compatibility test with existing Novel Engine systems."""
    try:
        logger.info("=== RUNNING COMPATIBILITY TEST ===")
        
        # Create orchestrator for testing
        config = SimulationConfig(
            mode=SimulationMode.ENTERPRISE,
            integration_level=IntegrationLevel.ENTERPRISE,
            output_directory=args.output_dir
        )
        
        orchestrator = EnhancedSimulationOrchestrator(config)
        
        # Initialize system
        init_result = await orchestrator.initialize_integrated_system()
        if not init_result["success"]:
            print(f"❌ System initialization failed: {init_result}")
            return False
        
        # Run compatibility test
        test_result = await orchestrator.run_compatibility_test()
        
        # Display results
        print(f"\n📊 COMPATIBILITY TEST RESULTS:")
        print(f"   Overall Score: {test_result['compatibility_score']:.2%}")
        print(f"   Components Tested: {len(test_result['components_tested'])}")
        
        if test_result['compatibility_issues']:
            print(f"   Issues Found: {len(test_result['compatibility_issues'])}")
            for issue in test_result['compatibility_issues']:
                print(f"     ⚠️  {issue}")
        
        if test_result['integration_warnings']:
            print(f"   Integration Warnings: {len(test_result['integration_warnings'])}")
            for warning in test_result['integration_warnings']:
                print(f"     ⚠️  {warning}")
        
        # Performance impact
        perf_impact = test_result.get('performance_impact', {})
        print(f"\n⚡ PERFORMANCE IMPACT:")
        for metric, value in perf_impact.items():
            print(f"   {metric.replace('_', ' ').title()}: {value}")
        
        success = test_result['compatibility_score'] >= 0.8
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"\n🎯 COMPATIBILITY TEST: {status}")
        
        return success
        
    except Exception as e:
        logger.error(f"Compatibility test failed: {e}")
        print(f"❌ Compatibility test failed: {e}")
        return False


async def run_performance_benchmark(args) -> Dict[str, Any]:
    """Run performance benchmarking."""
    try:
        logger.info("=== RUNNING PERFORMANCE BENCHMARK ===")
        
        benchmark_results = {
            "timestamp": datetime.now(),
            "mode_benchmarks": {},
            "scalability_test": {},
            "memory_usage": {},
            "recommendations": []
        }
        
        # Test different modes
        modes = [SimulationMode.CLASSIC, SimulationMode.ENHANCED, SimulationMode.ENTERPRISE]
        
        for mode in modes:
            print(f"📊 Benchmarking {mode.value} mode...")
            
            start_time = datetime.now()
            
            result = await run_enhanced_simulation(
                character_sheets=args.characters[:5],  # Limit for benchmarking
                mode=mode,
                num_turns=5  # Shorter for benchmarking
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            benchmark_results["mode_benchmarks"][mode.value] = {
                "execution_time": execution_time,
                "success": result.get("success", False),
                "turns_per_second": 5 / execution_time if execution_time > 0 else 0,
                "memory_efficient": execution_time < 30  # Arbitrary threshold
            }
            
            print(f"   {mode.value}: {execution_time:.2f}s ({5/execution_time:.1f} turns/sec)")
        
        # Generate recommendations
        enterprise_time = benchmark_results["mode_benchmarks"]["enterprise"]["execution_time"]
        classic_time = benchmark_results["mode_benchmarks"]["classic"]["execution_time"]
        
        overhead = (enterprise_time - classic_time) / classic_time * 100 if classic_time > 0 else 0
        
        if overhead < 50:
            benchmark_results["recommendations"].append("✅ Enterprise mode has acceptable performance overhead")
        else:
            benchmark_results["recommendations"].append("⚠️  Enterprise mode has high performance overhead")
        
        print(f"\n📈 BENCHMARK SUMMARY:")
        print(f"   Enterprise Mode Overhead: {overhead:.1f}%")
        
        for rec in benchmark_results["recommendations"]:
            print(f"   {rec}")
        
        return benchmark_results
        
    except Exception as e:
        logger.error(f"Performance benchmark failed: {e}")
        return {"error": str(e)}


async def execute_enhanced_simulation(args, config: SimulationConfig) -> Dict[str, Any]:
    """Execute the enhanced simulation with full integration."""
    try:
        logger.info(f"=== STARTING ENHANCED SIMULATION ===")
        logger.info(f"Mode: {config.mode.value}")
        logger.info(f"Integration Level: {config.integration_level.value}")
        logger.info(f"Turns: {config.num_turns}")
        logger.info(f"Characters: {args.characters}")
        
        # Execute simulation
        result = await run_enhanced_simulation(
            character_sheets=args.characters,
            campaign_brief=args.campaign,
            mode=config.mode,
            num_turns=config.num_turns
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Enhanced simulation execution failed: {e}")
        return {"success": False, "error": str(e)}


def display_simulation_results(result: Dict[str, Any]):
    """Display simulation results in formatted output."""
    print(f"\n🎯 SIMULATION RESULTS:")
    print(f"{'='*60}")
    
    if result["success"]:
        print(f"✅ Status: SUCCESSFUL")
        print(f"🎭 Mode: {result['mode']}")
        print(f"🔗 Integration: {result.get('integration_level', 'N/A')}")
        print(f"🎯 Turns Completed: {result['turns_executed']}")
        print(f"🤖 Agents Participated: {result['agents_participated']}")
        print(f"⏱️  Execution Time: {result['execution_time']:.2f} seconds")
        
        if 'summary' in result:
            summary = result['summary']
            print(f"📊 Success Rate: {summary.get('success_rate', 0):.1%}")
            print(f"⚡ Avg Turn Time: {summary.get('average_turn_time', 0):.2f}s")
            
            if summary.get('enterprise_features_used'):
                print(f"🏢 Enterprise Features: {summary['multi_agent_enhancements']}")
        
        if result.get('report_path'):
            print(f"📋 Detailed Report: {result['report_path']}")
        
        # Display enterprise dashboard summary if available
        if result.get('enterprise_dashboards'):
            latest_dashboard = result['enterprise_dashboards'][-1]['dashboard']
            print(f"\n🏢 ENTERPRISE DASHBOARD SUMMARY:")
            print(f"   System Health: {latest_dashboard.get('system_health', 'N/A')}")
            
            current_metrics = latest_dashboard.get('current_metrics', {})
            print(f"   Average Turn Time: {current_metrics.get('average_turn_time', 0):.2f}s")
            print(f"   Success Rate: {current_metrics.get('coordination_success_rate', 0):.1%}")
            print(f"   Quality Score: {current_metrics.get('overall_quality_score', 0):.2f}")
        
    else:
        print(f"❌ Status: FAILED")
        print(f"🚨 Error: {result.get('error', 'Unknown error')}")
        
        if result.get('turns_executed', 0) > 0:
            print(f"🎯 Partial Execution: {result['turns_executed']} turns completed")


def display_integration_status(init_result: Dict[str, Any]):
    """Display integration status information."""
    print(f"\n🔗 INTEGRATION STATUS:")
    print(f"{'='*40}")
    
    if init_result["success"]:
        components = init_result["components_initialized"]
        print(f"✅ System Integration: SUCCESSFUL")
        print(f"🏗️  Components Initialized: {len(components)}")
        
        for component in components:
            print(f"   ✅ {component}")
        
        if init_result.get("warnings"):
            print(f"\n⚠️  Integration Warnings:")
            for warning in init_result["warnings"]:
                print(f"   ⚠️  {warning}")
        
        # Display integration status details
        integration_status = init_result.get("integration_status", {})
        if integration_status:
            print(f"\n🔗 Integration Details:")
            for key, value in integration_status.items():
                if isinstance(value, dict):
                    print(f"   {key}: {value.get('status', 'active')}")
                else:
                    print(f"   {key}: {value}")
    
    else:
        print(f"❌ System Integration: FAILED")
        print(f"🚨 Error: {init_result.get('error', 'Unknown error')}")


async def main():
    """Main entry point for enhanced simulation execution."""
    try:
        # Display banner
        display_banner()
        
        # Parse command line arguments
        args = parse_command_line_arguments()
        
        # Configure logging
        configure_logging(args.verbose, args.debug)
        
        # Load Novel Engine configuration
        config_data = load_novel_engine_config(args)
        
        print(f"🔧 Configuration:")
        print(f"   Mode: {args.mode}")
        print(f"   Integration Level: {args.integration_level}")
        print(f"   Turns: {args.turns}")
        print(f"   Characters: {len(args.characters) if args.characters else 0}")
        print(f"   Novel Engine Config: {'✅ Loaded' if config_data.get('config_loaded') else '⚠️  Using defaults'}")
        
        # Handle special operations
        if args.compatibility_test:
            success = await run_compatibility_test(args)
            sys.exit(0 if success else 1)
        
        if args.benchmark_performance:
            await run_performance_benchmark(args)
            return
        
        # Create simulation configuration
        config = create_simulation_config(args, config_data)
        
        # Validate integration if requested
        if args.validate_integration:
            print(f"\n🔍 Running integration validation...")
            orchestrator = EnhancedSimulationOrchestrator(config)
            init_result = await orchestrator.initialize_integrated_system()
            display_integration_status(init_result)
            
            if not init_result["success"]:
                print(f"❌ Integration validation failed")
                sys.exit(1)
            else:
                print(f"✅ Integration validation passed")
        
        # Handle dry run
        if args.dry_run:
            print(f"\n🔍 Dry run mode - initializing systems only...")
            orchestrator = EnhancedSimulationOrchestrator(config)
            init_result = await orchestrator.initialize_integrated_system()
            display_integration_status(init_result)
            
            if init_result["success"]:
                print(f"✅ Dry run completed successfully")
            else:
                print(f"❌ Dry run failed")
                sys.exit(1)
            return
        
        # Execute enhanced simulation
        result = await execute_enhanced_simulation(args, config)
        
        # Display results
        display_simulation_results(result)
        
        # Exit with appropriate code
        sys.exit(0 if result["success"] else 1)
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Simulation interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Unexpected error in main execution: {e}")
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    """Entry point for enhanced simulation execution."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n⚠️  Simulation interrupted by user")
        sys.exit(1)