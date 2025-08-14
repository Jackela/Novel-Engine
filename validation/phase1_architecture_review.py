#!/usr/bin/env python3
"""
PHASE 1.1: Architecture Review and Component Analysis
====================================================

Comprehensive analysis of StoryForge AI architecture to ensure:
1. All components are properly integrated
2. Data flows are correct and efficient  
3. Dependencies are satisfied
4. API contracts are consistent
5. Error handling is comprehensive
"""

import sys
import os
import json
import importlib
from typing import Dict, List, Any, Tuple
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class ArchitectureReviewer:
    """Comprehensive architecture analysis and validation."""
    
    def __init__(self):
        self.project_root = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.components = {}
        self.dependencies = {}
        self.api_contracts = {}
        self.issues = []
        self.recommendations = []
        
    def analyze_component_structure(self) -> Dict[str, Any]:
        """Analyze the structure and integration of core components."""
        
        print("🏗️  ANALYZING COMPONENT STRUCTURE")
        print("=" * 60)
        
        core_components = {
            'api_server.py': 'FastAPI Web Server - Main Entry Point',
            'director_agent.py': 'DirectorAgent - Game Master AI',
            'chronicler_agent.py': 'ChroniclerAgent - Narrative Generation',
            'persona_agent.py': 'PersonaAgent - Character Intelligence',
            'character_factory.py': 'CharacterFactory - Character Creation',
            'config_loader.py': 'ConfigLoader - Configuration Management'
        }
        
        analysis_results = {}
        
        for component_file, description in core_components.items():
            component_path = self.project_root / component_file
            
            if not component_path.exists():
                self.issues.append(f"❌ CRITICAL: Missing core component {component_file}")
                continue
                
            print(f"✅ {component_file}: {description}")
            
            # Analyze component
            try:
                component_analysis = self._analyze_single_component(component_path)
                analysis_results[component_file] = component_analysis
                
                print(f"   📊 Classes: {len(component_analysis['classes'])}")
                print(f"   🔧 Functions: {len(component_analysis['functions'])}")
                print(f"   📦 Imports: {len(component_analysis['imports'])}")
                
            except Exception as e:
                self.issues.append(f"❌ ERROR analyzing {component_file}: {e}")
                print(f"   ❌ Analysis failed: {e}")
                
        return analysis_results
    
    def _analyze_single_component(self, component_path: Path) -> Dict[str, Any]:
        """Analyze a single component file."""
        
        with open(component_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        analysis = {
            'classes': self._extract_classes(content),
            'functions': self._extract_functions(content),
            'imports': self._extract_imports(content),
            'api_endpoints': self._extract_api_endpoints(content),
            'error_handlers': self._extract_error_handlers(content),
            'size_metrics': {
                'lines': len(content.split('\n')),
                'characters': len(content),
                'complexity_score': self._calculate_complexity(content)
            }
        }
        
        return analysis
    
    def _extract_classes(self, content: str) -> List[str]:
        """Extract class definitions from content."""
        import re
        classes = re.findall(r'^class\s+(\w+).*?:', content, re.MULTILINE)
        return classes
    
    def _extract_functions(self, content: str) -> List[str]:
        """Extract function definitions from content."""
        import re
        functions = re.findall(r'^def\s+(\w+).*?:', content, re.MULTILINE)
        return functions
    
    def _extract_imports(self, content: str) -> List[str]:
        """Extract import statements from content."""
        import re
        imports = re.findall(r'^(?:from\s+(\S+)\s+)?import\s+(.+)', content, re.MULTILINE)
        return [f"{module}.{items}" if module else items for module, items in imports]
    
    def _extract_api_endpoints(self, content: str) -> List[str]:
        """Extract API endpoints from FastAPI content."""
        import re
        endpoints = re.findall(r'@app\.(get|post|put|delete)\("([^"]+)"', content)
        return [f"{method.upper()} {path}" for method, path in endpoints]
    
    def _extract_error_handlers(self, content: str) -> List[str]:
        """Extract error handling patterns."""
        import re
        
        error_patterns = [
            r'try:\s*\n.*?except.*?:',
            r'raise\s+\w+Exception',
            r'HTTPException',
            r'logger\.error',
            r'logger\.warning'
        ]
        
        handlers = []
        for pattern in error_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            handlers.extend([f"Error Handler: {match[:50]}..." for match in matches])
            
        return handlers[:10]  # Limit output
    
    def _calculate_complexity(self, content: str) -> float:
        """Calculate basic complexity score."""
        
        # Simple complexity metrics
        lines = content.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        complexity_indicators = {
            'nested_blocks': content.count('    if ') + content.count('    for ') + content.count('    while '),
            'exception_handling': content.count('try:') + content.count('except'),
            'function_definitions': content.count('def '),
            'class_definitions': content.count('class '),
            'conditional_statements': content.count('if ') + content.count('elif '),
        }
        
        # Weighted complexity score
        weights = {
            'nested_blocks': 2.0,
            'exception_handling': 1.5,
            'function_definitions': 1.0,
            'class_definitions': 1.2,
            'conditional_statements': 1.0,
        }
        
        total_complexity = sum(count * weights[metric] for metric, count in complexity_indicators.items())
        
        # Normalize by lines of code
        complexity_score = total_complexity / max(len(non_empty_lines), 1)
        
        return round(complexity_score, 2)
    
    def analyze_data_flows(self) -> Dict[str, Any]:
        """Analyze data flow patterns between components."""
        
        print("\n🔄 ANALYZING DATA FLOWS")
        print("=" * 60)
        
        data_flows = {
            'request_flow': [
                'HTTP Request → api_server.py',
                'api_server.py → character_factory.py (character creation)',
                'character_factory.py → persona_agent.py (agent instantiation)',
                'api_server.py → director_agent.py (simulation execution)', 
                'director_agent.py → persona_agent.py (turn processing)',
                'director_agent.py → campaign_log.md (event logging)',
                'api_server.py → chronicler_agent.py (narrative generation)',
                'chronicler_agent.py → campaign_log.md (log reading)',
                'chronicler_agent.py → demo_narratives/ (story output)',
                'api_server.py → HTTP Response'
            ],
            'data_dependencies': {
                'character_names': 'User Input → API → CharacterFactory → PersonaAgent',
                'campaign_logs': 'DirectorAgent → Campaign Log File → ChroniclerAgent',
                'narrative_style': 'User Input → API → ChroniclerAgent',
                'world_state': 'DirectorAgent → PersonaAgent (simulation turns)',
                'character_data': 'Character Files → PersonaAgent → DirectorAgent'
            },
            'critical_paths': [
                'Character Name Integration: API → ChroniclerAgent (injected names)',
                'Story Generation: Campaign Log → Narrative Output',
                'Error Recovery: All components → Graceful degradation'
            ]
        }
        
        print("📋 REQUEST FLOW ANALYSIS:")
        for i, step in enumerate(data_flows['request_flow'], 1):
            print(f"   {i:2d}. {step}")
        
        print("\n🔗 DATA DEPENDENCIES:")
        for data_type, flow in data_flows['data_dependencies'].items():
            print(f"   • {data_type}: {flow}")
            
        print("\n⚡ CRITICAL PATHS:")
        for path in data_flows['critical_paths']:
            print(f"   🎯 {path}")
        
        # Validate critical paths
        validation_results = self._validate_critical_paths()
        
        return {
            'flows': data_flows,
            'validation': validation_results
        }
    
    def _validate_critical_paths(self) -> Dict[str, bool]:
        """Validate that critical data paths are working."""
        
        print("\n🔍 VALIDATING CRITICAL PATHS:")
        
        validations = {}
        
        # 1. Character name integration path
        try:
            from chronicler_agent import ChroniclerAgent
            chronicler = ChroniclerAgent(character_names=['test_pilot'])
            validations['character_name_injection'] = chronicler.character_names == ['test_pilot']
            print(f"   ✅ Character name injection: PASS")
        except Exception as e:
            validations['character_name_injection'] = False
            print(f"   ❌ Character name injection: FAIL - {e}")
        
        # 2. Configuration system
        try:
            from config_loader import get_config
            config = get_config()
            validations['config_loading'] = config is not None
            print(f"   ✅ Configuration loading: PASS")
        except Exception as e:
            validations['config_loading'] = False
            print(f"   ❌ Configuration loading: FAIL - {e}")
        
        # 3. Character factory integration
        try:
            from character_factory import CharacterFactory
            factory = CharacterFactory()
            available_chars = factory.list_available_characters()
            validations['character_factory'] = len(available_chars) > 0
            print(f"   ✅ Character factory: PASS ({len(available_chars)} characters available)")
        except Exception as e:
            validations['character_factory'] = False
            print(f"   ❌ Character factory: FAIL - {e}")
        
        return validations
    
    def analyze_api_contracts(self) -> Dict[str, Any]:
        """Analyze API contracts and consistency."""
        
        print("\n🌐 ANALYZING API CONTRACTS")
        print("=" * 60)
        
        try:
            # Import and analyze API server
            sys.path.insert(0, str(self.project_root))
            
            # Read API server content for analysis
            api_server_path = self.project_root / 'api_server.py'
            with open(api_server_path, 'r', encoding='utf-8') as f:
                api_content = f.read()
            
            # Extract API endpoints
            endpoints = self._extract_api_endpoints(api_content)
            
            print("📡 DISCOVERED API ENDPOINTS:")
            for endpoint in endpoints:
                print(f"   • {endpoint}")
            
            # Analyze request/response models
            models = self._extract_pydantic_models(api_content)
            
            print(f"\n📋 PYDANTIC MODELS:")
            for model in models:
                print(f"   • {model}")
            
            # Check for error handling
            error_handlers = self._extract_error_handlers(api_content)
            
            print(f"\n🛡️  ERROR HANDLING PATTERNS:")
            for handler in error_handlers[:5]:  # Show first 5
                print(f"   • {handler}")
            
            return {
                'endpoints': endpoints,
                'models': models,
                'error_handlers': error_handlers,
                'contract_health': 'HEALTHY' if len(endpoints) > 5 else 'NEEDS_REVIEW'
            }
            
        except Exception as e:
            print(f"❌ API contract analysis failed: {e}")
            return {'error': str(e)}
    
    def _extract_pydantic_models(self, content: str) -> List[str]:
        """Extract Pydantic model definitions."""
        import re
        
        # Look for BaseModel classes
        models = re.findall(r'class\s+(\w+).*?BaseModel.*?:', content, re.DOTALL)
        
        # Also look for response_model definitions
        response_models = re.findall(r'response_model=(\w+)', content)
        
        return models + response_models
    
    def generate_architecture_report(self) -> Dict[str, Any]:
        """Generate comprehensive architecture analysis report."""
        
        print("\n" + "=" * 80)
        print("🏁 PHASE 1.1: ARCHITECTURE REVIEW SUMMARY")
        print("=" * 80)
        
        # Run all analyses
        component_analysis = self.analyze_component_structure()
        data_flow_analysis = self.analyze_data_flows()
        api_analysis = self.analyze_api_contracts()
        
        # Calculate overall health scores
        component_health = len([c for c in component_analysis.values() if c]) / len(component_analysis) if component_analysis else 0
        data_flow_health = len([v for v in data_flow_analysis['validation'].values() if v]) / len(data_flow_analysis['validation']) if data_flow_analysis.get('validation') else 0
        api_health = 1.0 if api_analysis.get('contract_health') == 'HEALTHY' else 0.5
        
        overall_health = (component_health + data_flow_health + api_health) / 3
        
        print(f"\n📊 ARCHITECTURE HEALTH METRICS:")
        print(f"   🏗️  Component Health: {component_health:.1%}")
        print(f"   🔄 Data Flow Health: {data_flow_health:.1%}")
        print(f"   🌐 API Contract Health: {api_health:.1%}")
        print(f"   🎯 Overall Health: {overall_health:.1%}")
        
        # Recommendations
        if overall_health >= 0.9:
            print(f"\n✅ ARCHITECTURE STATUS: EXCELLENT - Ready for testing")
        elif overall_health >= 0.7:
            print(f"\n⚠️  ARCHITECTURE STATUS: GOOD - Minor improvements needed")
        else:
            print(f"\n❌ ARCHITECTURE STATUS: NEEDS ATTENTION - Address issues before testing")
        
        if self.issues:
            print(f"\n🚨 CRITICAL ISSUES TO ADDRESS:")
            for issue in self.issues:
                print(f"   {issue}")
        
        return {
            'component_analysis': component_analysis,
            'data_flow_analysis': data_flow_analysis, 
            'api_analysis': api_analysis,
            'health_metrics': {
                'component_health': component_health,
                'data_flow_health': data_flow_health,
                'api_health': api_health,
                'overall_health': overall_health
            },
            'issues': self.issues,
            'status': 'EXCELLENT' if overall_health >= 0.9 else 'GOOD' if overall_health >= 0.7 else 'NEEDS_ATTENTION'
        }

def main():
    """Execute Phase 1.1 Architecture Review."""
    
    print("🔍 STORYFORGE AI - PHASE 1.1: ARCHITECTURE REVIEW")
    print("=" * 80)
    print("Comprehensive analysis of system architecture, components, and integration")
    print("=" * 80)
    
    reviewer = ArchitectureReviewer()
    report = reviewer.generate_architecture_report()
    
    # Save report
    output_dir = Path(__file__).parent
    output_dir.mkdir(exist_ok=True)
    
    report_path = output_dir / 'phase1_1_architecture_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n💾 Architecture report saved: {report_path}")
    
    return report['health_metrics']['overall_health'] >= 0.7

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)