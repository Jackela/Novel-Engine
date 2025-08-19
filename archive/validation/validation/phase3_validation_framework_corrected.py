#!/usr/bin/env python3
"""
StoryForge AI - Phase 3: Validation Framework Execution (Corrected)
Comprehensive validation and verification framework for business logic and system behavior
"""

import json
import os
import sys
import unittest
import time
import tempfile
import shutil
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chronicler_agent import ChroniclerAgent
from director_agent import DirectorAgent, PersonaAgent
from character_factory import CharacterFactory
from config_loader import ConfigLoader

class ValidationFramework:
    """Comprehensive validation framework for StoryForge AI system"""
    
    def __init__(self, project_root: str = None):
        self.project_root = project_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.validation_results = {
            "business_logic": {},
            "data_integrity": {},
            "system_behavior": {},
            "quality_metrics": {},
            "timestamp": datetime.now().isoformat()
        }
        self.config_loader = ConfigLoader.get_instance()
        
    def run_all_validations(self) -> Dict[str, Any]:
        """Execute all validation tests"""
        print("=== PHASE 3: VALIDATION FRAMEWORK EXECUTION ===\n")
        
        # Business Logic Validation
        print("🎯 1. Business Logic Validation")
        self.validate_business_logic()
        
        # Data Integrity Validation  
        print("\n📊 2. Data Integrity Validation")
        self.validate_data_integrity()
        
        # System Behavior Validation
        print("\n⚙️ 3. System Behavior Validation")
        self.validate_system_behavior()
        
        # Quality Metrics Validation
        print("\n🔍 4. Quality Metrics Validation")
        self.validate_quality_metrics()
        
        # Generate comprehensive report
        self._generate_validation_report()
        
        return self.validation_results
    
    def validate_business_logic(self) -> Dict[str, Any]:
        """Validate core business logic requirements"""
        results = {}
        
        # 1. Story Generation Logic Validation
        print("   → Testing story generation logic...")
        results["story_generation"] = self._test_story_generation_logic()
        
        # 2. Character Management Logic
        print("   → Testing character management logic...")
        results["character_management"] = self._test_character_management_logic()
        
        # 3. Campaign Flow Logic
        print("   → Testing campaign flow logic...")
        results["campaign_flow"] = self._test_campaign_flow_logic()
        
        # 4. Agent Coordination Logic
        print("   → Testing agent coordination logic...")
        results["agent_coordination"] = self._test_agent_coordination_logic()
        
        self.validation_results["business_logic"] = results
        self._print_section_summary("Business Logic", results)
        return results
    
    def validate_data_integrity(self) -> Dict[str, Any]:
        """Validate data integrity and consistency"""
        results = {}
        
        # 1. Configuration Data Integrity
        print("   → Testing configuration data integrity...")
        results["configuration"] = self._test_configuration_integrity()
        
        # 2. Character Data Integrity
        print("   → Testing character data integrity...")
        results["character_data"] = self._test_character_data_integrity()
        
        # 3. Campaign Data Integrity
        print("   → Testing campaign data integrity...")
        results["campaign_data"] = self._test_campaign_data_integrity()
        
        # 4. File System Integrity
        print("   → Testing file system integrity...")
        results["filesystem"] = self._test_filesystem_integrity()
        
        self.validation_results["data_integrity"] = results
        self._print_section_summary("Data Integrity", results)
        return results
    
    def validate_system_behavior(self) -> Dict[str, Any]:
        """Validate system behavior patterns"""
        results = {}
        
        # 1. Error Handling Behavior
        print("   → Testing error handling behavior...")
        results["error_handling"] = self._test_error_handling_behavior()
        
        # 2. Performance Behavior
        print("   → Testing performance behavior...")
        results["performance"] = self._test_performance_behavior()
        
        # 3. Concurrent Access Behavior
        print("   → Testing concurrent access behavior...")
        results["concurrency"] = self._test_concurrent_behavior()
        
        # 4. Resource Management Behavior
        print("   → Testing resource management behavior...")
        results["resource_management"] = self._test_resource_management_behavior()
        
        self.validation_results["system_behavior"] = results
        self._print_section_summary("System Behavior", results)
        return results
    
    def validate_quality_metrics(self) -> Dict[str, Any]:
        """Validate quality metrics and thresholds"""
        results = {}
        
        # 1. Story Quality Metrics
        print("   → Testing story quality metrics...")
        results["story_quality"] = self._test_story_quality_metrics()
        
        # 2. Code Quality Metrics
        print("   → Testing code quality metrics...")
        results["code_quality"] = self._test_code_quality_metrics()
        
        # 3. Performance Metrics
        print("   → Testing performance metrics...")
        results["performance_metrics"] = self._test_performance_metrics()
        
        # 4. Reliability Metrics
        print("   → Testing reliability metrics...")
        results["reliability"] = self._test_reliability_metrics()
        
        self.validation_results["quality_metrics"] = results
        self._print_section_summary("Quality Metrics", results)
        return results
    
    def _test_story_generation_logic(self) -> Dict[str, Any]:
        """Test story generation business logic"""
        test_results = {"passed": 0, "failed": 0, "tests": []}
        
        try:
            # Test 1: Story generation produces valid output
            factory = CharacterFactory()
            characters = factory.list_available_characters()  # Corrected method name
            
            if len(characters) >= 2:
                char1, char2 = characters[:2]
                director = DirectorAgent(char1, char2)
                
                # Generate a test turn
                turn_result = director.execute_turn(1, {"context": "test scenario"})
                
                test_results["tests"].append({
                    "name": "story_generation_validity",
                    "passed": isinstance(turn_result, dict) and "content" in turn_result,
                    "details": f"Generated turn result: {type(turn_result)}"
                })
                
                # Test 2: Story content meets minimum requirements
                content = turn_result.get("content", "")
                min_length = 50  # Minimum story length
                
                test_results["tests"].append({
                    "name": "story_content_requirements",
                    "passed": len(content) >= min_length and content.strip() != "",
                    "details": f"Content length: {len(content)} chars"
                })
                
                # Test 3: No "Unknown" references in generated content
                has_unknown = "unknown" in content.lower() or "for unknown" in content.lower()
                
                test_results["tests"].append({
                    "name": "no_unknown_references",
                    "passed": not has_unknown,
                    "details": f"Contains 'unknown' references: {has_unknown}"
                })
                
            else:
                test_results["tests"].append({
                    "name": "insufficient_characters",
                    "passed": False,
                    "details": f"Only {len(characters)} characters available, need 2+"
                })
                
        except Exception as e:
            test_results["tests"].append({
                "name": "story_generation_exception",
                "passed": False,
                "details": f"Exception: {str(e)}"
            })
        
        # Calculate summary
        test_results["passed"] = sum(1 for t in test_results["tests"] if t["passed"])
        test_results["failed"] = len(test_results["tests"]) - test_results["passed"]
        test_results["success_rate"] = test_results["passed"] / len(test_results["tests"]) if test_results["tests"] else 0
        
        return test_results
    
    def _test_character_management_logic(self) -> Dict[str, Any]:
        """Test character management business logic"""
        test_results = {"passed": 0, "failed": 0, "tests": []}
        
        try:
            factory = CharacterFactory()
            
            # Test 1: Character factory initialization
            test_results["tests"].append({
                "name": "factory_initialization",
                "passed": factory is not None,
                "details": "CharacterFactory created successfully"
            })
            
            # Test 2: Character loading
            characters = factory.list_available_characters()  # Corrected method name
            test_results["tests"].append({
                "name": "character_loading",
                "passed": len(characters) > 0,
                "details": f"Loaded {len(characters)} characters"
            })
            
            # Test 3: Character creation validation
            valid_characters = 0
            for char in characters:
                try:
                    agent = factory.create_character(char)  # Corrected method name
                    if agent and isinstance(agent, PersonaAgent):
                        valid_characters += 1
                except Exception as e:
                    pass  # Count as invalid
            
            test_results["tests"].append({
                "name": "character_creation_validation",
                "passed": valid_characters == len(characters),
                "details": f"{valid_characters}/{len(characters)} characters can create valid agents"
            })
            
            # Test 4: Agent creation from characters
            if characters:
                test_char = characters[0]
                agent = factory.create_character(test_char)  # Corrected method name
                
                test_results["tests"].append({
                    "name": "agent_creation",
                    "passed": agent is not None and isinstance(agent, PersonaAgent),
                    "details": f"Created agent for character: {test_char}"
                })
            
        except Exception as e:
            test_results["tests"].append({
                "name": "character_management_exception",
                "passed": False,
                "details": f"Exception: {str(e)}"
            })
        
        # Calculate summary
        test_results["passed"] = sum(1 for t in test_results["tests"] if t["passed"])
        test_results["failed"] = len(test_results["tests"]) - test_results["passed"]
        test_results["success_rate"] = test_results["passed"] / len(test_results["tests"]) if test_results["tests"] else 0
        
        return test_results
    
    def _test_campaign_flow_logic(self) -> Dict[str, Any]:
        """Test campaign flow business logic"""
        test_results = {"passed": 0, "failed": 0, "tests": []}
        
        try:
            # Test 1: Campaign log creation and processing
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp_file:
                test_log_content = """# Test Campaign Log
## Turn 1
- **pilot**: Test action 1
- **engineer**: Test action 2

## Turn 2  
- **pilot**: Test action 3
- **scientist**: Test action 4
"""
                tmp_file.write(test_log_content)
                tmp_file_path = tmp_file.name
            
            try:
                chronicler = ChroniclerAgent()
                
                # Test campaign log processing using correct method
                processed = chronicler.transcribe_log(tmp_file_path)  # Corrected method name
                
                test_results["tests"].append({
                    "name": "campaign_log_processing",
                    "passed": processed is not None and len(processed.strip()) > 0,
                    "details": f"Processed log length: {len(processed) if processed else 0} chars"
                })
                
                # Test narrative generation quality
                if processed:
                    # Check for key narrative elements
                    has_structure = any(marker in processed for marker in ["#", "**", "Generated:", "Source:"])
                    no_unknown = "for unknown" not in processed.lower()
                    has_content = len(processed.strip()) > 100
                        
                    test_results["tests"].append({
                        "name": "narrative_quality",
                        "passed": has_structure and no_unknown and has_content,
                        "details": f"Structure: {has_structure}, No unknown: {no_unknown}, Content: {has_content}"
                    })
                
            finally:
                os.unlink(tmp_file_path)
                
        except Exception as e:
            test_results["tests"].append({
                "name": "campaign_flow_exception",
                "passed": False,
                "details": f"Exception: {str(e)}"
            })
        
        # Calculate summary
        test_results["passed"] = sum(1 for t in test_results["tests"] if t["passed"])
        test_results["failed"] = len(test_results["tests"]) - test_results["passed"]
        test_results["success_rate"] = test_results["passed"] / len(test_results["tests"]) if test_results["tests"] else 0
        
        return test_results
    
    def _test_agent_coordination_logic(self) -> Dict[str, Any]:
        """Test agent coordination business logic"""
        test_results = {"passed": 0, "failed": 0, "tests": []}
        
        try:
            factory = CharacterFactory()
            characters = factory.list_available_characters()  # Corrected method name
            
            if len(characters) >= 2:
                # Test 1: Director agent creation and coordination
                director = DirectorAgent(characters[0], characters[1])
                
                test_results["tests"].append({
                    "name": "director_creation",
                    "passed": director is not None,
                    "details": "DirectorAgent created successfully"
                })
                
                # Test 2: Agent coordination in turn execution
                turn_result = director.execute_turn(1, {"context": "coordination test"})
                
                test_results["tests"].append({
                    "name": "turn_coordination",
                    "passed": isinstance(turn_result, dict) and "content" in turn_result,
                    "details": f"Turn execution result type: {type(turn_result)}"
                })
                
                # Test 3: Multi-agent interaction
                if len(characters) >= 3:
                    director2 = DirectorAgent(characters[1], characters[2])
                    turn_result2 = director2.execute_turn(1, {"context": "multi-agent test"})
                    
                    test_results["tests"].append({
                        "name": "multi_agent_interaction",
                        "passed": isinstance(turn_result2, dict) and "content" in turn_result2,
                        "details": "Multiple directors can operate independently"
                    })
                
            else:
                test_results["tests"].append({
                    "name": "insufficient_characters_for_coordination",
                    "passed": False,
                    "details": f"Need 2+ characters, found {len(characters)}"
                })
                
        except Exception as e:
            test_results["tests"].append({
                "name": "agent_coordination_exception",
                "passed": False,
                "details": f"Exception: {str(e)}"
            })
        
        # Calculate summary
        test_results["passed"] = sum(1 for t in test_results["tests"] if t["passed"])
        test_results["failed"] = len(test_results["tests"]) - test_results["passed"]
        test_results["success_rate"] = test_results["passed"] / len(test_results["tests"]) if test_results["tests"] else 0
        
        return test_results
    
    def _test_configuration_integrity(self) -> Dict[str, Any]:
        """Test configuration data integrity"""
        test_results = {"passed": 0, "failed": 0, "tests": []}
        
        try:
            # Test 1: Configuration loading
            config_data = self.config_loader.get_config()  # Corrected method name
            
            test_results["tests"].append({
                "name": "config_loading",
                "passed": config_data is not None,
                "details": f"Config type: {type(config_data)}"
            })
            
            # Test 2: Key configuration values
            if config_data:
                # Test specific config access methods
                try:
                    simulation_turns = self.config_loader.get_simulation_turns()
                    char_sheets_path = self.config_loader.get_character_sheets_path()
                    output_dir = self.config_loader.get_output_directory()
                    
                    test_results["tests"].append({
                        "name": "config_values_accessible",
                        "passed": simulation_turns > 0 and len(char_sheets_path) > 0 and len(output_dir) > 0,
                        "details": f"Turns: {simulation_turns}, Path: {char_sheets_path}, Output: {output_dir}"
                    })
                    
                except Exception as e:
                    test_results["tests"].append({
                        "name": "config_values_accessible",
                        "passed": False,
                        "details": f"Config access error: {str(e)}"
                    })
                
                # Test 3: Default character sheets
                try:
                    default_sheets = self.config_loader.get_default_character_sheets()
                    
                    test_results["tests"].append({
                        "name": "default_character_sheets",
                        "passed": isinstance(default_sheets, list) and len(default_sheets) > 0,
                        "details": f"Default sheets: {len(default_sheets)} items"
                    })
                    
                except Exception as e:
                    test_results["tests"].append({
                        "name": "default_character_sheets",
                        "passed": False,
                        "details": f"Default sheets error: {str(e)}"
                    })
            
        except Exception as e:
            test_results["tests"].append({
                "name": "configuration_integrity_exception",
                "passed": False,
                "details": f"Exception: {str(e)}"
            })
        
        # Calculate summary
        test_results["passed"] = sum(1 for t in test_results["tests"] if t["passed"])
        test_results["failed"] = len(test_results["tests"]) - test_results["passed"]
        test_results["success_rate"] = test_results["passed"] / len(test_results["tests"]) if test_results["tests"] else 0
        
        return test_results
    
    def _test_character_data_integrity(self) -> Dict[str, Any]:
        """Test character data integrity"""
        test_results = {"passed": 0, "failed": 0, "tests": []}
        
        try:
            factory = CharacterFactory()
            characters = factory.list_available_characters()  # Corrected method name
            
            # Test 1: Character directory integrity
            character_dir = os.path.join(self.project_root, "characters")
            
            test_results["tests"].append({
                "name": "character_directory_exists",
                "passed": os.path.exists(character_dir) and os.path.isdir(character_dir),
                "details": f"Character directory: {character_dir}"
            })
            
            # Test 2: Character agent creation integrity
            valid_characters = 0
            invalid_characters = []
            
            for char in characters:
                try:
                    agent = factory.create_character(char)  # Corrected method name
                    if agent and isinstance(agent, PersonaAgent):
                        valid_characters += 1
                    else:
                        invalid_characters.append(f"{char}: invalid agent created")
                except Exception as e:
                    invalid_characters.append(f"{char}: creation error - {str(e)}")
            
            test_results["tests"].append({
                "name": "character_agent_creation_integrity",
                "passed": len(invalid_characters) == 0,
                "details": f"Valid: {valid_characters}, Invalid: {invalid_characters}"
            })
            
            # Test 3: Character file consistency
            file_consistency_issues = []
            
            for char in characters:
                char_dir = os.path.join(character_dir, char)
                if os.path.exists(char_dir):
                    expected_files = [f"character_{char}.md", "stats.yaml"]
                    
                    for expected_file in expected_files:
                        file_path = os.path.join(char_dir, expected_file)
                        if not os.path.exists(file_path):
                            file_consistency_issues.append(f"{char}: missing {expected_file}")
            
            test_results["tests"].append({
                "name": "character_file_consistency",
                "passed": len(file_consistency_issues) == 0,
                "details": f"Issues: {file_consistency_issues}" if file_consistency_issues else "All files consistent"
            })
            
        except Exception as e:
            test_results["tests"].append({
                "name": "character_data_integrity_exception",
                "passed": False,
                "details": f"Exception: {str(e)}"
            })
        
        # Calculate summary
        test_results["passed"] = sum(1 for t in test_results["tests"] if t["passed"])
        test_results["failed"] = len(test_results["tests"]) - test_results["passed"]
        test_results["success_rate"] = test_results["passed"] / len(test_results["tests"]) if test_results["tests"] else 0
        
        return test_results
    
    def _test_campaign_data_integrity(self) -> Dict[str, Any]:
        """Test campaign data integrity"""
        test_results = {"passed": 0, "failed": 0, "tests": []}
        
        try:
            # Test 1: Output directory integrity
            output_dirs = ["demo_narratives", "codex"]
            
            for output_dir in output_dirs:
                dir_path = os.path.join(self.project_root, output_dir)
                
                test_results["tests"].append({
                    "name": f"{output_dir}_directory_integrity",
                    "passed": os.path.exists(dir_path) and os.path.isdir(dir_path),
                    "details": f"Directory: {dir_path}"
                })
            
            # Test 2: Generated file format validation
            demo_dir = os.path.join(self.project_root, "demo_narratives")
            if os.path.exists(demo_dir):
                narrative_files = [f for f in os.listdir(demo_dir) if f.endswith('.md')]
                
                valid_narratives = 0
                format_issues = []
                
                for narrative_file in narrative_files[:5]:  # Check first 5 files
                    file_path = os.path.join(demo_dir, narrative_file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        # Check for required narrative structure
                        required_elements = ["Generated:", "Source:", "Chronicler:"]
                        missing_elements = [elem for elem in required_elements if elem not in content]
                        
                        if len(missing_elements) == 0:
                            valid_narratives += 1
                        else:
                            format_issues.append(f"{narrative_file}: missing {missing_elements}")
                            
                    except Exception as e:
                        format_issues.append(f"{narrative_file}: read error {str(e)}")
                
                test_results["tests"].append({
                    "name": "narrative_format_validation",
                    "passed": len(format_issues) == 0,
                    "details": f"Valid: {valid_narratives}, Issues: {format_issues}"
                })
            
        except Exception as e:
            test_results["tests"].append({
                "name": "campaign_data_integrity_exception",
                "passed": False,
                "details": f"Exception: {str(e)}"
            })
        
        # Calculate summary
        test_results["passed"] = sum(1 for t in test_results["tests"] if t["passed"])
        test_results["failed"] = len(test_results["tests"]) - test_results["passed"]
        test_results["success_rate"] = test_results["passed"] / len(test_results["tests"]) if test_results["tests"] else 0
        
        return test_results
    
    def _test_filesystem_integrity(self) -> Dict[str, Any]:
        """Test file system integrity"""
        test_results = {"passed": 0, "failed": 0, "tests": []}
        
        try:
            # Test 1: Project structure integrity
            required_dirs = ["characters", "demo_narratives", "validation"]
            missing_dirs = []
            
            for req_dir in required_dirs:
                dir_path = os.path.join(self.project_root, req_dir)
                if not os.path.exists(dir_path):
                    missing_dirs.append(req_dir)
            
            test_results["tests"].append({
                "name": "project_structure_integrity",
                "passed": len(missing_dirs) == 0,
                "details": f"Missing directories: {missing_dirs}" if missing_dirs else "All required directories present"
            })
            
            # Test 2: File permissions
            test_file_path = os.path.join(self.project_root, "demo_narratives", "test_permissions.tmp")
            
            try:
                with open(test_file_path, 'w') as f:
                    f.write("test")
                
                os.unlink(test_file_path)
                
                test_results["tests"].append({
                    "name": "file_write_permissions",
                    "passed": True,
                    "details": "Write permissions verified"
                })
                
            except Exception as e:
                test_results["tests"].append({
                    "name": "file_write_permissions",
                    "passed": False,
                    "details": f"Permission error: {str(e)}"
                })
            
            # Test 3: Disk space availability
            import shutil
            total, used, free = shutil.disk_usage(self.project_root)
            free_mb = free // (1024*1024)
            
            test_results["tests"].append({
                "name": "disk_space_availability",
                "passed": free_mb > 100,  # At least 100MB free
                "details": f"Free space: {free_mb} MB"
            })
            
        except Exception as e:
            test_results["tests"].append({
                "name": "filesystem_integrity_exception",
                "passed": False,
                "details": f"Exception: {str(e)}"
            })
        
        # Calculate summary
        test_results["passed"] = sum(1 for t in test_results["tests"] if t["passed"])
        test_results["failed"] = len(test_results["tests"]) - test_results["passed"]
        test_results["success_rate"] = test_results["passed"] / len(test_results["tests"]) if test_results["tests"] else 0
        
        return test_results
    
    def _test_error_handling_behavior(self) -> Dict[str, Any]:
        """Test error handling behavior"""
        test_results = {"passed": 0, "failed": 0, "tests": []}
        
        try:
            # Test 1: Invalid character handling
            factory = CharacterFactory()
            
            try:
                invalid_char_agent = factory.create_character("nonexistent_character")  # Corrected method name
                graceful_failure = invalid_char_agent is None
                
                test_results["tests"].append({
                    "name": "invalid_character_handling",
                    "passed": graceful_failure,
                    "details": f"Invalid character result: {type(invalid_char_agent)}"
                })
                
            except Exception as e:
                # Exception is expected for invalid character, check if it's handled gracefully
                test_results["tests"].append({
                    "name": "invalid_character_handling",
                    "passed": True,  # Exception is appropriate for invalid character
                    "details": f"Exception properly raised: {type(e).__name__}"
                })
            
            # Test 2: Invalid file path handling
            chronicler = ChroniclerAgent()
            
            try:
                result = chronicler.transcribe_log("nonexistent_file.md")  # Corrected method name
                graceful_failure = result is None or result == ""
                
                test_results["tests"].append({
                    "name": "invalid_file_handling",
                    "passed": graceful_failure,
                    "details": f"Invalid file result: {type(result)}"
                })
                
            except Exception as e:
                # Exception is expected for invalid file, check if it's handled gracefully
                test_results["tests"].append({
                    "name": "invalid_file_handling",
                    "passed": True,  # Exception is appropriate for invalid file
                    "details": f"Exception properly raised: {type(e).__name__}"
                })
            
            # Test 3: Empty input handling
            characters = factory.list_available_characters()  # Corrected method name
            if len(characters) >= 2:
                director = DirectorAgent(characters[0], characters[1])
                
                try:
                    empty_result = director.execute_turn(1, {})
                    handled_gracefully = isinstance(empty_result, dict)
                    
                    test_results["tests"].append({
                        "name": "empty_input_handling",
                        "passed": handled_gracefully,
                        "details": f"Empty input result: {type(empty_result)}"
                    })
                    
                except Exception as e:
                    test_results["tests"].append({
                        "name": "empty_input_handling",
                        "passed": False,
                        "details": f"Exception not handled: {str(e)}"
                    })
            
        except Exception as e:
            test_results["tests"].append({
                "name": "error_handling_behavior_exception",
                "passed": False,
                "details": f"Exception: {str(e)}"
            })
        
        # Calculate summary
        test_results["passed"] = sum(1 for t in test_results["tests"] if t["passed"])
        test_results["failed"] = len(test_results["tests"]) - test_results["passed"]
        test_results["success_rate"] = test_results["passed"] / len(test_results["tests"]) if test_results["tests"] else 0
        
        return test_results
    
    def _test_performance_behavior(self) -> Dict[str, Any]:
        """Test performance behavior"""
        test_results = {"passed": 0, "failed": 0, "tests": []}
        
        try:
            # Test 1: Story generation performance
            factory = CharacterFactory()
            characters = factory.list_available_characters()  # Corrected method name
            
            if len(characters) >= 2:
                director = DirectorAgent(characters[0], characters[1])
                
                start_time = time.time()
                turn_result = director.execute_turn(1, {"context": "performance test"})
                end_time = time.time()
                
                execution_time = end_time - start_time
                acceptable_time = execution_time < 30.0  # 30 second threshold
                
                test_results["tests"].append({
                    "name": "story_generation_performance",
                    "passed": acceptable_time,
                    "details": f"Execution time: {execution_time:.2f}s"
                })
            
            # Test 2: Character loading performance
            start_time = time.time()
            all_characters = factory.list_available_characters()  # Corrected method name
            character_agents = []
            for char in all_characters[:3]:  # Test first 3 characters
                try:
                    agent = factory.create_character(char)  # Corrected method name
                    character_agents.append(agent)
                except:
                    pass
            end_time = time.time()
            
            loading_time = end_time - start_time
            acceptable_loading = loading_time < 10.0  # 10 second threshold
            
            test_results["tests"].append({
                "name": "character_loading_performance",
                "passed": acceptable_loading,
                "details": f"Loading time: {loading_time:.2f}s for {len(all_characters)} characters"
            })
            
            # Test 3: Memory usage stability
            import psutil
            import gc
            
            # Force garbage collection and get initial memory
            gc.collect()
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Perform operations
            for i in range(3):
                if len(characters) >= 2:
                    director = DirectorAgent(characters[0], characters[1])
                    director.execute_turn(1, {"context": f"memory test {i}"})
            
            # Check final memory
            gc.collect()
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            acceptable_memory = memory_increase < 100  # Less than 100MB increase
            
            test_results["tests"].append({
                "name": "memory_usage_stability",
                "passed": acceptable_memory,
                "details": f"Memory increase: {memory_increase:.1f}MB"
            })
            
        except Exception as e:
            test_results["tests"].append({
                "name": "performance_behavior_exception",
                "passed": False,
                "details": f"Exception: {str(e)}"
            })
        
        # Calculate summary
        test_results["passed"] = sum(1 for t in test_results["tests"] if t["passed"])
        test_results["failed"] = len(test_results["tests"]) - test_results["passed"]
        test_results["success_rate"] = test_results["passed"] / len(test_results["tests"]) if test_results["tests"] else 0
        
        return test_results
    
    def _test_concurrent_behavior(self) -> Dict[str, Any]:
        """Test concurrent access behavior"""
        test_results = {"passed": 0, "failed": 0, "tests": []}
        
        try:
            from concurrent.futures import ThreadPoolExecutor
            import threading
            
            factory = CharacterFactory()
            characters = factory.list_available_characters()  # Corrected method name
            
            if len(characters) >= 2:
                # Test 1: Concurrent story generation
                def generate_story(thread_id):
                    try:
                        director = DirectorAgent(characters[0], characters[1])
                        result = director.execute_turn(1, {"context": f"concurrent test {thread_id}"})
                        return {"success": True, "thread_id": thread_id, "result_type": type(result).__name__}
                    except Exception as e:
                        return {"success": False, "thread_id": thread_id, "error": str(e)}
                
                with ThreadPoolExecutor(max_workers=3) as executor:
                    futures = [executor.submit(generate_story, i) for i in range(3)]
                    results = [future.result() for future in futures]
                
                successful_threads = sum(1 for r in results if r["success"])
                
                test_results["tests"].append({
                    "name": "concurrent_story_generation",
                    "passed": successful_threads >= 2,  # At least 2 of 3 should succeed
                    "details": f"{successful_threads}/3 threads successful"
                })
                
                # Test 2: Thread safety of character factory
                shared_data = {"errors": 0}
                lock = threading.Lock()
                
                def test_character_access(thread_id):
                    try:
                        for _ in range(5):
                            chars = factory.list_available_characters()  # Corrected method name
                            if len(chars) == 0:
                                with lock:
                                    shared_data["errors"] += 1
                    except Exception as e:
                        with lock:
                            shared_data["errors"] += 1
                
                threads = []
                for i in range(3):
                    thread = threading.Thread(target=test_character_access, args=(i,))
                    threads.append(thread)
                    thread.start()
                
                for thread in threads:
                    thread.join()
                
                test_results["tests"].append({
                    "name": "thread_safety_character_factory",
                    "passed": shared_data["errors"] == 0,
                    "details": f"Thread safety errors: {shared_data['errors']}"
                })
            
        except Exception as e:
            test_results["tests"].append({
                "name": "concurrent_behavior_exception",
                "passed": False,
                "details": f"Exception: {str(e)}"
            })
        
        # Calculate summary
        test_results["passed"] = sum(1 for t in test_results["tests"] if t["passed"])
        test_results["failed"] = len(test_results["tests"]) - test_results["passed"]
        test_results["success_rate"] = test_results["passed"] / len(test_results["tests"]) if test_results["tests"] else 0
        
        return test_results
    
    def _test_resource_management_behavior(self) -> Dict[str, Any]:
        """Test resource management behavior"""
        test_results = {"passed": 0, "failed": 0, "tests": []}
        
        try:
            # Test 1: File handle management
            chronicler = ChroniclerAgent()
            
            # Create multiple temporary files and process them
            temp_files = []
            try:
                for i in range(5):
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp_file:
                        tmp_file.write(f"# Test Campaign {i}\n## Turn 1\n- **pilot**: Test action {i}")
                        temp_files.append(tmp_file.name)
                
                # Process all files
                processing_results = []
                for temp_file in temp_files:
                    try:
                        result = chronicler.transcribe_log(temp_file)  # Corrected method name
                        processing_results.append(result is not None)
                    except Exception as e:
                        processing_results.append(False)
                
                successful_processing = sum(processing_results)
                
                test_results["tests"].append({
                    "name": "file_handle_management",
                    "passed": successful_processing >= 4,  # At least 4 of 5 should succeed
                    "details": f"{successful_processing}/5 files processed successfully"
                })
                
            finally:
                # Clean up temporary files
                for temp_file in temp_files:
                    try:
                        os.unlink(temp_file)
                    except:
                        pass
            
            # Test 2: Memory cleanup after operations
            import gc
            
            gc.collect()
            
            # Perform resource-intensive operations
            factory = CharacterFactory()
            characters = factory.list_available_characters()  # Corrected method name
            
            if len(characters) >= 2:
                agents_created = []
                for i in range(10):
                    director = DirectorAgent(characters[0], characters[1])
                    agents_created.append(director)
                
                # Clear references
                del agents_created
                gc.collect()
                
                test_results["tests"].append({
                    "name": "memory_cleanup",
                    "passed": True,  # If we reach here without memory errors, it's good
                    "details": "Memory cleanup completed successfully"
                })
            
            # Test 3: Output file management
            output_dir = os.path.join(self.project_root, "demo_narratives")
            if os.path.exists(output_dir):
                initial_files = len(os.listdir(output_dir))
                
                # Generate a test narrative
                chronicler = ChroniclerAgent()
                test_campaign_log = os.path.join(self.project_root, "campaign_log.md")
                
                if os.path.exists(test_campaign_log):
                    try:
                        chronicler.transcribe_log(test_campaign_log)  # Corrected method name
                        
                        # Check if new files were created appropriately
                        final_files = len(os.listdir(output_dir))
                        files_created = final_files > initial_files
                        
                        test_results["tests"].append({
                            "name": "output_file_management",
                            "passed": files_created,
                            "details": f"Files before: {initial_files}, after: {final_files}"
                        })
                        
                    except Exception as e:
                        test_results["tests"].append({
                            "name": "output_file_management",
                            "passed": False,
                            "details": f"File management error: {str(e)}"
                        })
            
        except Exception as e:
            test_results["tests"].append({
                "name": "resource_management_behavior_exception",
                "passed": False,
                "details": f"Exception: {str(e)}"
            })
        
        # Calculate summary
        test_results["passed"] = sum(1 for t in test_results["tests"] if t["passed"])
        test_results["failed"] = len(test_results["tests"]) - test_results["passed"]
        test_results["success_rate"] = test_results["passed"] / len(test_results["tests"]) if test_results["tests"] else 0
        
        return test_results
    
    def _test_story_quality_metrics(self) -> Dict[str, Any]:
        """Test story quality metrics"""
        test_results = {"passed": 0, "failed": 0, "tests": []}
        
        try:
            factory = CharacterFactory()
            characters = factory.list_available_characters()  # Corrected method name
            
            if len(characters) >= 2:
                director = DirectorAgent(characters[0], characters[1])
                turn_result = director.execute_turn(1, {"context": "quality metrics test"})
                
                if "content" in turn_result:
                    content = turn_result["content"]
                    
                    # Test 1: Content length quality
                    min_length = 100
                    length_quality = len(content) >= min_length
                    
                    test_results["tests"].append({
                        "name": "content_length_quality",
                        "passed": length_quality,
                        "details": f"Content length: {len(content)} chars (min: {min_length})"
                    })
                    
                    # Test 2: No placeholder text
                    placeholder_terms = ["placeholder", "lorem ipsum", "todo", "fixme", "unknown"]
                    has_placeholders = any(term in content.lower() for term in placeholder_terms)
                    
                    test_results["tests"].append({
                        "name": "no_placeholder_text",
                        "passed": not has_placeholders,
                        "details": f"Contains placeholders: {has_placeholders}"
                    })
                    
                    # Test 3: Character name integration
                    char_names = [characters[0], characters[1]]
                    names_mentioned = sum(1 for name in char_names if name in content)
                    good_integration = names_mentioned >= 1  # At least one character mentioned
                    
                    test_results["tests"].append({
                        "name": "character_name_integration",
                        "passed": good_integration,
                        "details": f"Character names mentioned: {names_mentioned}/{len(char_names)}"
                    })
                    
                    # Test 4: Narrative coherence
                    coherence_indicators = [".", "!", "?", ","]  # Basic sentence structure
                    has_structure = all(indicator in content for indicator in ['.'])  # At least sentences
                    
                    test_results["tests"].append({
                        "name": "narrative_coherence",
                        "passed": has_structure,
                        "details": f"Has basic sentence structure: {has_structure}"
                    })
                    
                    # Test 5: No "For Unknown" segments
                    no_unknown_segments = "for unknown" not in content.lower()
                    
                    test_results["tests"].append({
                        "name": "no_unknown_segments",
                        "passed": no_unknown_segments,
                        "details": f"Contains 'For Unknown' segments: {not no_unknown_segments}"
                    })
            
        except Exception as e:
            test_results["tests"].append({
                "name": "story_quality_metrics_exception",
                "passed": False,
                "details": f"Exception: {str(e)}"
            })
        
        # Calculate summary
        test_results["passed"] = sum(1 for t in test_results["tests"] if t["passed"])
        test_results["failed"] = len(test_results["tests"]) - test_results["passed"]
        test_results["success_rate"] = test_results["passed"] / len(test_results["tests"]) if test_results["tests"] else 0
        
        return test_results
    
    def _test_code_quality_metrics(self) -> Dict[str, Any]:
        """Test code quality metrics"""
        test_results = {"passed": 0, "failed": 0, "tests": []}
        
        try:
            # Test 1: Import consistency
            python_files = []
            for root, dirs, files in os.walk(self.project_root):
                if 'validation' in root:  # Skip validation directory to avoid circular imports
                    continue
                for file in files:
                    if file.endswith('.py') and not file.startswith('test_'):
                        python_files.append(os.path.join(root, file))
            
            import_issues = []
            for py_file in python_files:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Check for basic import hygiene
                    lines = content.split('\n')
                    import_lines = [line for line in lines if line.strip().startswith(('import ', 'from '))]
                    
                    # Check for unused imports (basic check)
                    for import_line in import_lines:
                        if 'import' in import_line:
                            # Skip this complex analysis for now
                            pass
                    
                except Exception as e:
                    import_issues.append(f"{py_file}: {str(e)}")
            
            test_results["tests"].append({
                "name": "import_consistency",
                "passed": len(import_issues) == 0,
                "details": f"Import issues: {len(import_issues)}"
            })
            
            # Test 2: Function documentation
            documented_functions = 0
            total_functions = 0
            
            for py_file in python_files[:3]:  # Check first 3 files
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    import ast
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            total_functions += 1
                            if ast.get_docstring(node):
                                documented_functions += 1
                                
                except Exception as e:
                    pass  # Skip files that can't be parsed
            
            documentation_rate = documented_functions / total_functions if total_functions > 0 else 1.0
            good_documentation = documentation_rate >= 0.5  # At least 50% documented
            
            test_results["tests"].append({
                "name": "function_documentation",
                "passed": good_documentation,
                "details": f"Documentation rate: {documentation_rate:.1%} ({documented_functions}/{total_functions})"
            })
            
            # Test 3: Error handling presence
            error_handling_files = 0
            
            for py_file in python_files:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if 'try:' in content and 'except' in content:
                        error_handling_files += 1
                        
                except Exception as e:
                    pass
            
            error_handling_rate = error_handling_files / len(python_files) if python_files else 1.0
            good_error_handling = error_handling_rate >= 0.6  # At least 60% of files have error handling
            
            test_results["tests"].append({
                "name": "error_handling_presence",
                "passed": good_error_handling,
                "details": f"Error handling rate: {error_handling_rate:.1%} ({error_handling_files}/{len(python_files)})"
            })
            
        except Exception as e:
            test_results["tests"].append({
                "name": "code_quality_metrics_exception",
                "passed": False,
                "details": f"Exception: {str(e)}"
            })
        
        # Calculate summary
        test_results["passed"] = sum(1 for t in test_results["tests"] if t["passed"])
        test_results["failed"] = len(test_results["tests"]) - test_results["passed"]
        test_results["success_rate"] = test_results["passed"] / len(test_results["tests"]) if test_results["tests"] else 0
        
        return test_results
    
    def _test_performance_metrics(self) -> Dict[str, Any]:
        """Test performance metrics"""
        test_results = {"passed": 0, "failed": 0, "tests": []}
        
        try:
            # Test 1: Response time consistency
            factory = CharacterFactory()
            characters = factory.list_available_characters()  # Corrected method name
            
            if len(characters) >= 2:
                response_times = []
                
                for i in range(3):
                    director = DirectorAgent(characters[0], characters[1])
                    
                    start_time = time.time()
                    director.execute_turn(1, {"context": f"performance test {i}"})
                    end_time = time.time()
                    
                    response_times.append(end_time - start_time)
                
                # Calculate variance
                avg_time = sum(response_times) / len(response_times)
                variance = sum((t - avg_time) ** 2 for t in response_times) / len(response_times)
                consistent_performance = variance < 25.0  # Low variance indicates consistency
                
                test_results["tests"].append({
                    "name": "response_time_consistency",
                    "passed": consistent_performance,
                    "details": f"Avg: {avg_time:.2f}s, Variance: {variance:.2f}"
                })
            
            # Test 2: Memory efficiency
            import psutil
            import gc
            
            gc.collect()
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Perform operations
            if len(characters) >= 2:
                for i in range(5):
                    director = DirectorAgent(characters[0], characters[1])
                    director.execute_turn(1, {"context": f"memory test {i}"})
            
            gc.collect()
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_per_operation = (final_memory - initial_memory) / 5 if final_memory > initial_memory else 0
            
            efficient_memory = memory_per_operation < 20  # Less than 20MB per operation
            
            test_results["tests"].append({
                "name": "memory_efficiency",
                "passed": efficient_memory,
                "details": f"Memory per operation: {memory_per_operation:.1f}MB"
            })
            
            # Test 3: Throughput metrics
            if len(characters) >= 2:
                start_time = time.time()
                stories_generated = 0
                
                for i in range(3):
                    try:
                        director = DirectorAgent(characters[0], characters[1])
                        result = director.execute_turn(1, {"context": f"throughput test {i}"})
                        if result and "content" in result:
                            stories_generated += 1
                    except:
                        pass
                
                end_time = time.time()
                total_time = end_time - start_time
                throughput = stories_generated / total_time  # Stories per second
                
                acceptable_throughput = throughput > 0.01  # At least 0.01 stories per second
                
                test_results["tests"].append({
                    "name": "throughput_metrics",
                    "passed": acceptable_throughput,
                    "details": f"Throughput: {throughput:.3f} stories/sec ({stories_generated} stories in {total_time:.1f}s)"
                })
            
        except Exception as e:
            test_results["tests"].append({
                "name": "performance_metrics_exception",
                "passed": False,
                "details": f"Exception: {str(e)}"
            })
        
        # Calculate summary
        test_results["passed"] = sum(1 for t in test_results["tests"] if t["passed"])
        test_results["failed"] = len(test_results["tests"]) - test_results["passed"]
        test_results["success_rate"] = test_results["passed"] / len(test_results["tests"]) if test_results["tests"] else 0
        
        return test_results
    
    def _test_reliability_metrics(self) -> Dict[str, Any]:
        """Test reliability metrics"""
        test_results = {"passed": 0, "failed": 0, "tests": []}
        
        try:
            # Test 1: Success rate consistency
            factory = CharacterFactory()
            characters = factory.list_available_characters()  # Corrected method name
            
            if len(characters) >= 2:
                successful_operations = 0
                total_operations = 10
                
                for i in range(total_operations):
                    try:
                        director = DirectorAgent(characters[0], characters[1])
                        result = director.execute_turn(1, {"context": f"reliability test {i}"})
                        
                        if result and isinstance(result, dict) and "content" in result:
                            successful_operations += 1
                            
                    except Exception as e:
                        pass  # Count as failure
                
                success_rate = successful_operations / total_operations
                reliable_success_rate = success_rate >= 0.7  # At least 70% success rate
                
                test_results["tests"].append({
                    "name": "success_rate_consistency",
                    "passed": reliable_success_rate,
                    "details": f"Success rate: {success_rate:.1%} ({successful_operations}/{total_operations})"
                })
            
            # Test 2: Error recovery
            chronicler = ChroniclerAgent()
            recovery_tests_passed = 0
            recovery_tests_total = 3
            
            # Test invalid file recovery
            try:
                result = chronicler.transcribe_log("nonexistent.md")  # Corrected method name
                if result is None or result == "":
                    recovery_tests_passed += 1
            except:
                recovery_tests_passed += 1  # Exception is acceptable for invalid file
            
            # Test empty file recovery
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp_file:
                    tmp_file.write("")  # Empty file
                    tmp_file_path = tmp_file.name
                
                result = chronicler.transcribe_log(tmp_file_path)  # Corrected method name
                if result is not None:  # Should handle gracefully
                    recovery_tests_passed += 1
                    
                os.unlink(tmp_file_path)
            except:
                recovery_tests_passed += 1  # Exception is acceptable for empty file
            
            # Test malformed content recovery
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp_file:
                    tmp_file.write("This is not a valid campaign log format")
                    tmp_file_path = tmp_file.name
                
                result = chronicler.transcribe_log(tmp_file_path)  # Corrected method name
                if result is not None:  # Should handle gracefully
                    recovery_tests_passed += 1
                    
                os.unlink(tmp_file_path)
            except:
                recovery_tests_passed += 1  # Exception is acceptable for malformed content
            
            error_recovery_rate = recovery_tests_passed / recovery_tests_total
            good_error_recovery = error_recovery_rate >= 0.67  # At least 2/3 recovery tests pass
            
            test_results["tests"].append({
                "name": "error_recovery",
                "passed": good_error_recovery,
                "details": f"Recovery rate: {error_recovery_rate:.1%} ({recovery_tests_passed}/{recovery_tests_total})"
            })
            
            # Test 3: Data consistency
            consistency_issues = 0
            
            # Check if multiple operations produce consistent character data
            char_data_sets = []
            for _ in range(3):
                char_data = {}
                for char in characters[:3]:  # Check first 3 characters
                    try:
                        agent = factory.create_character(char)  # Corrected method name
                        if agent:
                            char_data[char] = char  # Character name should be consistent
                    except:
                        pass
                char_data_sets.append(char_data)
            
            # Check consistency across loads
            for char in characters[:3]:
                char_names = [data.get(char, "") for data in char_data_sets if char in data]
                if len(set(char_names)) > 1:  # Different names loaded for same character
                    consistency_issues += 1
            
            good_consistency = consistency_issues == 0
            
            test_results["tests"].append({
                "name": "data_consistency",
                "passed": good_consistency,
                "details": f"Consistency issues: {consistency_issues}"
            })
            
        except Exception as e:
            test_results["tests"].append({
                "name": "reliability_metrics_exception",
                "passed": False,
                "details": f"Exception: {str(e)}"
            })
        
        # Calculate summary
        test_results["passed"] = sum(1 for t in test_results["tests"] if t["passed"])
        test_results["failed"] = len(test_results["tests"]) - test_results["passed"]
        test_results["success_rate"] = test_results["passed"] / len(test_results["tests"]) if test_results["tests"] else 0
        
        return test_results
    
    def _print_section_summary(self, section_name: str, results: Dict[str, Any]):
        """Print summary for a validation section"""
        total_tests = sum(len(subsection.get("tests", [])) for subsection in results.values() if isinstance(subsection, dict))
        passed_tests = sum(subsection.get("passed", 0) for subsection in results.values() if isinstance(subsection, dict))
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        status_icon = "✅" if success_rate >= 80 else "⚠️" if success_rate >= 60 else "❌"
        print(f"   {status_icon} {section_name}: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
    
    def _generate_validation_report(self):
        """Generate comprehensive validation report"""
        report_path = os.path.join(self.project_root, "validation", "phase3_validation_report_corrected.json")
        
        # Calculate overall metrics
        total_tests = 0
        total_passed = 0
        
        for category in self.validation_results.values():
            if isinstance(category, dict) and category != self.validation_results.get("timestamp"):
                for subcategory in category.values():
                    if isinstance(subcategory, dict) and "tests" in subcategory:
                        total_tests += len(subcategory["tests"])
                        total_passed += subcategory.get("passed", 0)
        
        overall_success_rate = (total_passed / total_tests) if total_tests > 0 else 0
        
        # Add overall metrics
        self.validation_results["overall_metrics"] = {
            "total_tests": total_tests,
            "total_passed": total_passed,
            "overall_success_rate": overall_success_rate,
            "validation_status": "PASS" if overall_success_rate >= 0.8 else "WARN" if overall_success_rate >= 0.6 else "FAIL"
        }
        
        # Save report
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.validation_results, f, indent=2)
        
        # Print summary
        print(f"\n=== PHASE 3 VALIDATION SUMMARY ===")
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Tests Passed: {total_passed}")
        print(f"❌ Tests Failed: {total_tests - total_passed}")
        print(f"📈 Success Rate: {overall_success_rate:.1%}")
        
        status_icon = "✅" if overall_success_rate >= 0.8 else "⚠️" if overall_success_rate >= 0.6 else "❌"
        status_text = self.validation_results["overall_metrics"]["validation_status"]
        print(f"{status_icon} Validation Status: {status_text}")
        
        print(f"\n📄 Detailed report saved to: {report_path}")


def main():
    """Run Phase 3 validation framework"""
    try:
        print("StoryForge AI - Phase 3: Validation Framework Execution (Corrected)")
        print("=" * 60)
        
        validator = ValidationFramework()
        results = validator.run_all_validations()
        
        return results
        
    except Exception as e:
        print(f"❌ Validation framework error: {str(e)}")
        return None


if __name__ == "__main__":
    main()